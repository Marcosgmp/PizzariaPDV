from fastapi import APIRouter, HTTPException
from ifood.ifood_services.auth import IfoodAuthService

router = APIRouter(prefix="/auth", tags=["auth"])

auth_service = IfoodAuthService()

@router.get("/token")
def get_ifood_token():
    try:
        token = auth_service.get_token()
        return {"access_token": token,
                "token_type": "Bearer",
                "expires_in": auth_service.expiration}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter token: {e}")