from fastapi import APIRouter, HTTPException, Body, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ifood_services.shipping import IfoodShippingService, DeliveryQuote, CancellationReason, SafeDeliveryScore, TrackingInfo

class DeliveryAvailabilityRequest(BaseModel):
    latitude: float = Field(..., description="Latitude do endereço de entrega")
    longitude: float = Field(..., description="Longitude do endereço de entrega")

class CreateExternalOrderRequest(BaseModel):
    order_data: Dict[str, Any] = Field(..., description="Dados completos do pedido Sob Demanda")

class RequestDriverRequest(BaseModel):
    quote_id: str = Field(..., description="ID da cotação obtida previamente")

class CancelOrderRequest(BaseModel):
    cancellation_code: str = Field(..., description="Código de cancelamento")
    reason: str = Field(..., description="Motivo do cancelamento")

class AddressChangeRequest(BaseModel):
    street_name: str = Field(..., description="Nome da rua")
    street_number: str = Field(..., description="Número")
    complement: Optional[str] = Field(None, description="Complemento")
    neighborhood: str = Field(..., description="Bairro")
    city: str = Field(..., description="Cidade")
    state: str = Field(..., description="Estado (UF)")
    country: str = Field(..., description="País")
    reference: Optional[str] = Field(None, description="Referência")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")

class ShippingResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class DeliveryQuoteResponse(BaseModel):
    success: bool
    data: Optional[DeliveryQuote] = None
    error: Optional[str] = None

class CancellationReasonsResponse(BaseModel):
    success: bool
    data: List[CancellationReason] = []
    error: Optional[str] = None

class SafeDeliveryResponse(BaseModel):
    success: bool
    data: Optional[SafeDeliveryScore] = None
    error: Optional[str] = None

class TrackingResponse(BaseModel):
    success: bool
    data: Optional[TrackingInfo] = None
    error: Optional[str] = None

router = APIRouter(prefix="/shipping", tags=["shipping"])
shipping_service = IfoodShippingService()

@router.get("/status")
async def get_shipping_status():
    return shipping_service.get_service_status()

@router.get("/merchants/{merchant_id}/delivery-availability", response_model=DeliveryQuoteResponse)
async def check_delivery_availability_get(
    merchant_id: str,
    latitude: float = Query(..., description="Latitude do endereço de entrega"),
    longitude: float = Query(..., description="Longitude do endereço de entrega")
):
    try:
        service = IfoodShippingService(merchant_id)
        quote = service.check_delivery_availability(latitude, longitude)
        return DeliveryQuoteResponse(success=True, data=quote)
    except HTTPException as e:
        return DeliveryQuoteResponse(success=False, error=e.detail)
    except Exception as e:
        return DeliveryQuoteResponse(success=False, error=str(e))

@router.get("/orders/{order_id}/delivery-availability", response_model=DeliveryQuoteResponse)
async def check_order_delivery_availability(order_id: str):
    try:
        quote = shipping_service.check_order_delivery_availability(order_id)
        return DeliveryQuoteResponse(success=True, data=quote)  
    except HTTPException as e:
        return DeliveryQuoteResponse(success=False, error=e.detail)
    except Exception as e:
        return DeliveryQuoteResponse(success=False, error=str(e))

@router.post("/external-orders", response_model=ShippingResponse)
async def create_external_order(order_data: Dict[str, Any] = Body(...)):
    try:
        result = shipping_service.create_external_order(order_data)
        return ShippingResponse(
            success=True,
            message="Pedido Sob Demanda criado com sucesso",
            data=result
        )
    except HTTPException as e:
        return ShippingResponse(success=False, message=e.detail)
    except Exception as e:
        return ShippingResponse(success=False, message=str(e))  
    
@router.post("/orders/{order_id}/request-driver", response_model=ShippingResponse)
async def request_driver_for_order(order_id: str, request: RequestDriverRequest):
    try:
        success = shipping_service.request_driver_for_order(order_id, request.quote_id)
        return ShippingResponse(
            success=success,
            message="Solicitação de entregador registrada com sucesso"
        )
    except HTTPException as e:
        return ShippingResponse(success=False, message=e.detail)
    except Exception as e:
        return ShippingResponse(success=False, message=str(e))

@router.post("/orders/{order_id}/cancel-request-driver", response_model=ShippingResponse)
async def cancel_request_driver(order_id: str):
    try:
        success = shipping_service.cancel_request_driver(order_id)
        return ShippingResponse(
            success=success,
            message="Cancelamento de entregador solicitado com sucesso"
        )
    except HTTPException as e:
        return ShippingResponse(success=False, message=e.detail)
    except Exception as e:
        return ShippingResponse(success=False, message=str(e))

