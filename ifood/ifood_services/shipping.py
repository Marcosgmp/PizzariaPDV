import requests
import time
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
from fastapi import HTTPException
from functools import wraps

from config import IFOOD_API_URL, IFOOD_MERCHANT_ID
from ifood_services.auth import IfoodAuthService

class ShippingEventType(str, Enum):
    REQUEST_DRIVER = "REQUEST_DRIVER"
    REQUEST_DRIVER_SUCCESS = "REQUEST_DRIVER_SUCCESS" 
    REQUEST_DRIVER_FAILED = "REQUEST_DRIVER_FAILED"
    DELIVERY_CANCELLATION_REQUESTED = "DELIVERY_CANCELLATION_REQUESTED"
    DELIVERY_CANCELLATION_REQUEST_ACCEPTED = "DELIVERY_CANCELLATION_REQUEST_ACCEPTED"
    DELIVERY_CANCELLATION_REQUEST_REJECTED = "DELIVERY_CANCELLATION_REQUEST_REJECTED"
    DELIVERY_DROP_CODE_REQUESTED = "DELIVERY_DROP_CODE_REQUESTED"
    ASSIGN_DRIVER = "ASSIGN_DRIVER"
    DELIVERY_ADDRESS_CHANGE_USER_CONFIRMED = "DELIVERY_ADDRESS_CHANGE_USER_CONFIRMED"
    DELIVERY_ADDRESS_CHANGE_REQUESTED = "DELIVERY_ADDRESS_CHANGE_REQUESTED"
    DELIVERY_ADDRESS_CHANGE_ACCEPTED = "DELIVERY_ADDRESS_CHANGE_ACCEPTED"
    DELIVERY_ADDRESS_CHANGE_DENIED = "DELIVERY_ADDRESS_CHANGE_DENIED"

