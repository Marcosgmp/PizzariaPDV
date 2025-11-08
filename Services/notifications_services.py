from Services.orders import create_cash_alert
from typing import Optional
import requests

def send_whatsapp_message(number: str, message: str) -> dict:
    """
    Envia uma mensagem via WhatsApp usando Waha.

    Args:
        number (str): Número do destinatário com código do país.
        message (str): Conteúdo da mensagem.

    Returns:
        dict: Resposta do servidor Waha.
    """
    url = "http://localhost:3000/sendText"
    payload = {"number": number, "message": message}
    response = requests.post(url, json=payload)
    return response.json()
