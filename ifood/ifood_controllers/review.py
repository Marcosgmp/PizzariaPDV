from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from pydantic import BaseModel
from ifood_services.review import ReviewService
from config import IFOOD_MERCHANT_ID

router = APIRouter(prefix="/reviews", tags=["reviews"])

def get_review_service():
    return ReviewService()

class ReplyRequest(BaseModel):
    text: str


@router.get("/merchants/{merchant_id}/reviews")
def list_reviews(
    merchant_id: str,
    page: int = Query(1, ge=1, description="Página (começa em 1)"),
    page_size: int = Query(10, ge=1, le=50, description="Tamanho da página (máx 50)"),
    add_count: bool = Query(False, description="Incluir contagem total"),
    date_from: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DDTHH:MM:SSZ)"),
    date_to: Optional[str] = Query(None, description="Data final (YYYY-MM-DDTHH:MM:SSZ)"),
    sort: str = Query("DESC", description="Ordenação: ASC ou DESC"),
    sort_by: str = Query("CREATED_AT", description="Campo para ordenar: ORDER_DATE ou CREATED_AT"),
    service: ReviewService = Depends(get_review_service)
):
    try:
        return service.list_reviews(
            merchant_id=merchant_id,
            page=page,
            page_size=page_size,
            add_count=add_count,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
            sort_by=sort_by
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/merchants/{merchant_id}/reviews/{review_id}")
def get_review(
    merchant_id: str, 
    review_id: str, 
    service: ReviewService = Depends(get_review_service)
):
    try:
        return service.get_review(merchant_id, review_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.post("/merchants/{merchant_id}/reviews/{review_id}/answers")
def post_reply(
    merchant_id: str, 
    review_id: str, 
    request: ReplyRequest,
    service: ReviewService = Depends(get_review_service)
):
    """
    Responde uma review - VALIDA LIMITES DE TEXTO E STATUS PARA HOMOLOGAÇÃO
    """
    try:
        return service.post_reply(merchant_id, review_id, request.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/merchants/{merchant_id}/summary")
def get_summary(
    merchant_id: str, 
    service: ReviewService = Depends(get_review_service)
):
    """
    Obtém resumo das reviews
    """
    try:
        return service.get_summary(merchant_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/test/v2-structure")
def test_v2_structure(service: ReviewService = Depends(get_review_service)):
    try:
        result = service.list_reviews(
            merchant_id= IFOOD_MERCHANT_ID,
            page=1,
            page_size=5,
            add_count=True
        )
        
        v2_checks = {
            "has_reviews_array": "reviews" in result,
            "has_v2_fields": all(
                all(field in review for field in ["status", "replies", "version", "visibility"])
                for review in result.get("reviews", [])
            ) if result.get("reviews") else True,
            "has_pagination": all(field in result for field in ["page", "size"]),
            "has_count_when_requested": "total" in result and "pageCount" in result
        }
        
        return {
            "message": "Teste de estrutura V2",
            "v2_structure_valid": all(v2_checks.values()),
            "checks": v2_checks,
            "sample_data": {
                "total_reviews": len(result.get("reviews", [])),
                "has_v2_fields": v2_checks["has_v2_fields"]
            } if result.get("reviews") else {"message": "Nenhuma review encontrada"}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no teste V2: {str(e)}")