class SafeDeliveryScore(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE" 
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"

@dataclass
class DeliveryQuote:
    id: str
    expiration_at: str
    created_at: str
    distance: int
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
class CancellationReason:
    cancel_code_id: str
    description: str

@dataclass
class SafeDeliveryScore:
    score: SafeDeliveryScore
    rules: Dict[str, bool]

@dataclass
class TrackingInfo:
    latitude: Optional[float]
    longitude: Optional[float]
    expected_delivery: Optional[str]
    pickup_eta_start: int
    delivery_eta_end: int
    track_date: Optional[str]

def retry_with_exponential_backoff(max_retries: int = 3, base_delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        raise e
                    delay = base_delay * (2 ** retries)
                    logging.warning(f"Tentativa {retries} falhou. Retry em {delay}s: {e}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

def log_operation(operation_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(__name__)
            try:
                result = func(*args, **kwargs)
                logger.info(f"SHIPPING_OP_SUCCESS - {operation_name}")
                return result
            except Exception as e:
                logger.error(f"SHIPPING_OP_FAILED - {operation_name}: {str(e)}")
                raise
        return wrapper
    return decorator

class IfoodShippingService:
    def __init__(self, merchant_id: str = None):
        self.base_url = f"{IFOOD_API_URL}/shipping/v1.0"
        self.merchant_id = merchant_id or IFOOD_MERCHANT_ID
        self.auth_service = IfoodAuthService()
        self.headers = {"Content-Type": "application/json"}
        
        self.callbacks = {
            'delivery_assigned': [],
            'delivery_cancelled': [],
            'drop_code_requested': [],
            'address_change_requested': []
        }
        
        self.logger = logging.getLogger(__name__)

    def _get_headers(self):
        token = self.auth_service.get_token()
        return {**self.headers, "Authorization": f"Bearer {token}"}

    def register_callback(self, event_type: str, callback: Callable):
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
        else:
            self.logger.warning(f"Tipo de evento desconhecido: {event_type}")

    def _notify_callbacks(self, event_type: str, data: Dict):
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"Erro em callback {event_type}: {e}")

    @retry_with_exponential_backoff()
    @log_operation("check_delivery_availability")
    def check_delivery_availability(self, latitude: float, longitude: float) -> Optional[DeliveryQuote]:
        url = f"{self.base_url}/merchants/{self.merchant_id}/deliveryAvailabilities"
        params = {"latitude": latitude, "longitude": longitude}

        try:
            headers = self._get_headers()
            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return self._parse_delivery_quote(data)
            elif response.status_code == 400:
                error_data = response.json()
                raise HTTPException(status_code=400, detail=error_data.get('message', 'Erro desconhecido'))
            else:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    @retry_with_exponential_backoff()
    @log_operation("check_order_delivery_availability")
    def check_order_delivery_availability(self, order_id: str) -> Optional[DeliveryQuote]:
        url = f"{self.base_url}/orders/{order_id}/deliveryAvailabilities"

        try:
            headers = self._get_headers()
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return self._parse_delivery_quote(data)
            elif response.status_code == 400:
                error_data = response.json()
                raise HTTPException(status_code=400, detail=error_data.get('message', 'Erro desconhecido'))
            else:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    def _parse_delivery_quote(self, data: Dict) -> DeliveryQuote:
        return DeliveryQuote(
            id=data.get("id", ""),
            expiration_at=data.get("expirationAt", ""),
            created_at=data.get("createdAt", ""),
            distance=data.get("distance", 0),
            preparation_time=data.get("preparationTime", 0),
            gross_value=data.get("quote", {}).get("grossValue", 0),
            discount=data.get("quote", {}).get("discount", 0),
            raise_value=data.get("quote", {}).get("raise", 0),
            net_value=data.get("quote", {}).get("netValue", 0),
            delivery_time_min=data.get("deliveryTime", {}).get("min", 0),
            delivery_time_max=data.get("deliveryTime", {}).get("max", 0),
            has_payment_methods=data.get("hasPaymentMethods", False),
            payment_methods=data.get("paymentMethods", [])
        )

    @retry_with_exponential_backoff()
    @log_operation("create_external_order")
    def create_external_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/merchants/{self.merchant_id}/orders"

        self._validate_order_data(order_data)

        try:
            headers = self._get_headers()
            response = requests.post(url, headers=headers, json=order_data, timeout=30)

            if response.status_code in [200, 201, 202]:
                result = response.json()
                return result
            elif response.status_code == 400:
                error_data = response.json()
                raise HTTPException(status_code=400, detail=error_data.get('message', 'Erro desconhecido'))
            else:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    def _validate_order_data(self, order_data: Dict):
        required_fields = {
            'orderType': 'DELIVERY',
            'orderTiming': 'IMMEDIATE', 
            'salesChannel': 'POS'
        }
    
        for field, expected_value in required_fields.items():
            if order_data.get(field) != expected_value:
                raise HTTPException(
                    status_code=422,
                    detail=f"Campo {field} deve ser '{expected_value}' para homologação"
                )
    
        phone_type = order_data.get('customer', {}).get('phone', {}).get('type')
        if phone_type != 'CUSTOMER':
            raise HTTPException(
                status_code=422,
                detail="customer.phone.type deve ser 'CUSTOMER' para elegibilidade de confirmação"
            )

    @retry_with_exponential_backoff()
    @log_operation("request_driver_for_order")
    def request_driver_for_order(self, order_id: str, quote_id: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}/requestDriver"
        data = {"quoteId": quote_id}

        try:
            headers = self._get_headers()
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 202:
                return True
            elif response.status_code == 400:
                error_data = response.json()
                raise HTTPException(status_code=400, detail=error_data.get('message', 'Erro desconhecido'))
            else:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    @retry_with_exponential_backoff()
    @log_operation("cancel_request_driver")
    def cancel_request_driver(self, order_id: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}/cancelRequestDriver"

        try:
            headers = self._get_headers()
            response = requests.post(url, headers=headers, timeout=30)

            if response.status_code == 202:
                self._notify_callbacks('delivery_cancelled', {
                    'order_id': order_id,
                    'timestamp': time.time(),
                    'type': 'REQUEST_DRIVER_CANCELLATION'
                })
                return True
            elif response.status_code == 400:
                error_data = response.json()
                raise HTTPException(status_code=400, detail=error_data.get('message', 'Erro desconhecido'))
            else:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    @retry_with_exponential_backoff()
    @log_operation("get_cancellation_reasons")
    def get_cancellation_reasons(self, order_id: str) -> List[CancellationReason]:
        url = f"{self.base_url}/orders/{order_id}/cancellationReasons"

        try:
            headers = self._get_headers()
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                reasons_data = response.json()
                return [
                    CancellationReason(
                        cancel_code_id=item.get("cancelCodeId", ""),
                        description=item.get("description", "")
                    )
                    for item in reasons_data
                ]
            elif response.status_code == 204:
                return []
            else:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    @retry_with_exponential_backoff()
    @log_operation("cancel_order")
    def cancel_order(self, order_id: str, cancellation_code: str, reason: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}/cancel"
        data = {"reason": reason, "cancellationCode": cancellation_code}

        try:
            headers = self._get_headers()
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 202:
                return True
            elif response.status_code == 400:
                error_data = response.json()
                raise HTTPException(status_code=400, detail=error_data.get('message', 'Erro desconhecido'))
            else:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    @retry_with_exponential_backoff()
    @log_operation("confirm_order_address")
    def confirm_order_address(self, order_id: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}/userConfirmAddress"

        try:
            headers = self._get_headers()
            response = requests.post(url, headers=headers, timeout=30)

            if response.status_code == 202:
                return True
            else:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    @retry_with_exponential_backoff()
    @log_operation("request_address_change")
    def request_address_change(self, order_id: str, address_data: Dict[str, Any]) -> bool:
        url = f"{self.base_url}/orders/{order_id}/deliveryAddressChangeRequest"

        try:
            headers = self._get_headers()
            response = requests.post(url, headers=headers, json=address_data, timeout=30)

            if response.status_code == 202:
                self._notify_callbacks('address_change_requested', {
                    'order_id': order_id,
                    'new_address': address_data,
                    'timestamp': time.time()
                })
                return True
            else:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    @retry_with_exponential_backoff()
    @log_operation("accept_address_change")
    def accept_address_change(self, order_id: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}/acceptDeliveryAddressChange"

        try:
            headers = self._get_headers()
            response = requests.post(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return True
            else:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    @retry_with_exponential_backoff()
    @log_operation("deny_address_change")
    def deny_address_change(self, order_id: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}/denyDeliveryAddressChange"

        try:
            headers = self._get_headers()
            response = requests.post(url, headers=headers, timeout=30)

            if response.status_code == 202:
                return True
            else:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    @retry_with_exponential_backoff()
    @log_operation("get_safe_delivery_score")
    def get_safe_delivery_score(self, order_id: str) -> SafeDeliveryScore:
        url = f"{self.base_url}/orders/{order_id}/safeDelivery"

        try:
            headers = self._get_headers()
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return SafeDeliveryScore(
                    score=SafeDeliveryScore(data.get("score", "LOW")),
                    rules=data.get("rules", {})
                )
            else:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    @retry_with_exponential_backoff()
    @log_operation("track_order")
    def track_order(self, order_id: str) -> TrackingInfo:
        url = f"{self.base_url}/orders/{order_id}/tracking"

        try:
            headers = self._get_headers()
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return TrackingInfo(
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                    expected_delivery=data.get("expectedDelivery"),
                    pickup_eta_start=data.get("pickupEtaStart", 0),
                    delivery_eta_end=data.get("deliveryEtaEnd", 0),
                    track_date=data.get("trackDate")
                )
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="Rastreamento não disponível")
            else:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    def process_shipping_event(self, event_data: Dict[str, Any]):
        event_type = event_data.get('type')
        order_id = event_data.get('orderId')

        if event_type == ShippingEventType.ASSIGN_DRIVER:
            self._handle_assign_driver(event_data)
        elif event_type == ShippingEventType.DELIVERY_DROP_CODE_REQUESTED:
            self._handle_drop_code_requested(event_data)
        elif event_type == ShippingEventType.DELIVERY_ADDRESS_CHANGE_REQUESTED:
            self._handle_address_change_requested(event_data)
        elif event_type == ShippingEventType.REQUEST_DRIVER_SUCCESS:
            self._handle_request_driver_success(event_data)
        elif event_type == ShippingEventType.REQUEST_DRIVER_FAILED:
            self._handle_request_driver_failed(event_data)

    def _handle_assign_driver(self, event_data: Dict):
        self._notify_callbacks('delivery_assigned', event_data)

    def _handle_drop_code_requested(self, event_data: Dict):
        code = event_data.get('metadata', {}).get('CODE')
        order_id = event_data.get('orderId')
        
        self._notify_callbacks('drop_code_requested', {
            'order_id': order_id,
            'code': code,
            'timestamp': time.time()
        })

    def _handle_address_change_requested(self, event_data: Dict):
        self._notify_callbacks('address_change_requested', event_data)

    def _handle_request_driver_success(self, event_data: Dict):
        pass

    def _handle_request_driver_failed(self, event_data: Dict):
        pass

    def get_service_status(self) -> Dict[str, Any]:
        return {
            "service": "IfoodShippingService",
            "merchant_id": self.merchant_id,
            "base_url": self.base_url,
            "callbacks_registered": {k: len(v) for k, v in self.callbacks.items()},
            "status": "ACTIVE"
        }

ifood_shipping_service = IfoodShippingService()