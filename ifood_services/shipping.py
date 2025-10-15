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
        """
        Consulta disponibilidade de entrega para coordenadas.
        """
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

    def create_order(self, order_data: dict) -> dict:
        """
        Cria um pedido no iFood com os dados fornecidos.
        """
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
    # ======================== ORDER ========================

    
    def track_order(self, order_id: str) -> dict:
        """
        Retorna informações de rastreio de um pedido.
        GET /orders/:id/tracking
        """
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

    # 1️⃣ Verificar disponibilidade de entrega
    quote = service.check_delivery_availability(latitude, longitude)

    if quote:
        print(f"\n✅ Entrega disponível! Quote ID: {quote.id}, Valor: R$ {quote.net_value:.2f}")

        # 2️⃣ Criar pedido
        order_data = {
            "orderType": "DELIVERY",
            "customer": {
                "name": "Artur Souza",
                "phone": {
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
        if created_order:
            print("\n✅ Pedido criado com sucesso!")
            print(created_order)
        else:
            print("\n❌ Falha ao criar pedido.")
    else:
        print("\n🚫 Nenhuma disponibilidade de entrega encontrada.")