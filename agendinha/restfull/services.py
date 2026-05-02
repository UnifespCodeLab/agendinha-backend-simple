import requests
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    """
    Serviço para integração com a API do WhatsApp da Akroz Group.
    """
    
    def __init__(self):
        self.base_url = os.getenv('WHATSAPP_API_BASE_URL', 'https://api.whatsapp.akrozgroup.com.br/api')
        self.token = os.getenv('WHATSAPP_API_TOKEN')
        self.endpoint = os.getenv('WHATSAPP_API_ENDPOINT', '/message/text')
        
    def format_phone_number(self, phone):
        """
        Formata o número de telefone para o padrão exigido pela API (WuzAPI).
        Remove caracteres não numéricos e garante o DDI 55.
        """
        if not phone:
            return None
            
        # Remove tudo que não for dígito (higienização)
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # Se não começar com 55 e tiver 10 ou 11 dígitos, adiciona 55
        if len(clean_phone) in [10, 11] and not clean_phone.startswith('55'):
            clean_phone = '55' + clean_phone
            
        return clean_phone

    def send_reminder(self, phone, message):
        """
        Envia uma mensagem de lembrete via WhatsApp usando WuzAPI.
        """
        if not self.token:
            logger.error("WhatsApp API Token não configurado.")
            return False, "Token não configurado"

        formatted_phone = self.format_phone_number(phone)
        if not formatted_phone:
            return False, "Número de telefone inválido"

        # Garante que a URL não tenha barras duplicadas
        url = f"{self.base_url.rstrip('/')}/{self.endpoint.lstrip('/')}"
        
        headers = {
            'token': self.token,  # WuzAPI usa header 'token'
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        payload = {
            'phone': formatted_phone,
            'message': message
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                logger.info(f"Lembrete enviado com sucesso para {formatted_phone}")
                return True, response.json()
            else:
                error_msg = f"Erro API WhatsApp ({response.status_code}): {response.text}"
                logger.error(error_msg)
                return False, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Falha na requisição para {formatted_phone}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
