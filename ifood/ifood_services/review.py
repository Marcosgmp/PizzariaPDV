import requests
from typing import Optional
from fastapi import HTTPException
from config import IFOOD_API_URL, IFOOD_MERCHANT_ID
from ifood_services.auth import IfoodAuthService

class ReviewService:
    def __init__(self):
        self.base_url = f"{IFOOD_API_URL}/review/v2.0"
        self.auth_service = IfoodAuthService()
        self.headers = {"Content-Type": "application/json"}

    def _get_headers(self):
        token = self.auth_service.get_token()
        return {**self.headers, "Authorization": f"Bearer {token}"}

    def list_reviews(
        self,
        merchant_id: str = IFOOD_MERCHANT_ID,
        page: int = 1,
        page_size: int = 10,
        add_count: bool = False,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort: str = "DESC",
        sort_by: str = "CREATED_AT"
    ):
        params = {
            "page": page,
            "pageSize": page_size,
            "addCount": str(add_count).lower(),
            "sort": sort,
            "sortBy": sort_by
        }

        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to

        url = f"{self.base_url}/merchants/{merchant_id}/reviews"
        headers = self._get_headers()
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())

        return response.json()

    def get_review(self, merchant_id: str, review_id: str):
        url = f"{self.base_url}/merchants/{merchant_id}/reviews/{review_id}"
        headers = self._get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        return response.json()

    def post_reply(self, merchant_id: str, review_id: str, text: str):
        url = f"{self.base_url}/merchants/{merchant_id}/reviews/{review_id}/answers"
        headers = self._get_headers()
        body = {"text": text}
        response = requests.post(url, headers=headers, json=body)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        return response.json()

    def get_summary(self, merchant_id: str):
        url = f"{self.base_url}/merchants/{merchant_id}/summary"
        headers = self._get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        return response.json()
