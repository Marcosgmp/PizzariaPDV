import requests
import time
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import IFOOD_API_URL, IFOOD_MERCHANT_ID
from ifood_services.auth import IfoodAuthService

class OrderStatus(str, Enum):
    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED" 
    CANCELLED = "CANCELLED"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    REJECTED = "REJECTED"
    INTEGRATED = "INTEGRATED"
    READY_TO_PICKUP = "READY_TO_PICKUP"

class OrderType(str, Enum):
    DELIVERY = "DELIVERY"
    TAKEOUT = "TAKEOUT"

class EventCode(str, Enum):
    PLC = "PLC"
    CFM = "CFM"
    RTP = "RTP"
    DIS = "DIS"
    CON = "CON"
    CAN = "CAN"
    CAR = "CAR"
    INT = "INT"
    DDCR = "DDCR" 

@dataclass
class Customer:
    id: str
    name: str
    phone: str
    document_number: str

@dataclass
class Address:
    street: str
    number: str
    complement: str
    neighborhood: str
    city: str
    state: str
    postal_code: str
    reference: str
    country: str

@dataclass
class Item:
    id: str
    name: str
    quantity: int
    price: float
    total_price: float
    observations: str
    external_code: str

@dataclass
class Payment:
    method: str
    value: float
    currency: str
    prepaid: bool
    type: str

@dataclass
class Order:
    id: str
    display_id: str
    reference: str
    short_reference: str
    created_at: str
    type: OrderType
    status: OrderStatus
    total_price: float
    sub_total: float
    delivery_fee: float
    delivery_address: Address
    customer: Customer
    items: List[Item]
    payments: List[Payment]
    preparation_time: int
    observations: str
    schedule: Dict[str, Any]
    is_test: bool

@dataclass
class OrderEvent:
    id: str
    code: EventCode
    order_id: str
    merchant_id: str
    created_at: str
    full_code: str
    sales_channel: str
    metadata: Dict[str, Any]

