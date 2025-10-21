import requests
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import IFOOD_MERCHANT_ID
from ifood_services.auth import IfoodAuthService

class IfoodFinancialService:
    def __init__(self, merchant_id: str = None):
        self.base_url = "https://merchant-api.ifood.com.br/financial/v3.0"
        self.merchant_id = merchant_id or IFOOD_MERCHANT_ID
        self.auth_service = IfoodAuthService()
        self.headers = {"Content-Type": "application/json", "accept": "application/json"}

    def _get_headers(self):
        token = self.auth_service.get_token()
        return {**self.headers, "Authorization": f"Bearer {token}"}

    # 1️⃣ Conciliation
    def get_reconciliation(self, competence: str) -> dict:
        url = f"{self.base_url}/merchants/{self.merchant_id}/reconciliation"
        params = {"competence": competence}
        try:
            headers = self._get_headers()
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                print(f"Arquivo não encontrado para competência {competence}.")
                return {}
            else:
                print(f"Erro ao consultar conciliação: {resp.status_code} - {resp.text}")
                return {}
        except Exception as e:
            print(f"Erro ao consultar conciliação: {e}")
            return {}

    # 2️⃣ Settlements
    def get_settlements(self, begin_payment_date: str, end_payment_date: str,
                        begin_calculation_date: str = None, end_calculation_date: str = None) -> dict:
        url = f"{self.base_url}/merchants/{self.merchant_id}/settlements"
        params = {
            "beginPaymentDate": begin_payment_date,
            "endPaymentDate": end_payment_date
        }
        if begin_calculation_date and end_calculation_date:
            params["beginCalculationDate"] = begin_calculation_date
            params["endCalculationDate"] = end_calculation_date
        try:
            headers = self._get_headers()
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 400:
                print("Parâmetros inválidos para consulta de settlements.")
                print(resp.text)
                return {}
            else:
                print(f"Erro ao consultar settlements: {resp.status_code} - {resp.text}")
                return {}
        except Exception as e:
            print(f"Erro ao consultar settlements: {e}")
            return {}

    # 3️⃣ Anticipations
    def get_anticipations(self, begin_calculation_date: str, end_calculation_date: str,
                          begin_anticipated_payment_date: str = None, end_anticipated_payment_date: str = None) -> dict:
        url = f"{self.base_url}/merchants/{self.merchant_id}/anticipations"
        params = {
            "beginCalculationDate": begin_calculation_date,
            "endCalculationDate": end_calculation_date
        }
        if begin_anticipated_payment_date and end_anticipated_payment_date:
            params["beginAnticipatedPaymentDate"] = begin_anticipated_payment_date
            params["endAnticipatedPaymentDate"] = end_anticipated_payment_date
        try:
            headers = self._get_headers()
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 400:
                print("Parâmetros inválidos para consulta de antecipações.")
                print(resp.text)
                return {}
            else:
                print(f"Erro ao consultar antecipações: {resp.status_code} - {resp.text}")
                return {}
        except Exception as e:
            print(f"Erro ao consultar antecipações: {e}")
            return {}

    # 4️⃣ Sales
    def get_sales(self, begin_sales_date: str, end_sales_date: str, page: int = 1) -> dict:
        url = f"{self.base_url}/merchants/{self.merchant_id}/sales"
        params = {
            "beginSalesDate": begin_sales_date,
            "endSalesDate": end_sales_date,
            "page": page
        }
        try:
            headers = self._get_headers()
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 400:
                print("Parâmetros inválidos para consulta de vendas.")
                print(resp.text)
                return {}
            else:
                print(f"Erro ao consultar vendas: {resp.status_code} - {resp.text}")
                return {}
        except Exception as e:
            print(f"Erro ao consultar vendas: {e}")
            return {}

    # 5️⃣ Financial Events
    def get_financial_events(self, begin_date: str, end_date: str, page: int = 1, size: int = 100) -> dict:
        url = f"{self.base_url}/merchants/{self.merchant_id}/financial-events"
        params = {
            "beginDate": begin_date,
            "endDate": end_date,
            "page": page,
            "size": size
        }
        try:
            headers = self._get_headers()
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 400:
                print("Parâmetros inválidos para consulta de eventos financeiros.")
                print(resp.text)
                return {}
            else:
                print(f"Erro ao consultar eventos financeiros: {resp.status_code} - {resp.text}")
                return {}
        except Exception as e:
            print(f"Erro ao consultar eventos financeiros: {e}")
            return {}

    # 6️⃣ Reconciliation On Demand (POST)
    def request_reconciliation_on_demand(self, competence: str) -> dict:
        url = f"{self.base_url}/merchants/{self.merchant_id}/reconciliation/on-demand"
        payload = {"competence": competence}
        try:
            headers = self._get_headers()
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code in [200, 202]:
                return resp.json()
            elif resp.status_code == 409:
                print("Já existe uma solicitação recente e válida. Tente novamente mais tarde.")
                print(resp.text)
                return {}
            else:
                print(f"Erro ao solicitar conciliação on demand: {resp.status_code} - {resp.text}")
                return {}
        except Exception as e:
            print(f"Erro ao solicitar conciliação on demand: {e}")
            return {}

    # 7️⃣ Get Reconciliation On Demand by requestId (GET)
    def get_reconciliation_on_demand(self, request_id: str) -> dict:
        url = f"{self.base_url}/merchants/{self.merchant_id}/reconciliation/on-demand/{request_id}"
        try:
            headers = self._get_headers()
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                print("Arquivo de conciliação não encontrado para o requestId informado.")
                return {}
            else:
                print(f"Erro ao consultar conciliação on demand: {resp.status_code} - {resp.text}")
                return {}
        except Exception as e:
            print(f"Erro ao consultar conciliação on demand: {e}")
            return {}

# Exemplo de uso:
if __name__ == "__main__":
    financial = IfoodFinancialService()
    print("Conciliação:", financial.get_reconciliation("2025-09"))
    print("Settlements:", financial.get_settlements("2025-09-01", "2025-10-16"))
    print("Antecipações:", financial.get_anticipations("2025-09-01", "2025-10-16"))
    print("Vendas:", financial.get_sales("2025-09-01", "2025-10-16"))
    print("Eventos financeiros:", financial.get_financial_events("2025-09-01", "2025-10-16"))
    print("Solicitação conciliação on demand:", financial.request_reconciliation_on_demand("2025-08"))
    print("Consulta conciliação on demand:", financial.get_reconciliation_on_demand("2ca49751-7fe8-40a9-b8d1-e1318af89e5c"))