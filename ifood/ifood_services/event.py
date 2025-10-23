import requests
from ifood_services.auth import IfoodAuthService

class IfoodEventService:
    def __init__(self):
        self.auth_service = IfoodAuthService()
        self.base_url = "https://merchant-api.ifood.com.br/order/v1.0/events"

    def get_events(self, merchant_ids: list[str] = None, types: str = None, groups: str = None, categories: str = None):
        """
        Busca novos eventos (pedidos, status, etc.) via polling.
        """
        token = self.auth_service.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        if merchant_ids:
            headers["x-polling-merchants"] = ",".join(merchant_ids)

        params = {}
        if types:
            params["types"] = types
        if groups:
            params["groups"] = groups
        if categories:
            params["categories"] = categories

        url = f"{self.base_url}:polling"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            return []  # sem eventos
        else:
            print(f"Erro ao buscar eventos: {response.status_code} - {response.text}")
            return None

    def acknowledge_events(self, event_ids: list[str]):
        """
        Confirma o recebimento dos eventos (ACK).
        """
        token = self.auth_service.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        body = [{"id": event_id} for event_id in event_ids]

        url = f"{self.base_url}/acknowledgment"
        response = requests.post(url, headers=headers, json=body)

        if response.status_code == 202:
            return {"status": "acknowledged", "count": len(event_ids)}
        else:
            print(f"Erro ao enviar ACK: {response.status_code} - {response.text}")
            return None
