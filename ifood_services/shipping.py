import requests
import sys
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import IFOOD_API_URL, IFOOD_MERCHANT_ID
from ifood_services.auth import IfoodAuthService

# ======================== DATACLASSES ========================

@dataclass
class DeliveryQuote:
    id: str
    expiration_at: str
    created_at: str
    distance: float
    preparation_time: int
    gross_value: float
    discount: float
    raise_value: float
    net_value: float
    delivery_time_min: int
    delivery_time_max: int
    has_payment_methods: bool
    payment_methods: List[Dict[str, Any]]

@dataclass
class OrderItemOption:
    id: str
    name: str
    externalCode: str
    index: int
    quantity: int
    unitPrice: float
    price: float

@dataclass
class OrderItemCreate:
    id: str
    name: str
    externalCode: str
    quantity: int
    unitPrice: float
    price: float
    optionsPrice: float
    totalPrice: float
    options: List[OrderItemOption]

@dataclass
class OrderPaymentMethod:
    method: str
    type: str
    value: float
    card_brand: Optional[str] = None

@dataclass
class OrderPayment:
    methods: List[OrderPaymentMethod]

@dataclass
class OrderDeliveryAddress:
    postalCode: str
    streetNumber: str
    streetName: str
    complement: str
    neighborhood: str
    city: str
    state: str
    country: str
    reference: str
    latitude: float
    longitude: float

@dataclass
class OrderDelivery:
    merchantFee: float
    quoteId: str
    deliveryAddress: OrderDeliveryAddress

@dataclass
class OrderCustomer:
    name: str
    countryCode: str
    areaCode: str
    number: str

@dataclass
class OrderCreateRequest:
    customer: Dict[str, Any]
    delivery: Dict[str, Any]
    items: List[Dict[str, Any]]
    payments: Dict[str, Any]
    metadata: Dict[str, Any]


# ======================== IfoodShippingService ========================