@router.get("/orders/{order_id}/cancellation-reasons", response_model=CancellationReasonsResponse)
async def get_cancellation_reasons(order_id: str):
    try:
        reasons = shipping_service.get_cancellation_reasons(order_id)
        return CancellationReasonsResponse(success=True, data=reasons)
    except HTTPException as e:
        return CancellationReasonsResponse(success=False, error=e.detail)
    except Exception as e:
        return CancellationReasonsResponse(success=False, error=str(e))

@router.post("/orders/{order_id}/cancel", response_model=ShippingResponse)
async def cancel_order(order_id: str, request: CancelOrderRequest):
    try:
        success = shipping_service.cancel_order(
            order_id=order_id,
            cancellation_code=request.cancellation_code,
            reason=request.reason
        )
        return ShippingResponse(
            success=success,
            message="Pedido cancelado com sucesso"
        )
    except HTTPException as e:
        return ShippingResponse(success=False, message=e.detail)
    except Exception as e:
        return ShippingResponse(success=False, message=str(e))

@router.post("/orders/{order_id}/confirm-address", response_model=ShippingResponse)
async def confirm_order_address(order_id: str):
    try:
        success = shipping_service.confirm_order_address(order_id)
        return ShippingResponse(
            success=success,
            message="Endereço confirmado com sucesso"
        )
    except HTTPException as e:
        return ShippingResponse(success=False, message=e.detail)
    except Exception as e:
        return ShippingResponse(success=False, message=str(e))

@router.post("/orders/{order_id}/request-address-change", response_model=ShippingResponse)
async def request_address_change(order_id: str, request: AddressChangeRequest):
    try:
        address_data = {
            "streetName": request.street_name,
            "streetNumber": request.street_number,
            "complement": request.complement,
            "neighborhood": request.neighborhood,
            "city": request.city,
            "state": request.state,
            "country": request.country,
            "reference": request.reference,
            "coordinates": {
                "latitude": request.latitude,
                "longitude": request.longitude
            }
        }
        success = shipping_service.request_address_change(order_id, address_data)
        return ShippingResponse(
            success=success,
            message="Alteração de endereço solicitada com sucesso"
        )
    except HTTPException as e:
        return ShippingResponse(success=False, message=e.detail)
    except Exception as e:
        return ShippingResponse(success=False, message=str(e))

@router.post("/orders/{order_id}/accept-address-change", response_model=ShippingResponse)
async def accept_address_change(order_id: str):
    try:
        success = shipping_service.accept_address_change(order_id)
        return ShippingResponse(
            success=success,
            message="Alteração de endereço aceita com sucesso"
        )
    except HTTPException as e:
        return ShippingResponse(success=False, message=e.detail)
    except Exception as e:
        return ShippingResponse(success=False, message=str(e))

@router.post("/orders/{order_id}/deny-address-change", response_model=ShippingResponse)
async def deny_address_change(order_id: str):
    try:
        success = shipping_service.deny_address_change(order_id)
        return ShippingResponse(
            success=success,
            message="Alteração de endereço rejeitada com sucesso"
        )
    except HTTPException as e:
        return ShippingResponse(success=False, message=e.detail)
    except Exception as e:
        return ShippingResponse(success=False, message=str(e))

@router.get("/orders/{order_id}/safe-delivery", response_model=SafeDeliveryResponse)
async def get_safe_delivery_score(order_id: str):
    try:
        score = shipping_service.get_safe_delivery_score(order_id)
        return SafeDeliveryResponse(success=True, data=score)
    except HTTPException as e:
        return SafeDeliveryResponse(success=False, error=e.detail)
    except Exception as e:
        return SafeDeliveryResponse(success=False, error=str(e))

@router.get("/orders/{order_id}/tracking", response_model=TrackingResponse)
async def track_order(order_id: str):
    try:
        tracking_info = shipping_service.track_order(order_id)
        return TrackingResponse(success=True, data=tracking_info)
    except HTTPException as e:
        return TrackingResponse(success=False, error=e.detail)
    except Exception as e:
        return TrackingResponse(success=False, error=str(e))

@router.post("/events/process")
async def process_shipping_event(event_data: Dict[str, Any] = Body(...)):
    try:
        shipping_service.process_shipping_event(event_data)
        return {"success": True, "message": "Evento processado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar evento: {str(e)}")