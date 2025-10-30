import requests
from typing import Optional, Dict, Any, List
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
    ) -> Dict[str, Any]:
        if page_size > 50:
            raise HTTPException(
                status_code=400, 
                detail="pageSize não pode ser maior que 50"
            )

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

        try:
            url = f"{self.base_url}/merchants/{merchant_id}/reviews"
            headers = self._get_headers()
            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                
                self._validate_v2_structure(data)
                return data
                
            elif response.status_code == 400:
                error_data = response.json()
                raise HTTPException(
                    status_code=400, 
                    detail=f"Parâmetro inválido: {error_data}"
                )
            else:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=error_data
                )

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    def _validate_v2_structure(self, data: Dict[str, Any]):
        """
        Valida estrutura V2 obrigatória para homologação
        """
        if "reviews" in data:
            for review in data["reviews"]:
                required_fields = ["status", "replies", "version", "visibility"]
                for field in required_fields:
                    if field not in review:
                        raise HTTPException(
                            status_code=500, 
                            detail=f"Campo V2 obrigatório faltando: {field}"
                        )
                
                valid_statuses = ["CREATED", "NOT_REPLIED", "REPLIED", "PUBLISHED", "INVALID", "DISCARDED", "UNKNOWN"]
                if review.get("status") not in valid_statuses:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Status inválido: {review.get('status')}"
                    )
                
                valid_visibility = ["PUBLIC", "PRIVATE"]
                if review.get("visibility") not in valid_visibility:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Visibility inválido: {review.get('visibility')}"
                    )
                
                if isinstance(review.get("replies"), list):
                    for reply in review["replies"]:
                        if "from" not in reply:
                            raise HTTPException(
                                status_code=500, 
                                detail="Campo 'from' faltando na estrutura replies"
                            )

    def get_review(self, merchant_id: str, review_id: str) -> Dict[str, Any]:
        """
        Obtém detalhes de uma review - CRÍTICO PARA HOMOLOGAÇÃO
        """
        try:
            url = f"{self.base_url}/merchants/{merchant_id}/reviews/{review_id}"
            headers = self._get_headers()
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data.get("replies"), list):
                    for reply in data["replies"]:
                        if "from" not in reply:
                            raise HTTPException(
                                status_code=500, 
                                detail="Campo 'from' faltando na estrutura replies"
                            )
                
                return data
                
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=404, 
                    detail="Review não encontrada"
                )
            else:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=error_data
                )

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    def post_reply(self, merchant_id: str, review_id: str, text: str) -> Dict[str, Any]:
        if len(text) < 10 or len(text) > 300:
            raise HTTPException(
                status_code=422,
                detail="Texto da resposta deve ter entre 10 e 300 caracteres"
            )

        try:
            url = f"{self.base_url}/merchants/{merchant_id}/reviews/{review_id}/answers"
            headers = self._get_headers()
            body = {"text": text}
            
            response = requests.post(url, headers=headers, json=body, timeout=30)

            if response.status_code == 200:
                return response.json()
                
            elif response.status_code == 422:
                error_data = response.json()
                raise HTTPException(
                    status_code=422,
                    detail="Review já descartada ou com moderação pendente"
                )
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Review não encontrada"
                )
            else:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=error_data
                )

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

    def get_summary(self, merchant_id: str) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/merchants/{merchant_id}/summary"
            headers = self._get_headers()
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=error_data
                )

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")