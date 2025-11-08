import requests
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

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
    corporateName: str
    description: str
    created: str
    status: str

@dataclass
class MerchantDetails:
    id: str
    name: str
    corporateName: str
    description: str
    created: str
    status: str
    averageTicket: float
    operation: Dict[str, Any]
    address: Dict[str, Any]
    contacts: List[Dict[str, Any]]
    bankAccounts: List[Dict[str, Any]]
    deliveryZones: List[Dict[str, Any]]
    metadata: Dict[str, Any]

@dataclass
class Interruption:
    id: str
    description: str
    startTime: str
    endTime: str
    reason: str
    status: str

@dataclass
class OpeningHours:
    daysOfWeek: List[str]
    timePeriods: List[Dict[str, str]]


class IfoodMerchantService:
    """
    iFood Merchant API Service
    
    Serviço dedicado para operações Merchant da API iFood.
    PARA POLLING AUTOMÁTICO, use IfoodPollingService.
    
    Endpoints Implementados:
    - GET    /merchants                    - Listar todos os merchants
    - GET    /merchants/{merchantId}       - Obter detalhes do merchant
    - GET    /merchants/{merchantId}/status - Obter status do merchant
    - GET    /merchants/{merchantId}/interruptions - Listar interrupções
    - POST   /merchants/{merchantId}/interruptions - Criar interrupção
    - DELETE /merchants/{merchantId}/interruptions/{interruptionId} - Remover interrupção
    - GET    /merchants/{merchantId}/opening-hours - Obter horário de funcionamento
    - PUT    /merchants/{merchantId}/opening-hours - Atualizar horário de funcionamento
    """
    
    def __init__(self, is_test_environment: bool = True):
        self.base_url = f"{IFOOD_API_URL}/merchant/v1.0"
        self.merchant_id = IFOOD_MERCHANT_ID
        self.auth_service = IfoodAuthService()
        self.headers = {
            "Content-Type": "application/json"
        }
        self.is_test_environment = is_test_environment
        
        if is_test_environment:
            print("AMBIENTE DE TESTE DETECTADO - Merchant Service")

    def _get_headers(self):
        """Get headers with current access token"""
        token = self.auth_service.get_token()
        return {
            **self.headers,
            "Authorization": f"Bearer {token}"
        }
    
    def _parse_merchant_basic_info(self, data: Dict) -> MerchantBasicInfo:
        """Parse merchant basic info according to iFood standards"""
        return MerchantBasicInfo(
            id=data.get("id", ""),
            name=data.get("name", ""),
            corporateName=data.get("corporateName", ""),
            description=data.get("description", ""),
            created=data.get("created", ""),
            status=data.get("status", "")
        )
    
    def _parse_merchant_details(self, data: Dict) -> MerchantDetails:
        """Parse merchant details according to iFood standards"""
        return MerchantDetails(
            id=data.get("id", ""),
            name=data.get("name", ""),
            corporateName=data.get("corporateName", ""),
            description=data.get("description", ""),
            created=data.get("created", ""),
            status=data.get("status", ""),
            averageTicket=data.get("averageTicket", 0),
            operation=data.get("operation", {}),
            address=data.get("address", {}),
            contacts=data.get("contacts", []),
            bankAccounts=data.get("bankAccounts", []),
            deliveryZones=data.get("deliveryZones", []),
            metadata=data.get("metadata", {})
        )

    def _parse_interruption_response(self, data: Dict) -> Interruption:
        """Parse interruption response according to iFood standards"""
        return Interruption(
            id=data.get("id"),
            description=data.get("description"),
            startTime=data.get("startTime"),
            endTime=data.get("endTime"),
            reason=data.get("reason"),
            status=data.get("status")
        )
    
    def test_authentication(self):
        """Test authentication"""
        print("TESTANDO AUTENTICACAO...")
        try:
            token = self.auth_service.get_token()
            if token:
                print("AUTENTICACAO: OK")
                return True
            else:
                print("AUTENTICACAO: FALHOU")
                return False
        except Exception as e:
            print(f"ERRO NA AUTENTICACAO: {e}")
            return False

    def list_merchants(self) -> List[MerchantBasicInfo]:
        """List all available merchants - GET /merchants"""
        url = f"{self.base_url}/merchants"
        
        try:
            headers = self._get_headers()
            print("Listando merchants...")
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            merchants = []
            for merchant_data in data:
                merchant = self._parse_merchant_basic_info(merchant_data)
                merchants.append(merchant)

            print(f"Encontrados {len(merchants)} merchant(s)")
            for merchant in merchants:
                print(f"  {merchant.name} (ID: {merchant.id})")
                
            return merchants

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print("Endpoint de listagem de merchants nao encontrado")
            else:
                print(f"Erro HTTP {e.response.status_code}: {e.response.text}")
            return []
        except Exception as e:
            print(f"Erro ao listar merchants: {e}")
            return []

    def get_merchant_details(self, merchant_id: str = None) -> Optional[MerchantDetails]:
        """Get full details of a specific merchant - GET /merchants/{merchantId}"""
        if not merchant_id:
            merchant_id = self.merchant_id
            
        url = f"{self.base_url}/merchants/{merchant_id}"
        
        try:
            headers = self._get_headers()
            print(f"Obtendo detalhes do merchant {merchant_id}...")
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            merchant = self._parse_merchant_details(data)
            self._print_merchant_details(merchant)
            return merchant

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"Merchant {merchant_id} nao encontrado")
            else:
                print(f"Erro HTTP {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            print(f"Erro ao obter detalhes do merchant: {e}")
            return None

    def _print_merchant_details(self, merchant: MerchantDetails):
        """Displays merchant details in a formatted manner"""
        print(f"DETALHES DO MERCHANT: {merchant.name}")
        print("=" * 50)
        
        print(f"INFORMACOES BASICAS:")
        print(f"  ID: {merchant.id}")
        print(f"  Nome: {merchant.name}")
        print(f"  Razao Social: {merchant.corporateName}")
        print(f"  Descricao: {merchant.description}")
        print(f"  Status: {merchant.status}")
        print(f"  Criado em: {merchant.created}")
        print(f"  Ticket Medio: R$ {merchant.averageTicket:.2f}")
        
        if merchant.operation:
            print(f"OPERACAO:")
            op = merchant.operation
            print(f"  Status: {op.get('status', 'N/A')}")
            print(f"  Tipo: {op.get('type', 'N/A')}")
            print(f"  Inicio: {op.get('beginsAt', 'N/A')}")
            print(f"  Termino: {op.get('endsAt', 'N/A')}")
        
        if merchant.address:
            print(f"ENDERECO:")
            addr = merchant.address
            print(f"  Logradouro: {addr.get('street', 'N/A')}")
            print(f"  Numero: {addr.get('number', 'N/A')}")
            print(f"  Bairro: {addr.get('neighborhood', 'N/A')}")
            print(f"  Cidade: {addr.get('city', 'N/A')}")
            print(f"  Estado: {addr.get('state', 'N/A')}")
            print(f"  CEP: {addr.get('postalCode', 'N/A')}")

    def get_merchant_status(self, merchant_id: str = None) -> MerchantStatus:
        """Gets the status of a specific merchant - GET /merchants/{merchantId}/status"""
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
        """Displays formatted status"""
        merchant_info = f" ({merchant_id})" if merchant_id else ""
        
        state_icons = {
            MerchantState.OK: "[OK]",
            MerchantState.WARNING: "[ATENCAO]", 
            MerchantState.CLOSED: "[FECHADO]",
            MerchantState.ERROR: "[ERRO]",
            MerchantState.UNKNOWN: "[DESCONHECIDO]"
        }
        
        icon = state_icons.get(status.state, "[DESCONHECIDO]")
        print(f"{icon} Status{merchant_info}: {status.state.value}")
        
        if status.message:
            print(f"  {status.message}")

        if status.validations:
            print("  Validacoes:")
            for v in status.validations:
                status_icon = "[OK]" if v.passed else "[ERRO]"
                print(f"   {status_icon} {v.id}: {v.description}")
    
    def create_interruption(self, merchant_id: str, description: str, start_time: str, 
        end_time: str, reason: str = "TECHNICAL_ISSUE") -> Optional[Interruption]:
        """Cria uma interrupção no merchant - POST /merchants/{merchantId}/interruptions"""
        url = f"{self.base_url}/merchants/{merchant_id}/interruptions"
        
        payload = {
            "description": description,
            "startTime": start_time,
            "endTime": end_time,
            "reason": reason
        }
        
        try:
            headers = self._get_headers()
            print(f"Criando interrupção para merchant {merchant_id}...")
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            interruption = self._parse_interruption_response(data)
            print(f"Interrupção criada: ID {interruption.id}")
            return interruption
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                print(f"Erro 400 ao criar interrupção: {e.response.text}")
            else:
                print(f"Erro HTTP {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            print(f"Erro ao criar interrupção: {e}")
            return None

    def list_interruptions(self, merchant_id: str) -> List[Interruption]:
        """Lista interrupções do merchant - GET /merchants/{merchantId}/interruptions"""
        url = f"{self.base_url}/merchants/{merchant_id}/interruptions"
        
        try:
            headers = self._get_headers()
            print(f"Listando interrupções do merchant {merchant_id}...")
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            interruptions = []
            for item in data:
                interruption = self._parse_interruption_response(item)
                interruptions.append(interruption)
            
            print(f"Encontradas {len(interruptions)} interrupção(ões)")
            return interruptions
            
        except Exception as e:
            print(f"Erro ao listar interrupções: {e}")
            return []

    def get_merchant_interruptions(self, merchant_id: str) -> List[Interruption]:
        """Alias para list_interruptions - para padronização com controller"""
        return self.list_interruptions(merchant_id)

    def delete_interruption(self, merchant_id: str, interruption_id: str) -> bool:
        """Remove uma interrupção - DELETE /merchants/{merchantId}/interruptions/{interruptionId}"""
        url = f"{self.base_url}/merchants/{merchant_id}/interruptions/{interruption_id}"
        
        try:
            headers = self._get_headers()
            print(f"Deletando interrupção {interruption_id}...")
            resp = requests.delete(url, headers=headers, timeout=10)
            resp.raise_for_status()
            print(f"Interrupção {interruption_id} deletada com sucesso")
            return True
            
        except Exception as e:
            print(f"Erro ao deletar interrupção: {e}")
            return False

    def get_opening_hours(self, merchant_id: str) -> Optional[OpeningHours]:
        """Obtém horário de funcionamento - GET /merchants/{merchantId}/opening-hours"""
        url = f"{self.base_url}/merchants/{merchant_id}/opening-hours"
        
        try:
            headers = self._get_headers()
            print(f"Obtendo horário de funcionamento do merchant {merchant_id}...")
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            opening_hours = OpeningHours(
                daysOfWeek=data.get("daysOfWeek", []),
                timePeriods=data.get("timePeriods", [])
            )
            
            print(f"Horário obtido: {len(opening_hours.daysOfWeek)} dia(s) configurado(s)")
            return opening_hours
            
        except Exception as e:
            print(f"Erro ao obter horário de funcionamento: {e}")
            return None

    def update_opening_hours(self, merchant_id: str, opening_hours: OpeningHours) -> bool:
        """Atualiza horário de funcionamento - PUT /merchants/{merchantId}/opening-hours"""
        url = f"{self.base_url}/merchants/{merchant_id}/opening-hours"
        
        payload = {
            "daysOfWeek": opening_hours.daysOfWeek,
            "timePeriods": opening_hours.timePeriods
        }
        
        try:
            headers = self._get_headers()
            print(f"Atualizando horário de funcionamento do merchant {merchant_id}...")
            resp = requests.put(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            print("Horário de funcionamento atualizado com sucesso")
            return True
            
        except Exception as e:
            print(f"Erro ao atualizar horário de funcionamento: {e}")
            return False

def run_merchant_service_tests():
    """Testes básicos do Merchant Service (sem polling)"""
    print("TESTES MERCHANT SERVICE (SEM POLLING)")
    print("=" * 60)
    
    merchant_service = IfoodMerchantService(is_test_environment=True)
    
    print("1. AUTENTICACAO")
    print("-" * 30)
    auth_ok = merchant_service.test_authentication()
    if not auth_ok:
        print("Testes interrompidos - Autenticacao falhou")
        return

    print("2. LISTAR MERCHANTS")
    print("-" * 30)
    merchants = merchant_service.list_merchants()
    
    if merchants:
        print("3. DETALHES DO MERCHANT")
        print("-" * 30)
        merchant_service.get_merchant_details()
        
        print("4. STATUS DO MERCHANT")
        print("-" * 30)
        merchant_service.get_merchant_status()

    print("=" * 60)
    print("TESTES CONCLUIDOS!")
    print("Use IfoodPollingService para polling automático")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Servico Merchant iFood')
    parser.add_argument('--test', action='store_true', help='Executar testes básicos')
    
    args = parser.parse_args()
    
    if args.test:
        run_merchant_service_tests()