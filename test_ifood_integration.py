import sys
import os
import time
from datetime import datetime

# Adiciona o diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ifood_services.auth import IfoodAuthService
from ifood_services.merchant import IfoodMerchantService
from ifood_services.orders import IfoodOrderService
from ifood_services.polling import IfoodPollingService, PollingType

class IfoodIntegrationTester:
    def __init__(self):
        self.auth_service = IfoodAuthService()
        self.merchant_service = IfoodMerchantService()
        self.order_service = IfoodOrderService()
        self.polling_service = IfoodPollingService()
        
    def run_complete_test(self):
        """Executa teste completo da integração"""
        print("=" * 60)
        print("TESTE COMPLETO DA INTEGRACAO iFOOD")
        print("=" * 60)
        
        # Teste 1: Autenticação
        print("\n1. TESTANDO AUTENTICACAO")
        print("-" * 30)
        auth_success = self.test_authentication()
        if not auth_success:
            print("FALHA NA AUTENTICACAO - TESTE INTERROMPIDO")
            return False
        
        # Teste 2: Serviço Merchant
        print("\n2. TESTANDO SERVICO MERCHANT")
        print("-" * 30)
        merchant_success = self.test_merchant_service()
        
        # Teste 3: Serviço de Pedidos
        print("\n3. TESTANDO SERVICO DE PEDIDOS")
        print("-" * 30)
        orders_success = self.test_orders_service()
        
        # Teste 4: Serviço de Polling
        print("\n4. TESTANDO SERVICO DE POLLING")
        print("-" * 30)
        polling_success = self.test_polling_service()
        
        # Resumo
        print("\n" + "=" * 60)
        print("RESUMO DOS TESTES")
        print("=" * 60)
        print(f"Autenticacao: {'SUCESSO' if auth_success else 'FALHA'}")
        print(f"Merchant: {'SUCESSO' if merchant_success else 'FALHA'}")
        print(f"Pedidos: {'SUCESSO' if orders_success else 'FALHA'}")
        print(f"Polling: {'SUCESSO' if polling_success else 'FALHA'}")
        
        overall_success = auth_success and merchant_success and orders_success and polling_success
        print(f"\nRESULTADO GERAL: {'SUCESSO' if overall_success else 'FALHA'}")
        
        return overall_success

    def test_authentication(self):
        """Testa o serviço de autenticação"""
        try:
            print("Testando autenticacao...")
            token = self.auth_service.get_token()
            
            if token:
                print("SUCESSO: Token obtido com sucesso")
                print(f"Token: {token[:50]}...")
                return True
            else:
                print("FALHA: Nao foi possivel obter token")
                return False
                
        except Exception as e:
            print(f"FALHA: Erro na autenticacao: {e}")
            return False

    def test_merchant_service(self):
        """Testa o serviço merchant"""
        try:
            print("Testando servico merchant...")
            
            # Testar listagem de merchants
            merchants = self.merchant_service.list_merchants()
            if merchants:
                print(f"SUCESSO: {len(merchants)} merchant(s) encontrado(s)")
            else:
                print("AVISO: Nenhum merchant encontrado")
            
            # Testar detalhes do merchant
            merchant_details = self.merchant_service.get_merchant_details()
            if merchant_details:
                print("SUCESSO: Detalhes do merchant obtidos")
            else:
                print("AVISO: Nao foi possivel obter detalhes do merchant")
            
            # Testar status do merchant
            merchant_status = self.merchant_service.get_merchant_status()
            if merchant_status:
                print(f"SUCESSO: Status do merchant: {merchant_status.state.value}")
            else:
                print("AVISO: Nao foi possivel obter status do merchant")
            
            return True
            
        except Exception as e:
            print(f"FALHA: Erro no servico merchant: {e}")
            return False

    def test_orders_service(self):
        """Testa o serviço de pedidos"""
        try:
            print("Testando servico de pedidos...")
            
            # Testar polling de eventos
            events = self.order_service.poll_events()
            print(f"Eventos recebidos: {len(events)}")
            
            # Processar eventos de pedidos
            if events:
                new_orders = self.order_service.process_new_orders()
                print(f"Pedidos processados: {len(new_orders)}")
                
                # Se houver pedidos, testar operacoes
                if new_orders:
                    order = new_orders[0]
                    print(f"Testando operacoes no pedido: {order.display_id}")
                    
                    # Testar confirmacao (apenas se pedido ainda nao confirmado)
                    if order.status.value == "PLACED":
                        success = self.order_service.confirm_order(order.id)
                        print(f"Confirmacao do pedido: {'SUCESSO' if success else 'FALHA'}")
                    
            else:
                print("AVISO: Nenhum evento de pedido recebido")
                print("Dica: Faca um pedido de teste no iFood Developer Portal")
            
            return True
            
        except Exception as e:
            print(f"FALHA: Erro no servico de pedidos: {e}")
            return False

    def test_polling_service(self):
        """Testa o serviço de polling"""
        try:
            print("Testando servico de polling...")
            
            # Registrar callbacks de teste
            def test_new_order_callback(data):
                print(f" CALLBACK: Novo pedido recebido - {data['count']} pedido(s)")
                
            def test_error_callback(data):
                print(f" CALLBACK: Erro no polling - {data['error']}")
            
            self.polling_service.register_callback('new_order', test_new_order_callback)
            self.polling_service.register_callback('error', test_error_callback)
            
            # Testar polling forcado
            print("Testando polling forcado de pedidos...")
            result = self.polling_service.force_poll(PollingType.ORDERS)
            print(f"Polling forcado: {'SUCESSO' if result.success else 'FALHA'}")
            if result.error:
                print(f"Erro: {result.error}")
            
            # Testar status do polling
            status = self.polling_service.get_status()
            print(f"Status do polling: {status['stats']['total_polls']} polls executados")
            
            # Testar inicio e parada rapida do polling
            print("Testando inicio/parada do polling...")
            self.polling_service.start_polling()
            time.sleep(2)  # Aguardar um pouco
            self.polling_service.stop_polling()
            print("Polling iniciado e parado com sucesso")
            
            return True
            
        except Exception as e:
            print(f"FALHA: Erro no servico de polling: {e}")
            return False

    def test_specific_order(self, order_id: str):
        """Testa um pedido especifico"""
        print(f"\nTESTANDO PEDIDO ESPECIFICO: {order_id}")
        print("-" * 40)
        
        try:
            # Buscar detalhes do pedido
            order = self.order_service.get_order_details(order_id)
            if order:
                print(f"Pedido encontrado: {order.display_id}")
                print(f"Status: {order.status.value}")
                print(f"Cliente: {order.customer.name}")
                print(f"Total: R$ {order.total_price:.2f}")
                
                # Testar operacoes no pedido
                if order.status.value == "PLACED":
                    print("Testando confirmacao do pedido...")
                    success = self.order_service.confirm_order(order.id)
                    print(f"Confirmacao: {'SUCESSO' if success else 'FALHA'}")
                
                return True
            else:
                print("FALHA: Pedido nao encontrado")
                return False
                
        except Exception as e:
            print(f"FALHA: Erro ao testar pedido: {e}")
            return False

