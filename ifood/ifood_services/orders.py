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
    PREPARATION_STARTED = "PREPARATION_STARTED"
    SEPARATION_STARTED = "SEPARATION_STARTED"
    SEPARATION_ENDED = "SEPARATION_ENDED"
    CONCLUDED = "CONCLUDED"

class OrderType(str, Enum):
    DELIVERY = "DELIVERY"
    TAKEOUT = "TAKEOUT"
    DINE_IN = "DINE_IN"

class OrderTiming(str, Enum):
    IMMEDIATE = "IMMEDIATE"
    SCHEDULED = "SCHEDULED"

class EventCode(str, Enum):
    PLC = "PLC"
    CFM = "CFM"
    RTP = "RTP"
    DIS = "DIS"
    CON = "CON"
    CAN = "CAN"
    CAR = "CAR"
    INT = "INT"
    PST = "PST"
    OPA = "OPA"
    ADR = "ADR"
    NEG = "NEG"
    DGR = "DGR"
    RQC = "RQC"

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
    index: int

@dataclass
class Payment:
    method: str
    value: float
    currency: str
    prepaid: bool
    type: str
    change_for: float = 0.0
    card_issuer: str = ""

@dataclass
class Benefit:
    value: float
    target: str
    target_id: str = ""
    sponsorship_values: List[Dict] = None
    sponsorship: str = ""

@dataclass
class Coupon:
    value: float
    code: str
    benefits: List[Benefit]

@dataclass
class Order:
    id: str
    display_id: str
    reference: str
    short_reference: str
    created_at: str
    type: OrderType
    status: OrderStatus
    timing: OrderTiming
    total_price: float
    sub_total: float
    delivery_fee: float
    delivery_address: Address
    customer: Customer
    items: List[Item]
    payments: List[Payment]
    coupons: List[Coupon]
    preparation_time: int
    observations: str
    delivery_observations: str
    schedule: Dict[str, Any]
    is_test: bool
    pickup_code: str = ""
    preparation_start_date_time: str = ""
    merchant_instructions: str = ""

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

@dataclass
class CancellationReason:
    code: str
    label: str
    expires_at: str

@dataclass
class Negotiation:
    id: str
    type: str
    status: str
    created_at: str
    updated_at: str
    proposal: Dict[str, Any]

