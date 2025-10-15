import requests
import os
import sys
from datetime import datetime, timedelta
from config import IFOOD_CLIENT_ID, IFOOD_CLIENT_SECRET

class IfoodAuthService:
    def __init__(self):
        self.client_id = IFOOD_CLIENT_ID
        self.client_secret = IFOOD_CLIENT_SECRET
        self.grant_type = "client_credentials"
        self.base_url = "https://merchant-api.ifood.com.br/authentication/v1.0/oauth/token"
        self.token = None
        self.expiration = None

    def get_token(self):
        """Gera um novo token se necessario"""
        if self.token and self.expiration and datetime.now() < self.expiration:
            return self.token

        data = {
            "grantType": self.grant_type,
            "clientId": self.client_id,
            "clientSecret": self.client_secret
        }

        print("Solicitando novo token ao iFood...")
        resp = requests.post(self.base_url, data=data)
        resp.raise_for_status()

        result = resp.json()
        self.token = result.get("accessToken")
        expires_in = result.get("expiresIn", 3600)
        self.expiration = datetime.now() + timedelta(seconds=expires_in - 60)

        print(f"Novo token obtido! Expira em {expires_in//60} minutos.")
        return self.token