class IfoodOrderService:
    def __init__(self, merchant_id: str = None):
        self.base_url = f"{IFOOD_API_URL}/order/v1.0"
        self.merchant_id = merchant_id or IFOOD_MERCHANT_ID
        self.auth_service = IfoodAuthService()
        self.headers = {
            "Content-Type": "application/json"
        }
        self._acknowledged_events = set()

    def _get_headers(self):
        """Get headers with current access token"""
        token = self.auth_service.get_token()
        return {
            **self.headers,
            "Authorization": f"Bearer {token}"
        }

    def poll_events(self) -> List[OrderEvent]:
        """Faz polling de eventos"""
        url = f"{self.base_url}/events:polling"
        
        try:
            headers = self._get_headers()
            print("Polling de eventos...")
            resp = requests.get(url, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                events_data = resp.json()
                events = []
                event_ids_to_acknowledge = []
                
                for event_data in events_data:
                    try:
                        event_code = event_data.get("code", "")
                        
                        # Mapear códigos desconhecidos para códigos conhecidos
                        code_mapping = {
                            "DDCR": "DIS"  # Delivery Driver Created -> Dispatched
                        }
                        
                        mapped_code = code_mapping.get(event_code, event_code)
                        
                        event = OrderEvent(
                            id=event_data.get("id", ""),
                            code=EventCode(mapped_code),
                            order_id=event_data.get("orderId", ""),
                            merchant_id=event_data.get("merchantId", ""),
                            created_at=event_data.get("createdAt", ""),
                            full_code=event_data.get("fullCode", ""),
                            sales_channel=event_data.get("salesChannel", ""),
                            metadata=event_data.get("metadata", {})
                        )
                        events.append(event)
                        event_ids_to_acknowledge.append(event.id)
                        
                    except ValueError:
                        print(f"Codigo de evento desconhecido: {event_data.get('code')}")
                        # Adicionar mesmo assim para confirmar
                        event_ids_to_acknowledge.append(event_data.get("id", ""))
                        continue
                
                # Confirmar todos os eventos de uma vez
                if event_ids_to_acknowledge:
                    self.acknowledge_events(event_ids_to_acknowledge)
                
                print(f"{len(events)} evento(s) recebido(s)")
                return events
                
            elif resp.status_code == 204:
                print("Nenhum evento novo")
                return []
            else:
                print(f"Erro no polling: {resp.status_code} - {resp.text}")
                return []
                
        except Exception as e:
            print(f"Erro no polling de eventos: {e}")
            return []

    def acknowledge_events(self, event_ids: List[str]) -> bool:
        """Confirma múltiplos eventos de uma vez (forma correta)"""
        url = f"{self.base_url}/events/acknowledgment"
        
        try:
            headers = self._get_headers()
            data = [{"id": event_id} for event_id in event_ids]
            
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            
            if resp.status_code in [200, 204]:
                for event_id in event_ids:
                    self._acknowledged_events.add(event_id)
                print(f"{len(event_ids)} evento(s) confirmado(s)")
                return True
            else:
                print(f"Erro ao confirmar eventos: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao confirmar eventos: {e}")
            return False

    def acknowledge_event(self, event_id: str) -> bool:
        """Confirma um evento individual (para compatibilidade)"""
        return self.acknowledge_events([event_id])

    def get_order_details(self, order_id: str) -> Optional[Order]:
        """Obtem detalhes de um pedido especifico"""
        url = f"{self.base_url}/orders/{order_id}"
        
        try:
            headers = self._get_headers()
            print(f"Buscando detalhes do pedido {order_id}...")
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                order_data = resp.json()
                print(f"DADOS BRUTOS DO PEDIDO:")
                print(f"  Tipo: {type(order_data)}")
                
                order = self._parse_order_data(order_data)
                
                if order:
                    self._print_order_details(order)
                    return order
                else:
                    print("Erro ao processar dados do pedido")
                    return None
            else:
                print(f"Erro ao buscar detalhes do pedido: {resp.status_code} - {resp.text}")
                return None
                
        except Exception as e:
            print(f"Erro ao buscar detalhes do pedido: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_order_data(self, order_data: Dict) -> Optional[Order]:
        """Parse dos dados do pedido com estrutura atualizada da API"""
        try:
            print("Iniciando parsing dos dados do pedido...")
            
            if isinstance(order_data, list):
                if len(order_data) > 0:
                    print("API retornou lista, usando primeiro elemento")
                    order_data = order_data[0]
                else:
                    print("Lista de pedidos vazia")
                    return None
            
            order_id = order_data.get("id", "")
            display_id = order_data.get("displayId", "")
            created_at = order_data.get("createdAt", "")
            
            print(f"  ID: {order_id}")
            print(f"  Display ID: {display_id}")
            
            order_type_str = order_data.get("orderType", "DELIVERY")
            order_type = OrderType.DELIVERY if order_type_str.upper() == "DELIVERY" else OrderType.TAKEOUT
            
            status_str = order_data.get("status", "PLACED")
            status_map = {
                "PLACED": OrderStatus.PLACED,
                "CONFIRMED": OrderStatus.CONFIRMED,
                "CANCELLED": OrderStatus.CANCELLED,
                "DISPATCHED": OrderStatus.DISPATCHED,
                "DELIVERED": OrderStatus.DELIVERED,
                "INTEGRATED": OrderStatus.INTEGRATED,
                "READY_TO_PICKUP": OrderStatus.READY_TO_PICKUP
            }
            status = status_map.get(status_str.upper(), OrderStatus.PLACED)
            
            total_data = order_data.get("total", {})
            total_price = total_data.get("orderAmount", 0)
            sub_total_price = total_data.get("subTotal", 0)
            delivery_fee_price = total_data.get("deliveryFee", 0)
            
            customer_data = order_data.get("customer", {})
            phone_data = customer_data.get("phone", {})
            phone_number = phone_data.get("number", "") if isinstance(phone_data, dict) else str(customer_data.get("phone", ""))
            
            customer = Customer(
                id=customer_data.get("id", ""),
                name=customer_data.get("name", ""),
                phone=phone_number,
                document_number=customer_data.get("documentNumber", "")
            )
            
            delivery_data = order_data.get("delivery", {})
            address_data = delivery_data.get("deliveryAddress", {})
            address = Address(
                street=address_data.get("streetName", ""),
                number=address_data.get("streetNumber", ""),
                complement=address_data.get("complement", ""),
                neighborhood=address_data.get("neighborhood", ""),
                city=address_data.get("city", ""),
                state=address_data.get("state", ""),
                postal_code=address_data.get("postalCode", ""),
                reference=address_data.get("reference", ""),
                country=address_data.get("country", "BRA")
            )
            
            items = []
            items_data = order_data.get("items", [])
            
            for item_data in items_data:
                item = Item(
                    id=item_data.get("id", ""),
                    name=item_data.get("name", ""),
                    quantity=item_data.get("quantity", 0),
                    price=item_data.get("unitPrice", 0),
                    total_price=item_data.get("totalPrice", 0),
                    observations=item_data.get("observations", ""),
                    external_code=item_data.get("externalCode", "")
                )
                items.append(item)
            
            payments = []
            payments_data = order_data.get("payments", {})
            methods_data = payments_data.get("methods", [])
            
            for payment_data in methods_data:
                payment = Payment(
                    method=payment_data.get("method", ""),
                    value=payment_data.get("value", 0),
                    currency=payment_data.get("currency", "BRL"),
                    prepaid=payment_data.get("prepaid", False),
                    type=payment_data.get("type", "")
                )
                payments.append(payment)
            
            preparation_time = 0
            observations = delivery_data.get("observations", "")
            schedule = {}
            is_test = order_data.get("isTest", False)
            
            short_reference = display_id
            reference = f"IFOOD-{display_id}"
            
            order = Order(
                id=order_id,
                display_id=display_id,
                reference=reference,
                short_reference=short_reference,
                created_at=created_at,
                type=order_type,
                status=status,
                total_price=total_price,
                sub_total=sub_total_price,
                delivery_fee=delivery_fee_price,
                delivery_address=address,
                customer=customer,
                items=items,
                payments=payments,
                preparation_time=preparation_time,
                observations=observations,
                schedule=schedule,
                is_test=is_test
            )
            
            print(f"Pedido processado com sucesso: {order.short_reference}")
            return order
            
        except Exception as e:
            print(f"Erro critico ao processar dados do pedido: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _print_order_details(self, order: Order):
        """Exibe detalhes do pedido"""
        print(f"PEDIDO: {order.short_reference}")
        print("=" * 50)
        
        print(f"INFORMACOES BASICAS:")
        print(f"  ID: {order.id}")
        print(f"  Display ID: {order.display_id}")
        print(f"  Referencia: {order.reference}")
        print(f"  Data: {order.created_at}")
        print(f"  Tipo: {order.type.value}")
        print(f"  Status: {order.status.value}")
        print(f"  Teste: {'SIM' if order.is_test else 'NAO'}")
        
        print(f"VALORES:")
        print(f"  Subtotal: R$ {order.sub_total:.2f}")
        print(f"  Taxa de entrega: R$ {order.delivery_fee:.2f}")
        print(f"  Total: R$ {order.total_price:.2f}")
        
        print(f"CLIENTE:")
        print(f"  Nome: {order.customer.name}")
        print(f"  Telefone: {order.customer.phone}")
        print(f"  Documento: {order.customer.document_number}")
        
        if order.type == OrderType.DELIVERY:
            print(f"ENDERECO DE ENTREGA:")
            addr = order.delivery_address
            print(f"  {addr.street}, {addr.number}")
            if addr.complement:
                print(f"  Complemento: {addr.complement}")
            print(f"  {addr.neighborhood}")
            print(f"  {addr.city}/{addr.state}")
            print(f"  CEP: {addr.postal_code}")
            if addr.reference:
                print(f"  Referencia: {addr.reference}")
        
        print(f"ITENS ({len(order.items)}):")
        for i, item in enumerate(order.items, 1):
            print(f"  {i}. {item.name}")
            print(f"     Codigo: {item.external_code}")
            print(f"     Quantidade: {item.quantity}")
            print(f"     Preco unitario: R$ {item.price:.2f}")
            print(f"     Total: R$ {item.total_price:.2f}")
            if item.observations:
                print(f"     Observacoes: {item.observations}")
        
        print(f"PAGAMENTOS ({len(order.payments)}):")
        for payment in order.payments:
            tipo = "Pre-pago" if payment.prepaid else "Pendente"
            print(f"  - {payment.method}: R$ {payment.value:.2f} ({tipo})")

    def confirm_order(self, order_id: str) -> bool:
        """Confirma um pedido - DEVE SER FEITO EM ATE 5 MINUTOS"""
        url = f"{self.base_url}/orders/{order_id}/confirm"
        
        try:
            headers = self._get_headers()
            print(f"Confirmando pedido {order_id}...")
            resp = requests.post(url, headers=headers, timeout=10)
            
            if resp.status_code == 204:
                print("Pedido confirmado com sucesso!")
                return True
            elif resp.status_code == 202:
                print("Pedido ja confirmado ou em processamento")
                return True
            else:
                print(f"Erro ao confirmar pedido: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao confirmar pedido: {e}")
            return False

    def start_preparation(self, order_id: str) -> bool:
        """Inicia o preparo do pedido"""
        url = f"{self.base_url}/orders/{order_id}/startPreparation"
        
        try:
            headers = self._get_headers()
            print(f"Iniciando preparo do pedido {order_id}...")
            resp = requests.post(url, headers=headers, timeout=10)
            
            if resp.status_code == 204:
                print("Preparo iniciado com sucesso!")
                return True
            elif resp.status_code == 202:
                print("Preparo ja iniciado ou em processamento")
                return True
            else:
                print(f"Erro ao iniciar preparo: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao iniciar preparo: {e}")
            return False

    def ready_to_pickup(self, order_id: str) -> bool:
        """Marca pedido como pronto para retirada (apenas para TAKEOUT)"""
        url = f"{self.base_url}/orders/{order_id}/readyToPickup"
        
        try:
            headers = self._get_headers()
            print(f"Marcando pedido {order_id} como pronto para retirada...")
            resp = requests.post(url, headers=headers, timeout=10)
            
            if resp.status_code == 204:
                print("Pedido marcado como pronto para retirada!")
                return True
            elif resp.status_code == 202:
                print("Pedido ja marcado como pronto ou em processamento")
                return True
            else:
                print(f"Erro ao marcar como pronto: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao marcar como pronto: {e}")
            return False

    def dispatch_order(self, order_id: str) -> bool:
        """Despacha o pedido (apenas para DELIVERY)"""
        url = f"{self.base_url}/orders/{order_id}/dispatch"
        
        try:
            headers = self._get_headers()
            print(f"Despachando pedido {order_id}...")
            resp = requests.post(url, headers=headers, timeout=10)
            
            if resp.status_code == 204:
                print("Pedido despachado com sucesso!")
                return True
            elif resp.status_code == 202:
                print("Pedido ja despachado ou em processamento")
                return True
            else:
                print(f"Erro ao despachar pedido: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao despachar pedido: {e}")
            return False

    def cancel_order(self, order_id: str, reason: str = "OUT_OF_STOCK") -> bool:
        """Cancela um pedido"""
        url = f"{self.base_url}/orders/{order_id}/cancel"
        
        try:
            headers = self._get_headers()
            data = {
                "cancellationCode": reason,
                "reason": "Item indisponivel"
            }
            
            print(f"Cancelando pedido {order_id}...")
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            
            if resp.status_code == 204:
                print("Pedido cancelado com sucesso!")
                return True
            else:
                print(f"Erro ao cancelar pedido: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao cancelar pedido: {e}")
            return False

    def process_new_orders(self) -> List[Order]:
        """Processa eventos e retorna novos pedidos"""
        print("PROCESSANDO NOVOS PEDIDOS...")
        events = self.poll_events()
        
        new_orders = []
        
        for event in events:
            event_description = {
                EventCode.PLC: "NOVO PEDIDO RECEBIDO",
                EventCode.CFM: "PEDIDO CONFIRMADO", 
                EventCode.RTP: "PRONTO PARA RETIRADA",
                EventCode.DIS: "PEDIDO DESPACHADO",
                EventCode.CON: "PEDIDO ENTREGUE",
                EventCode.CAN: "PEDIDO CANCELADO",
                EventCode.CAR: "SOLICITACAO DE CANCELAMENTO",
                EventCode.INT: "PEDIDO INTEGRADO",
                EventCode.DDCR: "ENTREGADOR DESIGNADO"
            }.get(event.code, f"EVENTO: {event.code}")
            
            print(f"  {event_description} - Pedido: {event.order_id}")
            
            if event.code == EventCode.PLC:
                print(f"  PROCESSANDO NOVO PEDIDO!")
                
                order = self.get_order_details(event.order_id)
                if order:
                    new_orders.append(order)
                    print(f"  Pedido {order.short_reference} processado com sucesso!")
                    
                    # Tentar confirmar automaticamente se for novo
                    if order.status == OrderStatus.PLACED:
                        print(f"  Confirmando pedido automaticamente...")
                        if self.confirm_order(order.id):
                            print(f"  Pedido {order.short_reference} confirmado!")
                        else:
                            print(f"  Falha ao confirmar pedido {order.short_reference}")
            
            elif event.code in [EventCode.CFM, EventCode.RTP, EventCode.DIS, EventCode.CON, EventCode.CAN, EventCode.CAR, EventCode.DDCR]:
                # Apenas logar outros eventos - ja foram confirmados no poll_events
                print(f"  Evento {event.code} registrado para pedido {event.order_id}")
        
        return new_orders

def debug_order_details():
    """Debug especifico para ver os dados dos pedidos"""
    print("DEBUG DE DETALHES DE PEDIDOS")
    print("=" * 50)
    
    order_service = IfoodOrderService()
    
    print("Buscando eventos recentes...")
    events = order_service.poll_events()
    
    if events:
        plc_events = [e for e in events if e.code == EventCode.PLC]
        if plc_events:
            event = plc_events[0]
            print(f"Testando com pedido: {event.order_id}")
            order = order_service.get_order_details(event.order_id)
            if order:
                print(f"Pedido {order.display_id} processado com sucesso!")
                if order_service.confirm_order(order.id):
                    print("Pedido confirmado!")
        else:
            print("Nenhum evento PLC encontrado")
    else:
        print("Nenhum evento encontrado")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Servico de Pedidos iFood')
    parser.add_argument('--debug', action='store_true', help='Debug de detalhes')
    
    args = parser.parse_args()
    
    if args.debug:
        debug_order_details()
    else:
        print("ORDER SERVICE - iFood Food API")
        print("Executando debug...")
        debug_order_details()