class IfoodShipping:
    """
    Classe unificada para consultar disponibilidade de entrega
    e criar pedidos no iFood.
    """

    def __init__(self, merchant_id: str = None):
        self.base_url = f"{IFOOD_API_URL}/shipping/v1.0"
        self.merchant_id = merchant_id or IFOOD_MERCHANT_ID
        self.auth_service = IfoodAuthService()
        self.headers = {"Content-Type": "application/json"}

    def _get_headers(self):
        token = self.auth_service.get_token()
        return {**self.headers, "Authorization": f"Bearer {token}"}

    # ======================== MERCHANTS/{merchantsid} ========================

    def check_delivery_availability(self, latitude: float, longitude: float) -> Optional[DeliveryQuote]:
        """Consulta disponibilidade de entrega para pedidos fora da plataforma iFood."""
        url = f"{self.base_url}/merchants/{self.merchant_id}/deliveryAvailabilities"
        params = {"latitude": latitude, "longitude": longitude}

        try:
            headers = self._get_headers()
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                quote = DeliveryQuote(
                    id=data.get("id", ""),
                    expiration_at=data.get("expirationAt", ""),
                    created_at=data.get("createdAt", ""),
                    distance=data.get("distance", 0),
                    preparation_time=data.get("preparationTime", 0),
                    gross_value=data["quote"].get("grossValue", 0),
                    discount=data["quote"].get("discount", 0),
                    raise_value=data["quote"].get("raise", 0),
                    net_value=data["quote"].get("netValue", 0),
                    delivery_time_min=data["deliveryTime"].get("min", 0),
                    delivery_time_max=data["deliveryTime"].get("max", 0),
                    has_payment_methods=data.get("hasPaymentMethods", False),
                    payment_methods=data.get("paymentMethods", [])
                )
                return quote
            else:
                print(f"Erro ao consultar disponibilidade: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Erro ao consultar disponibilidade: {e}")
            return None

    def check_order_delivery_availability(self, order_id: str) -> Optional[DeliveryQuote]:
        """Consulta disponibilidade de entrega para pedidos da plataforma iFood."""
        url = f"{self.base_url}/orders/{order_id}/deliveryAvailabilities"
        try:
            headers = self._get_headers()
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"Erro ao consultar disponibilidade: {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            print(f"Erro ao consultar disponibilidade: {e}")
            return None

    def create_order(self, order_data: dict) -> dict:
        """Registra pedido fora da plataforma iFood e solicita entregador parceiro."""
        url = f"{self.base_url}/merchants/{self.merchant_id}/orders"
        try:
            headers = self._get_headers()
            resp = requests.post(url, headers=headers, json=order_data, timeout=15)
            if resp.status_code in [200, 201, 202]:
                return resp.json()
            elif resp.status_code == 204:
                return {}
            else:
                print(f"Erro ao criar pedido: {resp.status_code} - {resp.text}")
                return {}
        except Exception as e:
            print(f"Erro ao criar pedido: {e}")
            return {}

    def request_driver_for_order(self, order_id: str, quote_id: str) -> bool:
        """Solicita entregador para pedido da plataforma iFood."""
        url = f"{self.base_url}/orders/{order_id}/requestDriver"
        data = {"quoteId": quote_id}
        try:
            headers = self._get_headers()
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            if resp.status_code == 202:
                print("Solicitação de entregador registrada com sucesso!")
                return True
            else:
                print(f"Erro ao solicitar entregador: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"Erro ao solicitar entregador: {e}")
            return False

    def cancel_order(self, order_id: str, cancellation_code: str, reason: str) -> bool:
        """Cancela pedido fora da plataforma iFood."""
        url = f"{self.base_url}/orders/{order_id}/cancel"
        data = {"cancellationCode": cancellation_code, "reason": reason}
        try:
            headers = self._get_headers()
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            if resp.status_code == 202:
                print("Pedido cancelado com sucesso!")
                return True
            else:
                print(f"Erro ao cancelar pedido: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"Erro ao cancelar pedido: {e}")
            return False

    def cancel_request_driver(self, order_id: str) -> bool:
        """Cancela apenas a solicitação de entregador de um pedido da plataforma iFood."""
        url = f"{self.base_url}/orders/{order_id}/cancelRequestDriver"
        try:
            headers = self._get_headers()
            resp = requests.post(url, headers=headers, timeout=10)
            if resp.status_code == 202:
                print("Solicitação de cancelamento do entregador registrada!")
                return True
            else:
                print(f"Erro ao cancelar entregador: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"Erro ao cancelar entregador: {e}")
            return False

    def get_order_cancellation_reasons(self, order_id: str) -> list:
        """Consulta motivos/códigos de cancelamento disponíveis para o pedido."""
        url = f"{self.base_url}/orders/{order_id}/cancellationReasons"
        try:
            headers = self._get_headers()
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 204:
                print("Nenhum motivo disponível para cancelamento.")
                return []
            else:
                print(f"Erro ao buscar motivos de cancelamento: {resp.status_code} - {resp.text}")
                return []
        except Exception as e:
            print(f"Erro ao buscar motivos de cancelamento: {e}")
            return []

    def confirm_order_address(self, order_id: str) -> bool:
        """Confirma o endereço do pedido."""
        url = f"{self.base_url}/orders/{order_id}/userConfirmAddress"
        try:
            headers = self._get_headers()
            resp = requests.post(url, headers=headers, timeout=10)
            if resp.status_code == 202:
                print("Endereço confirmado com sucesso!")
                return True
            else:
                print(f"Erro ao confirmar endereço: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"Erro ao confirmar endereço: {e}")
            return False

    def request_address_change(self, order_id: str, address_data: dict) -> bool:
        """Solicita alteração do endereço de entrega."""
        url = f"{self.base_url}/orders/{order_id}/deliveryAddressChangeRequest"
        try:
            headers = self._get_headers()
            resp = requests.post(url, headers=headers, json=address_data, timeout=10)
            if resp.status_code == 202:
                print("Solicitação de alteração de endereço registrada!")
                return True
            else:
                print(f"Erro ao solicitar alteração de endereço: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"Erro ao solicitar alteração de endereço: {e}")
            return False

    def accept_address_change(self, order_id: str) -> bool:
        """Aceita alteração de endereço solicitada."""
        url = f"{self.base_url}/orders/{order_id}/acceptDeliveryAddressChange"
        try:
            headers = self._get_headers()
            resp = requests.post(url, headers=headers, timeout=10)
            if resp.status_code == 202:
                print("Alteração de endereço aceita!")
                return True
            else:
                print(f"Erro ao aceitar alteração de endereço: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"Erro ao aceitar alteração de endereço: {e}")
            return False

    def deny_address_change(self, order_id: str) -> bool:
        """Rejeita alteração de endereço solicitada."""
        url = f"{self.base_url}/orders/{order_id}/denyDeliveryAddressChange"
        try:
            headers = self._get_headers()
            resp = requests.post(url, headers=headers, timeout=10)
            if resp.status_code == 202:
                print("Alteração de endereço rejeitada!")
                return True
            else:
                print(f"Erro ao rejeitar alteração de endereço: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"Erro ao rejeitar alteração de endereço: {e}")
            return False

    def get_safe_delivery_score(self, order_id: str) -> dict:
        """Consulta o nível de confiança da entrega do pedido."""
        url = f"{self.base_url}/orders/{order_id}/safeDelivery"
        try:
            headers = self._get_headers()
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"Erro ao consultar score de entrega: {resp.status_code} - {resp.text}")
                return {}
        except Exception as e:
            print(f"Erro ao consultar score de entrega: {e}")
            return {}

    def track_order(self, order_id: str) -> dict:
        """Rastreia o pedido e retorna informações do entregador."""
        url = f"{self.base_url}/orders/{order_id}/tracking"
        try:
            headers = self._get_headers()
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"Erro ao rastrear pedido: {resp.status_code} - {resp.text}")
                return {}
        except Exception as e:
            print(f"Erro ao rastrear pedido: {e}")
            return {}

if __name__ == "__main__":
    service = IfoodShipping()

    latitude = -9.822384
    longitude = -67.948589

    # 1️⃣ Verificar disponibilidade de entrega (fora do iFood)
    quote = service.check_delivery_availability(latitude, longitude)
    if not quote:
        print("\n🚫 Nenhuma disponibilidade de entrega encontrada.")
        exit()

    print(f"\n✅ Entrega disponível! Quote ID: {quote.id}, Valor: R$ {quote.net_value:.2f}")

    # 2️⃣ Criar pedido fora do iFood
    order_data = {
        "orderType": "DELIVERY",
        "customer": {
            "name": "Artur Souza",
            "phone": {
                "type": "CUSTOMER",  # Adicionado para garantir elegibilidade!
                "countryCode": "55",
                "areaCode": "85",
                "number": "999999999"
            }
        },
        "delivery": {
            "merchantFee": 8.99,
            "quoteId": quote.id,
            "deliveryAddress": {
                "postalCode": "69923000",
                "streetNumber": "122",
                "streetName": "Rua Ramal Bujari",
                "neighborhood": "Centro",
                "city": "Bujari",
                "state": "AC",
                "country": "BR",
                "reference": "Perto da praça",
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude
                }
            }
        },
        "items": [
            {
                "id": "d40f9b0a-5e55-4df1-bc3c-1b1ec7fcb2c0",
                "name": "Pizza Mussarela",
                "externalCode": "PZ001",
                "quantity": 1,
                "unitPrice": 25.00,
                "price": 25.00,
                "optionsPrice": 0,
                "totalPrice": 25.00,
                "options": []
            }
        ],
        "payments": {
            "methods": [
                {
                    "method": "CREDIT",
                    "type": "OFFLINE",
                    "value": 33.99,
                    "card": {"brand": "VISA"}
                }
            ]
        },
        "metadata": {"elitab": "pedido_teste_01", "sit_4": "via_api"}
    }

    created_order = service.create_order(order_data)
    if not created_order or 'id' not in created_order:
        print("\n❌ Falha ao criar pedido.")
        exit()

    order_id = created_order['id']
    print("\n✅ Pedido criado com sucesso!")
    print(created_order)

    # 3️⃣ Confirmar endereço do pedido (só se o tipo for CUSTOMER)
    if order_data["customer"]["phone"].get("type") == "CUSTOMER":
        if service.confirm_order_address(order_id):
            print("\n📦 Endereço confirmado!")
        else:
            print("\n❌ Falha ao confirmar endereço.")
    else:
        print("\n⚠️ Endereço não pode ser confirmado pois o tipo do telefone não é CUSTOMER.")

    # 4️⃣ Consultar motivos de cancelamento
    reasons = service.get_order_cancellation_reasons(order_id)
    print("\n📋 Motivos de cancelamento disponíveis:")
    print(reasons)

    # 5️⃣ Consultar score de entrega
    score = service.get_safe_delivery_score(order_id)
    print("\n🔒 Score de entrega:")
    print(score)

    # 6️⃣ Rastrear pedido (só se houver entregador atribuído)
    tracking = service.track_order(order_id)
    if tracking:
        print("\n🚚 Rastreamento do pedido:")
        print(tracking)
    else:
        print("\n⚠️ Rastreamento indisponível. Aguarde atribuição do entregador.")

    # 7️⃣ Solicitar alteração de endereço
    novo_endereco = {
        "streetName": "Rua Nova",
        "streetNumber": "200",
        "complement": "",
        "reference": "Próximo ao mercado",
        "neighborhood": "Centro",
        "city": "Bujari",
        "state": "AC",
        "country": "BR",
        "coordinates": {
            "latitude": -9.822300,
            "longitude": -67.948600
        }
    }
    if service.request_address_change(order_id, novo_endereco):
        print("\n✏️ Solicitação de alteração de endereço registrada!")
    else:
        print("\n❌ Falha ao solicitar alteração de endereço.")

    # 8️⃣ Aceitar alteração de endereço
    if service.accept_address_change(order_id):
        print("\n✅ Alteração de endereço aceita!")
    else:
        print("\n❌ Falha ao aceitar alteração de endereço.")

    # 9️⃣ Rejeitar alteração de endereço
    if service.deny_address_change(order_id):
        print("\n🚫 Alteração de endereço rejeitada!")
    else:
        print("\n❌ Falha ao rejeitar alteração de endereço.")

    # 10️⃣ Cancelar pedido
    if reasons:
        cancel_code = reasons[0]['cancelCodeId']
        cancel_reason = reasons[0]['description']
        if service.cancel_order(order_id, cancel_code, cancel_reason):
            print("\n🛑 Pedido cancelado com sucesso!")
        else:
            print("\n❌ Falha ao cancelar pedido.")

    # 11️⃣ Cancelar solicitação de entregador
    if service.cancel_request_driver(order_id):
        print("\n🛑 Solicitação de entregador cancelada!")
    else:
        print("\n❌ Falha ao cancelar solicitação de entregador.")