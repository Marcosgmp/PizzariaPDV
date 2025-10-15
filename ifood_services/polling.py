import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ifood_services.orders import IfoodOrderService, Order as IfoodOrder, EventCode
from ifood_services.merchant import IfoodMerchantService, MerchantState
from config import IFOOD_MERCHANT_ID

class PollingType(str, Enum):
    ORDERS = "orders"
    MERCHANT_STATUS = "merchant_status"
    FULL_SYNC = "full_sync"

@dataclass
class PollingConfig:
    enabled: bool = True
    interval: int = 30
    max_retries: int = 3
    retry_delay: int = 5

@dataclass
class PollingResult:
    success: bool
    type: PollingType
    data: Optional[Dict] = None
    error: Optional[str] = None
    timestamp: datetime = None
    items_processed: int = 0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class IfoodPollingService:
    """Servico centralizado de polling para iFood"""
    
    def __init__(self):
        self.orders_service = IfoodOrderService()
        self.merchant_service = IfoodMerchantService()
        
        self.config = {
            PollingType.ORDERS: PollingConfig(enabled=True, interval=30),
            PollingType.MERCHANT_STATUS: PollingConfig(enabled=True, interval=60),
            PollingType.FULL_SYNC: PollingConfig(enabled=True, interval=300)
        }
        
        self.is_running = False
        self.threads = {}
        self.last_results = {}
        self.stats = {
            'total_polls': 0,
            'successful_polls': 0,
            'failed_polls': 0,
            'last_success': None,
            'started_at': None
        }
        
        self.callbacks = {
            'new_order': [],
            'status_change': [],
            'merchant_offline': [],
            'error': []
        }
        
        print("iFood Polling Service inicializado")

    def register_callback(self, event_type: str, callback: Callable):
        """Registra callback para eventos especificos"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            print(f"Callback registrado para evento: {event_type}")
        else:
            print(f"Tipo de evento desconhecido: {event_type}")

    def _notify_callbacks(self, event_type: str, data: Dict):
        """Notifica todos os callbacks registrados para um evento"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Erro em callback {event_type}: {e}")

    def start_polling(self):
        """Inicia todos os servicos de polling"""
        if self.is_running:
            print("Polling ja esta em execucao")
            return

        self.is_running = True
        self.stats['started_at'] = datetime.now()
        
        print("INICIANDO SERVICOS DE POLLING iFOOD...")
        
        for poll_type, config in self.config.items():
            if config.enabled:
                self._start_polling_thread(poll_type, config)
        
        print("Todos os servicos de polling iniciados")
        self._print_status()

    def stop_polling(self):
        """Para todos os servicos de polling"""
        if not self.is_running:
            print("Polling nao esta em execucao")
            return

        self.is_running = False
        print("PARANDO SERVICOS DE POLLING...")
        
        for poll_type, thread in self.threads.items():
            if thread and thread.is_alive():
                thread.join(timeout=5)
                print(f"Polling {poll_type.value} parado")
        
        self.threads.clear()
        print("Todos os servicos de polling parados")

    def _start_polling_thread(self, poll_type: PollingType, config: PollingConfig):
        """Inicia thread de polling para um tipo especifico"""
        thread = threading.Thread(
            target=self._polling_worker,
            args=(poll_type, config),
            daemon=True,
            name=f"ifood_poll_{poll_type.value}"
        )
        
        self.threads[poll_type] = thread
        thread.start()
        print(f"Polling {poll_type.value} iniciado (intervalo: {config.interval}s)")

    def _polling_worker(self, poll_type: PollingType, config: PollingConfig):
        """Worker thread para polling continuo"""
        while self.is_running:
            try:
                result = self._execute_poll(poll_type, config)
                self.last_results[poll_type] = result
                self._update_stats(result)
                
                if result.success:
                    self._process_successful_poll(result)
                else:
                    self._process_failed_poll(result)
                
            except Exception as e:
                error_result = PollingResult(
                    success=False,
                    type=poll_type,
                    error=f"Erro no worker: {e}"
                )
                self.last_results[poll_type] = error_result
                self._process_failed_poll(error_result)
            
            time.sleep(config.interval)

    def _execute_poll(self, poll_type: PollingType, config: PollingConfig) -> PollingResult:
        """Executa o polling baseado no tipo"""
        retries = 0
        
        while retries <= config.max_retries:
            try:
                if poll_type == PollingType.ORDERS:
                    return self._poll_orders()
                elif poll_type == PollingType.MERCHANT_STATUS:
                    return self._poll_merchant_status()
                elif poll_type == PollingType.FULL_SYNC:
                    return self._poll_full_sync()
                else:
                    return PollingResult(
                        success=False,
                        type=poll_type,
                        error=f"Tipo de polling nao implementado: {poll_type}"
                    )
                    
            except Exception as e:
                retries += 1
                if retries <= config.max_retries:
                    print(f"Tentativa {retries}/{config.max_retries} para {poll_type.value}")
                    time.sleep(config.retry_delay)
                else:
                    return PollingResult(
                        success=False,
                        type=poll_type,
                        error=f"Falha apos {retries} tentativas: {e}"
                    )
        
        return PollingResult(success=False, type=poll_type, error="Maximo de tentativas excedido")

    def _poll_orders(self) -> PollingResult:
        """Polling especifico para pedidos"""
        try:
            print("Polling de pedidos...")
            events = self.orders_service.poll_events()
            
            new_orders = []
            for event in events:
                if event.code == EventCode.PLC:
                    print(f"Novo pedido detectado: {event.order_id}")
                    
                    order = self.orders_service.get_order_details(event.order_id)
                    if order:
                        new_orders.append(order)
                        
                    self.orders_service.acknowledge_event(event.id)
            
            if new_orders:
                self._notify_callbacks('new_order', {
                    'orders': new_orders,
                    'count': len(new_orders),
                    'timestamp': datetime.now()
                })
            
            return PollingResult(
                success=True,
                type=PollingType.ORDERS,
                data={'events': len(events), 'new_orders': len(new_orders)},
                items_processed=len(new_orders)
            )
            
        except Exception as e:
            return PollingResult(
                success=False,
                type=PollingType.ORDERS,
                error=f"Erro no polling de pedidos: {e}"
            )

    def _poll_merchant_status(self) -> PollingResult:
        """Polling especifico para status do merchant"""
        try:
            print("Polling de status do merchant...")
            status = self.merchant_service.get_merchant_status()
            
            if status and status.state == MerchantState.CLOSED:
                self._notify_callbacks('merchant_offline', {
                    'merchant_id': IFOOD_MERCHANT_ID,
                    'status': status.state.value,
                    'message': status.message,
                    'timestamp': datetime.now()
                })
            
            return PollingResult(
                success=True,
                type=PollingType.MERCHANT_STATUS,
                data={'status': status.state.value if status else 'UNKNOWN'},
                items_processed=1
            )
            
        except Exception as e:
            return PollingResult(
                success=False,
                type=PollingType.MERCHANT_STATUS,
                error=f"Erro no polling de status: {e}"
            )

    def _poll_full_sync(self) -> PollingResult:
        """Sincronizacao completa"""
        try:
            print("Sincronizacao completa...")
            
            orders_result = self._poll_orders()
            status_result = self._poll_merchant_status()
            
            success = orders_result.success and status_result.success
            
            return PollingResult(
                success=success,
                type=PollingType.FULL_SYNC,
                data={
                    'orders': orders_result.data,
                    'merchant_status': status_result.data
                },
                items_processed=orders_result.items_processed + status_result.items_processed
            )
            
        except Exception as e:
            return PollingResult(
                success=False,
                type=PollingType.FULL_SYNC,
                error=f"Erro na sincronizacao completa: {e}"
            )

    def _process_successful_poll(self, result: PollingResult):
        """Processa resultado de polling bem-sucedido"""
        print(f"Polling {result.type.value} bem-sucedido: {result.items_processed} itens")
        
        if result.data:
            print(f"  Dados: {result.data}")

    def _process_failed_poll(self, result: PollingResult):
        """Processa resultado de polling com falha"""
        print(f"Polling {result.type.value} falhou: {result.error}")
        
        self._notify_callbacks('error', {
            'type': result.type.value,
            'error': result.error,
            'timestamp': result.timestamp
        })

    def _update_stats(self, result: PollingResult):
        """Atualiza estatisticas de polling"""
        self.stats['total_polls'] += 1
        
        if result.success:
            self.stats['successful_polls'] += 1
            self.stats['last_success'] = datetime.now()
        else:
            self.stats['failed_polls'] += 1

    def get_status(self) -> Dict:
        """Retorna status completo do polling service"""
        status = {
            'is_running': self.is_running,
            'stats': self.stats.copy(),
            'config': {k.value: {
                'enabled': v.enabled,
                'interval': v.interval
            } for k, v in self.config.items()},
            'last_results': {},
            'threads_status': {}
        }
        
        for poll_type, result in self.last_results.items():
            status['last_results'][poll_type.value] = {
                'success': result.success,
                'timestamp': result.timestamp.isoformat() if result.timestamp else None,
                'items_processed': result.items_processed,
                'error': result.error
            }
        
        for poll_type, thread in self.threads.items():
            status['threads_status'][poll_type.value] = {
                'alive': thread.is_alive() if thread else False,
                'name': thread.name if thread else None
            }
        
        return status

    def update_config(self, poll_type: PollingType, **kwargs):
        """Atualiza configuracao de polling"""
        if poll_type in self.config:
            for key, value in kwargs.items():
                if hasattr(self.config[poll_type], key):
                    setattr(self.config[poll_type], key, value)
                    print(f"Config {poll_type.value}.{key} atualizado para: {value}")
            
            if self.is_running and self.config[poll_type].enabled:
                self._restart_polling_thread(poll_type)

    def _restart_polling_thread(self, poll_type: PollingType):
        """Reinicia thread de polling especifica"""
        if poll_type in self.threads:
            old_thread = self.threads[poll_type]
            if old_thread and old_thread.is_alive():
                pass
            
            self._start_polling_thread(poll_type, self.config[poll_type])

    def _print_status(self):
        """Imprime status atual do polling"""
        status = self.get_status()
        print("STATUS DO POLLING iFOOD")
        print("=" * 40)
        print(f"Executando: {'SIM' if status['is_running'] else 'NAO'}")
        print(f"Total de polls: {status['stats']['total_polls']}")
        print(f"Bem-sucedidos: {status['stats']['successful_polls']}")
        print(f"Falhas: {status['stats']['failed_polls']}")
        print(f"Iniciado em: {status['stats']['started_at']}")
        
        if status['last_results']:
            print("Ultimos resultados:")
            for poll_type, result in status['last_results'].items():
                status_icon = "[OK]" if result['success'] else "[ERRO]"
                print(f"  {status_icon} {poll_type}: {result['items_processed']} itens")

    def force_poll(self, poll_type: PollingType) -> PollingResult:
        """Forca uma execucao imediata de polling"""
        print(f"Forcando polling: {poll_type.value}")
        
        config = self.config.get(poll_type, PollingConfig())
        result = self._execute_poll(poll_type, config)
        
        self.last_results[poll_type] = result
        self._update_stats(result)
        
        if result.success:
            self._process_successful_poll(result)
        else:
            self._process_failed_poll(result)
        
        return result

ifood_polling_service = IfoodPollingService()