class IfoodOrderService:
    def __init__(self, merchant_id: str = None):
        self.base_url = "https://merchant-api.ifood.com.br/order/v1.0"
        self.merchant_id = merchant_id
        self.auth_service = IfoodAuthService()
        self.headers = {
            "Content-Type": "application/json"
        }
        self._acknowledged_events = set()
        self._processed_orders = set()

    def _get_headers(self):
        token = self.auth_service.get_token()
        headers = {
            **self.headers,
            "Authorization": f"Bearer {token}"
        }
        
        # ✅ HEADER OBRIGATÓRIO para homologação
        if self.merchant_id:
            headers["x-polling-merchants"] = self.merchant_id
            
        return headers

    def poll_events(self) -> List[OrderEvent]:
        url = f"{self.base_url}/events:polling"
        
        try:
            headers = self._get_headers()
            
            # ✅ PARÂMETROS OBRIGATÓRIOS para homologação
            params = {
                "groups": "ORDER",
                "types": "PLC,CFM,CAN,DIS,RTP,CON,PST,OPA,ADR,NEG,CAR,DGR,RQC",
                "categories": "ALL",  # ✅ RECEBE TODAS CATEGORIAS
                "excludeHeartbeat": "true"  # ✅ PARA INTEGRADORAS LOGÍSTICAS
            }
            
            print("🔄 Polling de eventos (com parâmetros de homologação)...")
            resp = requests.get(url, headers=headers, params=params, timeout=30)  # ✅ TIMEOUT 30s
            
            if resp.status_code == 200:
                events_data = resp.json()
                events = []
                event_ids_to_acknowledge = []
                
                for event_data in events_data:
                    try:
                        event_id = event_data.get("id", "")
                        order_id = event_data.get("orderId", "")
                        
                        if event_id in self._acknowledged_events:
                            print(f"✅ Evento {event_id} já processado")
                            continue
                            
                        event_code = event_data.get("code", "")
                        
                        code_mapping = {
                            "PLC": EventCode.PLC, "CFM": EventCode.CFM, "RTP": EventCode.RTP,
                            "DIS": EventCode.DIS, "CON": EventCode.CON, "CAN": EventCode.CAN,
                            "CAR": EventCode.CAR, "INT": EventCode.INT, "PST": EventCode.PST,
                            "OPA": EventCode.OPA, "ADR": EventCode.ADR, "NEG": EventCode.NEG,
                            "DGR": EventCode.DGR, "RQC": EventCode.RQC
                        }
                        
                        if event_code in code_mapping:
                            event = OrderEvent(
                                id=event_id,
                                code=code_mapping[event_code],
                                order_id=order_id,
                                merchant_id=event_data.get("merchantId", ""),
                                created_at=event_data.get("createdAt", ""),
                                full_code=event_data.get("fullCode", ""),
                                sales_channel=event_data.get("salesChannel", ""),
                                metadata=event_data.get("metadata", {})
                            )
                            events.append(event)
                            event_ids_to_acknowledge.append(event_id)
                        else:
                            print(f"⚠️  Código desconhecido: {event_code}")
                            event_ids_to_acknowledge.append(event_id)
                        
                    except Exception as e:
                        print(f"❌ Erro ao processar evento: {e}")
                        continue
                
                # ✅ ACKNOWLEDGMENT IMEDIATO - CRÍTICO
                if event_ids_to_acknowledge:
                    self.acknowledge_events(event_ids_to_acknowledge)
                
                print(f"✅ {len(events)} evento(s) processado(s)")
                return events
                
            elif resp.status_code == 204:
                print("ℹ️  Nenhum evento novo")
                return []
            else:
                print(f"❌ Erro no polling: {resp.status_code} - {resp.text}")
                return []
                
        except Exception as e:
            print(f"❌ Exception no polling: {e}")
            return []
        
    def acknowledge_events(self, event_ids: List[str]) -> bool:
        url = f"{self.base_url}/events/acknowledgment"
        
        try:
            headers = self._get_headers()
            data = [{"id": event_id} for event_id in event_ids]
            
            resp = requests.post(url, headers=headers, json=data, timeout=30)  # ✅ TIMEOUT 30s
            
            if resp.status_code in [200, 202, 204]:
                for event_id in event_ids:
                    self._acknowledged_events.add(event_id)
                print(f"✅ {len(event_ids)} evento(s) confirmado(s)")
                return True
            else:
                print(f"❌ Erro no ACK: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"❌ Exception no ACK: {e}")
            return False

    def get_order_details(self, order_id: str) -> Optional[Order]:
        url = f"{self.base_url}/orders/{order_id}"
        
        try:
            headers = self._get_headers()
            print(f"Buscando detalhes do pedido {order_id}...")
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                order_data = resp.json()
                order = self._parse_order_data(order_data)
                
                if order:
                    self._print_order_details(order)
                    return order
                else:
                    print("Erro ao processar dados do pedido")
                    return None
            elif resp.status_code == 404:
                print("Pedido nao encontrado")
                return None
            else:
                print(f"Erro ao buscar detalhes do pedido: {resp.status_code} - {resp.text}")
                return None
                
        except Exception as e:
            print(f"Erro ao buscar detalhes do pedido: {e}")
            return None

    def _parse_order_data(self, order_data: Dict) -> Optional[Order]:
        try:
            if isinstance(order_data, list):
                if len(order_data) > 0:
                    order_data = order_data[0]
                else:
                    return None
            
            order_id = order_data.get("id", "")
            display_id = order_data.get("displayId", "")
            created_at = order_data.get("createdAt", "")
            
            order_type_str = order_data.get("orderType", "DELIVERY")
            order_type = OrderType.DELIVERY if order_type_str.upper() == "DELIVERY" else (
                OrderType.TAKEOUT if order_type_str.upper() == "TAKEOUT" else OrderType.DINE_IN
            )
            
            timing_str = order_data.get("orderTiming", "IMMEDIATE")
            timing = OrderTiming.SCHEDULED if timing_str.upper() == "SCHEDULED" else OrderTiming.IMMEDIATE
            
            status_str = order_data.get("status", "PLACED")
            status_map = {
                "PLACED": OrderStatus.PLACED,
                "CONFIRMED": OrderStatus.CONFIRMED,
                "CANCELLED": OrderStatus.CANCELLED,
                "DISPATCHED": OrderStatus.DISPATCHED,
                "DELIVERED": OrderStatus.DELIVERED,
                "INTEGRATED": OrderStatus.INTEGRATED,
                "READY_TO_PICKUP": OrderStatus.READY_TO_PICKUP,
                "PREPARATION_STARTED": OrderStatus.PREPARATION_STARTED,
                "SEPARATION_STARTED": OrderStatus.SEPARATION_STARTED,
                "SEPARATION_ENDED": OrderStatus.SEPARATION_ENDED,
                "CONCLUDED": OrderStatus.CONCLUDED
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
            
            for index, item_data in enumerate(items_data):
                item = Item(
                    id=item_data.get("id", ""),
                    name=item_data.get("name", ""),
                    quantity=item_data.get("quantity", 0),
                    price=item_data.get("unitPrice", 0),
                    total_price=item_data.get("totalPrice", 0),
                    observations=item_data.get("observations", ""),
                    external_code=item_data.get("externalCode", ""),
                    index=index + 1
                )
                items.append(item)
            
            payments = []
            payments_data = order_data.get("payments", {})
            methods_data = payments_data.get("methods", [])
            
            for payment_data in methods_data:
                card_data = payment_data.get("card", {})
                card_issuer = card_data.get("issuer", "") if card_data else ""
                
                change_for = payment_data.get("changeFor", 0)
                
                payment = Payment(
                    method=payment_data.get("method", ""),
                    value=payment_data.get("value", 0),
                    currency=payment_data.get("currency", "BRL"),
                    prepaid=payment_data.get("prepaid", False),
                    type=payment_data.get("type", ""),
                    change_for=change_for,
                    card_issuer=card_issuer
                )
                payments.append(payment)
            
            coupons = []
            benefits_data = order_data.get("benefits", [])
            
            for benefit_data in benefits_data:
                benefit = Benefit(
                    value=benefit_data.get("value", 0),
                    target=benefit_data.get("target", ""),
                    target_id=benefit_data.get("targetId", ""),
                    sponsorship_values=benefit_data.get("sponsorshipValues", []),
                    sponsorship=benefit_data.get("sponsorship", "")
                )
                
                coupon = Coupon(
                    value=benefit.value,
                    code=benefit_data.get("code", ""),
                    benefits=[benefit]
                )
                coupons.append(coupon)
            
            preparation_time = delivery_data.get("preparationTime", 0)
            observations = delivery_data.get("observations", "")
            pickup_code = delivery_data.get("pickupCode", "")
            preparation_start_date_time = order_data.get("preparationStartDateTime", "")
            merchant_instructions = delivery_data.get("merchantInstructions", "")
            
            schedule = {}
            scheduling_data = order_data.get("scheduling", {})
            if scheduling_data:
                schedule = {
                    "delivery_date_time_start": scheduling_data.get("deliveryDateTimeStart"),
                    "delivery_date_time_end": scheduling_data.get("deliveryDateTimeEnd"),
                }
            
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
                timing=timing,
                total_price=total_price,
                sub_total=sub_total_price,
                delivery_fee=delivery_fee_price,
                delivery_address=address,
                customer=customer,
                items=items,
                payments=payments,
                coupons=coupons,
                preparation_time=preparation_time,
                observations=observations,
                delivery_observations=observations,
                schedule=schedule,
                is_test=order_data.get("isTest", False),
                pickup_code=pickup_code,
                preparation_start_date_time=preparation_start_date_time,
                merchant_instructions=merchant_instructions
            )
            
            print(f"Pedido processado com sucesso: {order.short_reference}")
            return order
            
        except Exception as e:
            print(f"Erro critico ao processar dados do pedido: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _print_order_details(self, order: Order):
        print(f"\n{'='*60}")
        print(f"PEDIDO: {order.short_reference}")
        print(f"{'='*60}")
        
        print(f"INFORMACOES BASICAS:")
        print(f"  ID: {order.id}")
        print(f"  Display ID: {order.display_id}")
        print(f"  Referencia: {order.reference}")
        print(f"  Data: {order.created_at}")
        print(f"  Tipo: {order.type.value}")
        print(f"  Timing: {order.timing.value}")
        print(f"  Status: {order.status.value}")
        print(f"  Teste: {'SIM' if order.is_test else 'NAO'}")
        
        if order.timing == OrderTiming.SCHEDULED and order.schedule:
            print(f"  AGENDADO: {order.schedule.get('delivery_date_time_start', 'N/A')}")
        
        print(f"VALORES:")
        print(f"  Subtotal: R$ {order.sub_total:.2f}")
        print(f"  Taxa de entrega: R$ {order.delivery_fee:.2f}")
        print(f"  Total: R$ {order.total_price:.2f}")
        
        if order.coupons:
            print(f"CUPONS E DESCONTOS:")
            for coupon in order.coupons:
                for benefit in coupon.benefits:
                    sponsor = benefit.sponsorship or "IFOOD"
                    if benefit.sponsorship_values:
                        for sponsorship in benefit.sponsorship_values:
                            sponsor = sponsorship.get("name", "IFOOD")
                    print(f"  Desconto: R$ {benefit.value:.2f} - Responsavel: {sponsor}")
        
        print(f"CLIENTE:")
        print(f"  Nome: {order.customer.name}")
        print(f"  Telefone: {order.customer.phone}")
        if order.customer.document_number:
            print(f"  CPF/CNPJ: {order.customer.document_number}")
        
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
        for item in order.items:
            print(f"  {item.index}. {item.name}")
            print(f"     Codigo: {item.external_code}")
            print(f"     Quantidade: {item.quantity}")
            print(f"     Preco unitario: R$ {item.price:.2f}")
            print(f"     Total: R$ {item.total_price:.2f}")
            if item.observations:
                print(f"     Observacoes: {item.observations}")
        
        print(f"PAGAMENTOS ({len(order.payments)}):")
        for payment in order.payments:
            tipo = "Pre-pago" if payment.prepaid else "Pendente"
            method_info = f"{payment.method}"
            
            if payment.method.upper() == "CREDIT_CARD" and payment.card_issuer:
                method_info += f" ({payment.card_issuer})"
            elif payment.method.upper() == "CASH" and payment.change_for > 0:
                method_info += f" - Troco para: R$ {payment.change_for:.2f}"
                
            print(f"  - {method_info}: R$ {payment.value:.2f} ({tipo})")
        
        if order.pickup_code:
            print(f"CODIGO DE COLETA: {order.pickup_code}")
        
        if order.observations:
            print(f"OBSERVACOES DA ENTREGA: {order.observations}")
        
        if order.merchant_instructions:
            print(f"  INSTRUCOES DO MERCHANT: {order.merchant_instructions}")
        
        print(f"{'='*60}\n")

    def get_cancellation_reasons(self, order_id: str) -> List[CancellationReason]:
        url = f"{self.base_url}/orders/{order_id}/cancellationReasons"
        
        try:
            headers = self._get_headers()
            print(f"Buscando motivos de cancelamento para pedido {order_id}...")
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                reasons_data = resp.json()
                reasons = []
                
                for reason_data in reasons_data:
                    reason = CancellationReason(
                        code=reason_data.get("code", ""),
                        label=reason_data.get("label", ""),
                        expires_at=reason_data.get("expiresAt", "")
                    )
                    reasons.append(reason)
                
                print(f"Encontrados {len(reasons)} motivos de cancelamento")
                return reasons
            else:
                print(f"Erro ao buscar motivos de cancelamento: {resp.status_code} - {resp.text}")
                return []
                
        except Exception as e:
            print(f"Erro ao buscar motivos de cancelamento: {e}")
            return []

    def request_cancellation(self, order_id: str, reason_code: str, reason: str = "") -> bool:
        url = f"{self.base_url}/orders/{order_id}/requestCancellation"
        
        try:
            headers = self._get_headers()
            data = {
                "reasonCode": reason_code,
                "reason": reason or f"Cancelado por motivo: {reason_code}"
            }
            
            print(f"Solicitando cancelamento do pedido {order_id}...")
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            
            if resp.status_code == 202:
                print("Solicitacao de cancelamento enviada com sucesso!")
                return True
            else:
                print(f"Erro ao solicitar cancelamento: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao solicitar cancelamento: {e}")
            return False

    def start_preparation(self, order_id: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}/startPreparation"
        
        try:
            headers = self._get_headers()
            print(f"Iniciando preparo do pedido {order_id}...")
            resp = requests.post(url, headers=headers, timeout=10)
            
            if resp.status_code in [200, 202, 204]:
                print("Preparo iniciado com sucesso!")
                return True
            else:
                print(f"Erro ao iniciar preparo: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao iniciar preparo: {e}")
            return False

    def ready_to_pickup(self, order_id: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}/readyToPickup"
        
        try:
            headers = self._get_headers()
            print(f"Marcando pedido {order_id} como pronto para retirada...")
            resp = requests.post(url, headers=headers, timeout=10)
            
            if resp.status_code in [200, 202, 204]:
                print("Pedido marcado como pronto para retirada!")
                return True
            else:
                print(f"Erro ao marcar como pronto: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao marcar como pronto: {e}")
            return False

    def dispatch_order(self, order_id: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}/dispatch"
        
        try:
            headers = self._get_headers()
            print(f"Despachando pedido {order_id}...")
            resp = requests.post(url, headers=headers, timeout=10)
            
            if resp.status_code in [200, 202, 204]:
                print("Pedido despachado com sucesso!")
                return True
            else:
                print(f"Erro ao despachar pedido: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao despachar pedido: {e}")
            return False

    def validate_pickup_code(self, order_id: str, code: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}/validatePickupCode"
        
        try:
            headers = self._get_headers()
            data = {
                "code": code
            }
            
            print(f"Validando codigo de coleta {code} para pedido {order_id}...")
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            
            if resp.status_code == 200:
                print("Codigo de coleta validado com sucesso!")
                return True
            else:
                print(f"Erro ao validar codigo: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao validar codigo: {e}")
            return False

    def get_tracking(self, order_id: str) -> Optional[Dict]:
        url = f"{self.base_url}/orders/{order_id}/tracking"
        
        try:
            headers = self._get_headers()
            print(f"Buscando rastreamento do pedido {order_id}...")
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                tracking_data = resp.json()
                print("Informacoes de rastreamento obtidas com sucesso!")
                return tracking_data
            else:
                print(f"Erro ao buscar rastreamento: {resp.status_code} - {resp.text}")
                return None
                
        except Exception as e:
            print(f"Erro ao buscar rastreamento: {e}")
            return None

    def get_negotiation(self, order_id: str) -> Optional[Negotiation]:
        url = f"{self.base_url}/orders/{order_id}/negotiation"
        
        try:
            headers = self._get_headers()
            print(f"Buscando negociacoes do pedido {order_id}...")
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                negotiation_data = resp.json()
                negotiation = Negotiation(
                    id=negotiation_data.get("id", ""),
                    type=negotiation_data.get("type", ""),
                    status=negotiation_data.get("status", ""),
                    created_at=negotiation_data.get("createdAt", ""),
                    updated_at=negotiation_data.get("updatedAt", ""),
                    proposal=negotiation_data.get("proposal", {})
                )
                print("Negociacoes obtidas com sucesso!")
                return negotiation
            else:
                print(f"Erro ao buscar negociacoes: {resp.status_code} - {resp.text}")
                return None
                
        except Exception as e:
            print(f"Erro ao buscar negociacoes: {e}")
            return None

    def accept_negotiation(self, order_id: str, negotiation_id: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}/negotiation/{negotiation_id}/accept"
        
        try:
            headers = self._get_headers()
            print(f"Aceitando negociacao {negotiation_id} do pedido {order_id}...")
            resp = requests.post(url, headers=headers, timeout=10)
            
            if resp.status_code in [200, 202, 204]:
                print("Negociacao aceita com sucesso!")
                return True
            else:
                print(f"Erro ao aceitar negociacao: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao aceitar negociacao: {e}")
            return False

    def reject_negotiation(self, order_id: str, negotiation_id: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}/negotiation/{negotiation_id}/reject"
        
        try:
            headers = self._get_headers()
            print(f"Rejeitando negociacao {negotiation_id} do pedido {order_id}...")
            resp = requests.post(url, headers=headers, timeout=10)
            
            if resp.status_code in [200, 202, 204]:
                print("Negociacao rejeitada com sucesso!")
                return True
            else:
                print(f"Erro ao rejeitar negociacao: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao rejeitar negociacao: {e}")
            return False

    def confirm_order(self, order_id: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}/confirm"
        
        try:
            headers = self._get_headers()
            print(f"Confirmando pedido {order_id}...")
            resp = requests.post(url, headers=headers, timeout=10)
            
            if resp.status_code in [200, 202, 204]:
                print("Pedido confirmado com sucesso!")
                return True
            else:
                print(f"Erro ao confirmar pedido: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"Erro ao confirmar pedido: {e}")
            return False

    def process_new_orders(self) -> List[Order]:
        print("PROCESSANDO NOVOS PEDIDOS...")
        events = self.poll_events()
        
        new_orders = []
        
        for event in events:
            event_description = {
                EventCode.PLC: "NOVO PEDIDO RECEBIDO",
                EventCode.CFM: "PEDIDO CONFIRMADO", 
                EventCode.RTP: "PRONTO PARA RETIRADA",
                EventCode.DIS: "PEDIDO DESPACHADO",
                EventCode.CON: "PEDIDO CONCLUIDO",
                EventCode.CAN: "PEDIDO CANCELADO",
                EventCode.CAR: "SOLICITACAO DE CANCELAMENTO",
                EventCode.INT: "PEDIDO INTEGRADO",
                EventCode.PST: "PREPARO INICIADO",
                EventCode.OPA: "PEDIDO MODIFICADO",
                EventCode.ADR: "ENTREGADOR DESIGNADO",
                EventCode.NEG: "NEGOCIACAO DISPONIVEL",
                EventCode.DGR: "GRUPO DE ENTREGA",
                EventCode.RQC: "CODIGO DE DEVOLUCAO SOLICITADO"
            }.get(event.code, f"EVENTO: {event.code}")
            
            print(f"  {event_description} - Pedido: {event.order_id}")
            
            if event.order_id in self._processed_orders and event.code != EventCode.OPA:
                print(f"  Pedido {event.order_id} ja processado, ignorando...")
                continue
                
            if event.code == EventCode.PLC:
                print(f"  PROCESSANDO NOVO PEDIDO!")
                
                order = self.get_order_details(event.order_id)
                if order:
                    new_orders.append(order)
                    self._processed_orders.add(order.id)
                    print(f"  Pedido {order.short_reference} processado com sucesso!")
                    
                    print(f"  Pedido aguardando confirmacao manual...")
            
            elif event.code == EventCode.NEG:
                print(f"  NEGOCIACAO DISPONIVEL - Verificar plataforma de negociacao")
                negotiation = self.get_negotiation(event.order_id)
                if negotiation:
                    print(f"  Tipo: {negotiation.type}, Status: {negotiation.status}")
            
            elif event.code == EventCode.RQC:
                print(f"  CODIGO DE DEVOLUCAO SOLICITADO - Pedido: {event.order_id}")
                order = self.get_order_details(event.order_id)
                if order and order.pickup_code:
                    print(f"  Codigo de devolucao: {order.pickup_code}")
            
            else:
                if event.order_id in self._processed_orders:
                    print(f"  Atualizando status do pedido {event.order_id} para {event.code}")
        
        return new_orders