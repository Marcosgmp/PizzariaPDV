from fastapi import APIRouter, HTTPException
from typing import List
from ifood.ifood_services.merchant import IfoodMerchantService, MerchantBasicInfo, MerchantDetails, MerchantStatus

router = APIRouter(prefix="/merchant", tags=["merchant"])

merchant_service = IfoodMerchantService(is_test_environment=True)

@router.get("/list", response_model=List[MerchantBasicInfo])
def list_merchants():
    merchants = merchant_service.list_merchants()
    if not merchants:
        raise HTTPException(status_code=404, detail="Nenhum merchant encontrado")
    return merchants

@router.get("/{merchant_id}", response_model=MerchantDetails)
def get_merchant_details(merchant_id: str):
    merchant = merchant_service.get_merchant_details(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail=f"Merchant {merchant_id} nao encontrado")
    return merchant

@router.get("/{merchant_id}/status", response_model=MerchantStatus)
def get_merchant_status(merchant_id: str):
    status = merchant_service.get_merchant_status(merchant_id)
    if not status:
        raise HTTPException(status_code=500, detail="Erro ao obter status do merchant")
    return status
