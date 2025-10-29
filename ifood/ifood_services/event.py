import requests
from typing import List, Optional, Dict, Any
from ifood_services.auth import IfoodAuthService

class IfoodEventService:
    def __init__(self):
        self.auth_service = IfoodAuthService()
        self.base_url = "https://merchant-api.ifood.com.br/order/v1.0/events"

    def get_events(self, 
                   merchant_ids: Optional[List[str]] = None, 
                   types: Optional[str] = None, 
                   groups: Optional[str] = None, 
                   categories: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Busca novos eventos via polling - CRÍTICO PARA HOMOLOGAÇÃO
        """
        try:
            token = self.auth_service.get_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            # Header OBRIGATÓRIO para homologação
            if merchant_ids:
                headers["x-polling-merchants"] = ",".join(merchant_ids)

            # Parâmetros OBRIGATÓRIOS para homologação
            params = {
                "categories": categories or "ALL",
                "excludeHeartbeat": "true" 
            }
            
            if types:
                params["types"] = types
            if groups:
                params["groups"] = groups

            url = f"{self.base_url}:polling"
            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                events = response.json()
                print(f"{len(events)} evento(s) recebido(s)")
                return events
            elif response.status_code == 204:
                print("Nenhum evento novo")
                return []
            elif response.status_code == 403:
                error_data = response.json()
                unauthorized_merchants = error_data.get('error', {}).get('unauthorizedMerchants', [])
                print(f"Merchants não autorizados: {unauthorized_merchants}")
                return []
            else:
                print(f"Erro ao buscar eventos: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"Exception ao buscar eventos: {e}")
            return None

    def acknowledge_events(self, event_ids: List[str]) -> Optional[Dict[str, Any]]:
        """
        Confirma o recebimento dos eventos (ACK) - CRÍTICO PARA HOMOLOGAÇÃO
        """
        try:
            if not event_ids:
                return {"status": "no_events", "count": 0}

            token = self.auth_service.get_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            # Limite da API: máximo 2000 eventos por ACK
            if len(event_ids) > 2000:
                print(f"Lista de eventos excede limite. Total: {len(event_ids)}")
                event_ids = event_ids[:2000]

            body = [{"id": event_id} for event_id in event_ids]

            url = f"{self.base_url}/acknowledgment"
            response = requests.post(url, headers=headers, json=body, timeout=30)

            if response.status_code == 202:
                result = {"status": "acknowledged", "count": len(event_ids)}
                print(f"{len(event_ids)} evento(s) confirmado(s)")
                return result
            else:
                print(f"Erro ao enviar ACK: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"Exception no ACK: {e}")
            return None