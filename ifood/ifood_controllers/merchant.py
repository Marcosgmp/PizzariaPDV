from fastapi import APIRouter, HTTPException, status, Body
from typing import List
from ..ifood_services.merchant import IfoodMerchantService, MerchantBasicInfo, MerchantDetails, MerchantStatus, Interruption, OpeningHours

router = APIRouter(prefix="/merchant", tags=["merchant"])

merchant_service = IfoodMerchantService(is_test_environment=True)

@router.get(
    "/merchants", 
    response_model=List[MerchantBasicInfo],
    summary="Listar todos os merchants",
    description="Retorna a lista de todos os merchants disponíveis para o cliente autenticado"
)
def list_merchants():
    """
    List all merchants - GET /merchants
    """
    merchants = merchant_service.list_merchants()
    if not merchants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Nenhum merchant encontrado"
        )
    return merchants

@router.get(
    "/merchants/{merchant_id}", 
    response_model=MerchantDetails,
    summary="Obter detalhes do merchant",
    description="Retorna os detalhes completos de um merchant específico"
)
def get_merchant_details(merchant_id: str):
    """
    Get merchant details - GET /merchants/{merchantId}
    """
    merchant = merchant_service.get_merchant_details(merchant_id)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Merchant {merchant_id} não encontrado"
        )
    return merchant

@router.get(
    "/merchants/{merchant_id}/status", 
    response_model=MerchantStatus,
    summary="Obter status do merchant",
    description="Retorna o status atual do merchant incluindo validações e mensagens"
)
def get_merchant_status(merchant_id: str):
    """
    Get merchant status - GET /merchants/{merchantId}/status
    """
    status_obj = merchant_service.get_merchant_status(merchant_id)
    if not status_obj:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Erro ao obter status do merchant"
        )
    return status_obj

@router.get(
    "/merchants/{merchant_id}/interruptions", 
    response_model=List[Interruption],
    summary="Listar interrupções",
    description="Retorna a lista de interrupções ativas do merchant"
)
def get_merchant_interruptions(merchant_id: str):
    """
    List interruptions - GET /merchants/{merchantId}/interruptions
    """
    interruptions = merchant_service.get_merchant_interruptions(merchant_id)
    if interruptions is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Erro ao obter interrupções do merchant"
        )
    return interruptions

@router.post(
    "/merchants/{merchant_id}/interruptions",
    response_model=Interruption,
    summary="Criar interrupção",
    description="Cria uma nova interrupção para o merchant"
)
def create_interruption(
    merchant_id: str,
    description: str = Body(..., embed=True), 
    start: str = Body(..., embed=True),    
    end: str = Body(..., embed=True) 
):
    result = merchant_service.create_interruption(  
        merchant_id=merchant_id,
        description=description,
        start_time=start,
        end_time=end
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Erro ao criar interrupção. Verifique os dados e tente novamente."
        )
    return result

@router.delete(
    "/merchants/{merchant_id}/interruptions/{interruption_id}",
    summary="Remover interrupção",
    description="Remove uma interrupção específica do merchant"
)
def delete_interruption(merchant_id: str, interruption_id: str):
    """
    Delete interruption - DELETE /merchants/{merchantId}/interruptions/{interruptionId}
    """
    success = merchant_service.delete_interruption(merchant_id, interruption_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Erro ao deletar interrupção"
        )
    return {"success": True, "message": "Interrupção deletada com sucesso"}

@router.get(
    "/merchants/{merchant_id}/opening-hours",
    response_model=OpeningHours,
    summary="Obter horário de funcionamento",
    description="Retorna o horário de funcionamento configurado do merchant"
)
def get_opening_hours(merchant_id: str):
    """
    Get opening hours - GET /merchants/{merchantId}/opening-hours
    """
    hours = merchant_service.get_opening_hours(merchant_id)
    if not hours:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Horário de funcionamento não encontrado"
        )
    return hours

@router.put(
    "/merchants/{merchant_id}/opening-hours",
    summary="Atualizar horário de funcionamento",
    description="Atualiza o horário de funcionamento do merchant"
)
def update_opening_hours(merchant_id: str, opening_hours: OpeningHours):
    """
    Update opening hours - PUT /merchants/{merchantId}/opening-hours
    """
    success = merchant_service.update_opening_hours(merchant_id, opening_hours)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Erro ao atualizar horário de funcionamento"
        )
    return {"success": True, "message": "Horário de funcionamento atualizado com sucesso"}