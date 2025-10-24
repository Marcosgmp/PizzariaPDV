from fastapi import APIRouter, Depends, Query
from typing import Optional
from ifood_services.review import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])

def get_service():
    return ReviewService()

@router.get("/merchants/{merchant_id}")
def list_reviews(
    merchant_id: str,
    page: int = Query(1),
    page_size: int = Query(10),
    add_count: bool = Query(False),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort: str = Query("DESC"),
    sort_by: str = Query("CREATED_AT"),
    service: ReviewService = Depends(get_service)
):
    return service.list_reviews(merchant_id, page, page_size, add_count, date_from, date_to, sort, sort_by)

@router.get("/merchants/{merchant_id}/reviews/{review_id}")
def get_review(merchant_id: str, review_id: str, service: ReviewService = Depends(get_service)):
    return service.get_review(merchant_id, review_id)

@router.post("/merchants/{merchant_id}/reviews/{review_id}/answers")
def post_reply(merchant_id: str, review_id: str, body: dict, service: ReviewService = Depends(get_service)):
    text = body.get("text")
    if not text:
        return {"error": "O campo 'text' é obrigatório."}
    return service.post_reply(merchant_id, review_id, text)

@router.get("/merchants/{merchant_id}/summary")
def get_summary(merchant_id: str, service: ReviewService = Depends(get_service)):
    return service.get_summary(merchant_id)
