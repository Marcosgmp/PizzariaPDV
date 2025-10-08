import requests
import time
import threading
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Adiciona o diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import IFOOD_API_URL, IFOOD_MERCHANT_ID
from ifood_services.auth import IfoodAuthService

class MerchantState(str, Enum):
    OK = "OK"
    WARNING = "WARNING" 
    CLOSED = "CLOSED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"

@dataclass
class ReopenableInfo:
    reopenable: bool
    type: Optional[str] = None
    identifier: Optional[str] = None

@dataclass
class ValidationResult:
    id: str
    description: str
    passed: bool

@dataclass
class MerchantStatus:
    state: MerchantState
    validations: List[ValidationResult]
    reopenable: Optional[ReopenableInfo] = None
    message: Optional[str] = None

@dataclass
class MerchantBasicInfo:
    id: str
    name: str
    corporate_name: str
    description: str
    created: str
    status: str

@dataclass
class MerchantDetails:
    id: str
    name: str
    corporate_name: str
    description: str
    created: str
    status: str
    average_ticket: float
    operation: Dict[str, Any]
    address: Dict[str, Any]
    contacts: List[Dict[str, Any]]
    bank_accounts: List[Dict[str, Any]]
    delivery_zones: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class IfoodMerchantService:
    def __init__(self, is_test_environment: bool = True):
        self.base_url = f"{IFOOD_API_URL}/merchant/v1.0"
        self.merchant_id = IFOOD_MERCHANT_ID
        self.auth_service = IfoodAuthService()
        self.headers = {
            "Content-Type": "application/json"
        }
        self.last_polling_time = None
        self.polling_active = False
        self.polling_thread = None
        self.polling_interval = 30
        self.polling_counter = 0
        self._last_status = None
        self._last_status_time = None
        self.is_test_environment = is_test_environment
        
        if is_test_environment:
            print("🔧 AMBIENTE DE TESTE DETECTADO")

    def _get_headers(self):
        """
        Get headers with current access token
        """
        token = self.auth_service.get_token()
        return {
            **self.headers,
            "Authorization": f"Bearer {token}"
        }
    
    def test_authentication(self):
        """
        Test authentication
        """
        print("  TESTANDO AUTENTICAÇÃO...")
        try:
            token = self.auth_service.get_token()
            if token:
                print("✅ Autenticação: OK")
                return True
            else:
                print("❌ Autenticação: FALHOU")
                return False
        except Exception as e:
            print(f"❌ Erro na autenticação: {e}")
            return False

    def test_api_endpoints(self):
        """
        Test endpoints available
        """
        print("\n🔍 TESTANDO ENDPOINTS...")
        
        endpoints = {
            "list_merchants": f"{self.base_url}/merchants",
            "merchant_details": f"{self.base_url}/merchants/{self.merchant_id}",
            "merchant_status": f"{self.base_url}/merchants/{self.merchant_id}/status",
        }
        
        available_endpoints = []
        
        for name, url in endpoints.items():
            try:
                headers = self._get_headers()
                resp = requests.get(url, headers=headers, timeout=10)
                
                if resp.status_code == 200:
                    print(f"✅ {name}: DISPONÍVEL")
                    available_endpoints.append(name)
                else:
                    print(f"⚠️  {name}: STATUS {resp.status_code}")
                    
            except Exception as e:
                print(f"❌ {name}: ERRO - {e}")
        
        return available_endpoints

    def list_merchants(self) -> List[MerchantBasicInfo]:
        """
        List all available merchants
        """
        url = f"{self.base_url}/merchants"
        
        try:
            headers = self._get_headers()
            print(f"🔗 Listando merchants...")
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            merchants = []
            for merchant_data in data:
                merchant = MerchantBasicInfo(
                    id=merchant_data.get("id", ""),
                    name=merchant_data.get("name", ""),
                    corporate_name=merchant_data.get("corporateName", ""),
                    description=merchant_data.get("description", ""),
                    created=merchant_data.get("created", ""),
                    status=merchant_data.get("status", "")
                )
                merchants.append(merchant)

            print(f"✅ Encontrados {len(merchants)} merchant(s)")
            for merchant in merchants:
                print(f"   🏪 {merchant.name} (ID: {merchant.id})")
                
            return merchants

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print("❌ Endpoint de listagem de merchants não encontrado")
            else:
                print(f"❌ Erro HTTP {e.response.status_code}: {e.response.text}")
            return []
        except Exception as e:
            print(f"❌ Erro ao listar merchants: {e}")
            return []

    def get_merchant_details(self, merchant_id: str = None) -> Optional[MerchantDetails]:
        """
        get full details of a specific merchant
        """
        if not merchant_id:
            merchant_id = self.merchant_id
            
        url = f"{self.base_url}/merchants/{merchant_id}"
        
        try:
            headers = self._get_headers()
            print(f"🔗 Obtendo detalhes do merchant {merchant_id}...")
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Processar dados do merchant
            merchant = MerchantDetails(
                id=data.get("id", ""),
                name=data.get("name", ""),
                corporate_name=data.get("corporateName", ""),
                description=data.get("description", ""),
                created=data.get("created", ""),
                status=data.get("status", ""),
                average_ticket=data.get("averageTicket", 0),
                operation=data.get("operation", {}),
                address=data.get("address", {}),
                contacts=data.get("contacts", []),
                bank_accounts=data.get("bankAccounts", []),
                delivery_zones=data.get("deliveryZones", []),
                metadata=data.get("metadata", {})
            )

            self._print_merchant_details(merchant)
            return merchant

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"❌ Merchant {merchant_id} não encontrado")
            else:
                print(f"❌ Erro HTTP {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            print(f"❌ Erro ao obter detalhes do merchant: {e}")
            return None

    def _print_merchant_details(self, merchant: MerchantDetails):
        """
        Displays merchant details in a formatted manner
        """
        print(f"\n DETALHES DO MERCHANT: {merchant.name}")
        print("=" * 50)
        
        print(f"  INFORMAÇÕES BÁSICAS:")
        print(f"   ID: {merchant.id}")
        print(f"   Nome: {merchant.name}")
        print(f"   Razão Social: {merchant.corporate_name}")
        print(f"   Descrição: {merchant.description}")
        print(f"   Status: {merchant.status}")
        print(f"   Criado em: {merchant.created}")
        print(f"   Ticket Médio: R$ {merchant.average_ticket:.2f}")
        
        if merchant.operation:
            print(f"\n  OPERAÇÃO:")
            op = merchant.operation
            print(f"   Status: {op.get('status', 'N/A')}")
            print(f"   Tipo: {op.get('type', 'N/A')}")
            print(f"   Início: {op.get('beginsAt', 'N/A')}")
            print(f"   Término: {op.get('endsAt', 'N/A')}")
        
        if merchant.address:
            print(f"\n📍 ENDEREÇO:")
            addr = merchant.address
            print(f"   Logradouro: {addr.get('street', 'N/A')}")
            print(f"   Número: {addr.get('number', 'N/A')}")
            print(f"   Bairro: {addr.get('neighborhood', 'N/A')}")
            print(f"   Cidade: {addr.get('city', 'N/A')}")
            print(f"   Estado: {addr.get('state', 'N/A')}")
            print(f"   CEP: {addr.get('postalCode', 'N/A')}")
        
        if merchant.contacts:
            print(f"\n📞 CONTATOS:")
            for contact in merchant.contacts[:3]:  # Mostrar apenas os primeiros 3
                print(f"   - {contact.get('name', 'N/A')}: {contact.get('number', 'N/A')}")
        
        if merchant.delivery_zones:
            print(f"\n🚚 ZONAS DE ENTREGA: {len(merchant.delivery_zones)} zona(s)")
            for zone in merchant.delivery_zones[:2]:  # Mostrar apenas as primeiras 2
                print(f"   - {zone.get('name', 'N/A')} (R$ {zone.get('deliveryPrice', 0):.2f})")
        
        if merchant.bank_accounts:
            print(f"\n  CONTAS BANCÁRIAS: {len(merchant.bank_accounts)} conta(s)")

    def get_merchant_status(self, merchant_id: str = None) -> MerchantStatus:
        """
        Gets the status of a specific merchant
        """
        if not merchant_id:
            merchant_id = self.merchant_id
            
        url = f"{self.base_url}/merchants/{merchant_id}/status"

        try:
            headers = self._get_headers()
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            self.last_polling_time = datetime.now()

            # Processar dados
            state = MerchantState(data.get("state", "UNKNOWN"))
            
            validations_data = data.get("validations", [])
            validations = []
            
            for v in validations_data:
                message_data = v.get("message", {})
                description = message_data.get("subtitle", "") or message_data.get("title", "")
                passed = v.get("state") == "OK"
                
                validations.append(ValidationResult(
                    id=v.get("id", ""),
                    description=description,
                    passed=passed
                ))
            
            reopenable_data = data.get("reopenable")
            reopenable = None
            if reopenable_data:
                reopenable = ReopenableInfo(
                    reopenable=reopenable_data.get("reopenable", False),
                    type=reopenable_data.get("type"),
                    identifier=reopenable_data.get("identifier")
                )

            message_data = data.get("message", {})
            message = message_data.get("subtitle", "") or message_data.get("title", "")

            status = MerchantStatus(
                state=state,
                validations=validations,
                reopenable=reopenable,
                message=message
            )

            self._print_status(status, merchant_id)
            return status

        except Exception as e:
            error_msg = f"Erro ao obter status: {e}"
            print(f"  {error_msg}")
            return MerchantStatus(
                state=MerchantState.ERROR,
                validations=[],
                message=error_msg
            )

    def _print_status(self, status: MerchantStatus, merchant_id: str = None):
        """
        Displays formatted status
        """
        merchant_info = f" ({merchant_id})" if merchant_id else ""
        
        state_emojis = {
            MerchantState.OK: "🟢",
            MerchantState.WARNING: "🟡", 
            MerchantState.CLOSED: "⚫",
            MerchantState.ERROR: "🔴",
            MerchantState.UNKNOWN: "⚪"
        }
        
        emoji = state_emojis.get(status.state, "⚪")
        print(f"{emoji} Status{merchant_info}: {status.state.value}")
        
        if status.message:
            print(f"     {status.message}")

        if status.validations:
            print("     Validações:")
            for v in status.validations:
                status_icon = "✅" if v.passed else "❌"
                print(f"      {status_icon} {v.id}: {v.description}")

    # Métodos de polling
    def start_polling(self):
        """
        Start automatic polling
        """
        if self.polling_active:
            print("⚠️ Polling já está ativo")
            return

        self.polling_active = True
        self.polling_thread = threading.Thread(target=self._polling_worker, daemon=True)
        self.polling_thread.start()
        print("🔄 Polling iniciado (30 segundos)")

    def stop_polling(self):
        """
        Stop automatic polling
        """
        self.polling_active = False
        if self.polling_thread:
            self.polling_thread.join(timeout=5)
        print("🛑 Polling parado")

    def _polling_worker(self):
        """
        Worker thread para polling regular
        """
        while self.polling_active:
            try:
                # Polling básico de status
                self.get_merchant_status()
                
                self.last_polling_time = datetime.now()
                self.polling_counter += 1
                
            except Exception as e:
                print(f"❌ Erro no polling: {e}")
            
            time.sleep(self.polling_interval)

    def is_polling_healthy(self) -> bool:
        """
        Check if polling is healthy
        """
        if not self.last_polling_time:
            return False
        time_since_last_poll = (datetime.now() - self.last_polling_time).total_seconds()
        return time_since_last_poll <= self.polling_interval + 10



#daqui pra frente só teste do gpto
# TESTES COMPLETOS COM NOVAS FUNCIONALIDADES
def run_complete_merchant_tests():
    """
    Testes completos das funcionalidades de merchant
    """
    print("🧪 TESTES COMPLETOS - MERCHANT SERVICE")
    print("=" * 60)
    
    merchant_service = IfoodMerchantService(is_test_environment=True)
    
    # Teste 1: Autenticação
    print("\n1️⃣ AUTENTICAÇÃO")
    print("-" * 30)
    auth_ok = merchant_service.test_authentication()
    if not auth_ok:
        print("❌ Testes interrompidos - Autenticação falhou")
        return

    # Teste 2: Listar merchants
    print("\n2️⃣ LISTAR MERCHANTS")
    print("-" * 30)
    merchants = merchant_service.list_merchants()
    
    if merchants:
        # Teste 3: Detalhes do merchant atual
        print("\n3️⃣ DETALHES DO MERCHANT ATUAL")
        print("-" * 30)
        current_merchant = merchant_service.get_merchant_details()
        
        # Teste 4: Status do merchant atual
        print("\n4️⃣ STATUS DO MERCHANT ATUAL")
        print("-" * 30)
        status = merchant_service.get_merchant_status()
        
        # Teste 5: Status de outros merchants (se houver múltiplos)
        if len(merchants) > 1:
            print("\n5️⃣ STATUS DE OUTROS MERCHANTS")
            print("-" * 30)
            for merchant in merchants[1:3]:  # Limitar a 2 merchants adicionais
                print(f"\n📊 Status do merchant: {merchant.name}")
                merchant_service.get_merchant_status(merchant.id)
    else:
        print("ℹ️  Nenhum merchant encontrado para teste")
        
        # Tentar pelo menos o merchant atual
        print("\n3️⃣ DETALHES DO MERCHANT CONFIGURADO")
        print("-" * 30)
        merchant_service.get_merchant_details()
        
        print("\n4️⃣ STATUS DO MERCHANT CONFIGURADO")
        print("-" * 30)
        merchant_service.get_merchant_status()

    # Teste 6: Endpoints disponíveis
    print("\n6️⃣ ENDPOINTS DISPONÍVEIS")
    print("-" * 30)
    merchant_service.test_api_endpoints()

    print("\n" + "=" * 60)
    print("🎯 TESTES CONCLUÍDOS!")

def interactive_merchant_explorer():
    """Explorador interativo de merchants"""
    print("🔍 EXPLORADOR INTERATIVO DE MERCHANTS")
    print("=" * 50)
    
    merchant_service = IfoodMerchantService(is_test_environment=True)
    
    while True:
        print("\nOpções:")
        print("1. Listar todos os merchants")
        print("2. Ver detalhes do merchant atual")
        print("3. Ver status do merchant atual") 
        print("4. Testar endpoints")
        print("5. Sair")
        
        choice = input("\nEscolha uma opção (1-5): ").strip()
        
        if choice == "1":
            merchants = merchant_service.list_merchants()
            if merchants:
                print(f"\n🏪 Merchants encontrados: {len(merchants)}")
                
        elif choice == "2":
            merchant_service.get_merchant_details()
            
        elif choice == "3":
            merchant_service.get_merchant_status()
            
        elif choice == "4":
            merchant_service.test_api_endpoints()
            
        elif choice == "5":
            print("👋 Saindo...")
            break
            
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Serviço Merchant iFood')
    parser.add_argument('--test', action='store_true', help='Executar testes completos')
    parser.add_argument('--explore', action='store_true', help='Modo explorador interativo')
    parser.add_argument('--list', action='store_true', help='Apenas listar merchants')
    parser.add_argument('--details', action='store_true', help='Apenas detalhes do merchant')
    parser.add_argument('--status', action='store_true', help='Apenas status do merchant')
    
    args = parser.parse_args()
    
    if args.test:
        run_complete_merchant_tests()
    elif args.explore:
        interactive_merchant_explorer()
    elif args.list:
        service = IfoodMerchantService