def main():
    """Funcao principal de teste"""
    tester = IfoodIntegrationTester()
    
    import argparse
    parser = argparse.ArgumentParser(description='Testador da Integracao iFood')
    
    parser.add_argument('--completo', action='store_true', 
                       help='Executar teste completo')
    parser.add_argument('--auth', action='store_true', 
                       help='Testar apenas autenticacao')
    parser.add_argument('--merchant', action='store_true', 
                       help='Testar apenas servico merchant')
    parser.add_argument('--orders', action='store_true', 
                       help='Testar apenas servico de pedidos')
    parser.add_argument('--polling', action='store_true', 
                       help='Testar apenas servico de polling')
    parser.add_argument('--pedido', type=str, 
                       help='Testar pedido especifico (ID do pedido)')
    parser.add_argument('--monitorar', action='store_true',
                       help='Monitorar polling por 2 minutos')
    
    args = parser.parse_args()
    
    if args.auth:
        success = tester.test_authentication()
        exit(0 if success else 1)
        
    elif args.merchant:
        success = tester.test_merchant_service()
        exit(0 if success else 1)
        
    elif args.orders:
        success = tester.test_orders_service()
        exit(0 if success else 1)
        
    elif args.polling:
        success = tester.test_polling_service()
        exit(0 if success else 1)
        
    elif args.pedido:
        success = tester.test_specific_order(args.pedido)
        exit(0 if success else 1)
        
    elif args.monitorar:
        monitor_polling()
        
    else:
        # Teste completo por padrão
        success = tester.run_complete_test()
        exit(0 if success else 1)

def monitor_polling():
    """Monitora o polling por 2 minutos"""
    print("INICIANDO MONITORAMENTO DO POLLING (2 minutos)")
    print("Pressione Ctrl+C para parar mais cedo")
    print("-" * 50)
    
    polling_service = IfoodPollingService()
    
    # Callback para mostrar novos pedidos
    def monitor_callback(data):
        if data['count'] > 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] NOVOS PEDIDOS: {data['count']}")
            for order in data['orders']:
                print(f"  - Pedido {order.display_id}: {order.customer.name} - R$ {order.total_price:.2f}")
    
    polling_service.register_callback('new_order', monitor_callback)
    
    # Callback para erros
    def error_callback(data):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ERRO: {data['error']}")
    
    polling_service.register_callback('error', error_callback)
    
    try:
        # Iniciar polling
        polling_service.start_polling()
        
        # Monitorar por 2 minutos (120 segundos)
        for i in range(120):
            time.sleep(1)
            # Mostrar status a cada 30 segundos
            if i % 30 == 0 and i > 0:
                status = polling_service.get_status()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Status: {status['stats']['successful_polls']} polls bem-sucedidos")
                
    except KeyboardInterrupt:
        print("\nMonitoramento interrompido pelo usuario")
    finally:
        polling_service.stop_polling()
        print("Monitoramento finalizado")

if __name__ == "__main__":
    main()