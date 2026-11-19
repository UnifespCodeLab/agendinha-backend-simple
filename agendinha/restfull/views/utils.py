from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import jwt
from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from datetime import datetime, timedelta
from django.shortcuts import render
from drf_spectacular.utils import extend_schema
from rest_framework import status
import requests as http_requests
import logging

logger = logging.getLogger(__name__)

GOOGLE_REDIRECT_URI = "postmessage"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"
EVENT_FIELDS = ("summary", "location", "description", "start", "end", "colorId")

class GoogleAuthError(Exception):
    """Falha na autenticação com o Google (code inválido, token inválido, etc.)."""
 
class GoogleUnavailableError(Exception):
    """Não foi possível falar com o Google (rede, timeout)."""

# ============================================================================
# ARQUIVOS ESTÁTICOS E TEMPLATES
# ============================================================================
def create_guardian_page(request):
    return render(request, 'create_guardian.html', {})

def create_appointment_page(request):
    return render(request, 'create_appointment.html', {})

def create_notification_page(request):
    return render(request, 'create_notification.html', {})

# ============================================================================
# UTILIDADES JWT
# ============================================================================

def generate_custom_jwt(user):
    """
    Gera JWT customizado compatível com os microserviços Java
    Claims: idUsuario, email, role
    """
    payload = {
        'sub': user.email,
        'iss': settings.SECURITY_EMISSOR,
        'idUsuario': user.id_usuario,
        'role': user.role,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=24)
    }

    token = jwt.encode(payload, settings.SECURITY_TOKEN, algorithm='HS256')
    return token

def convert_to_iso(date_string):
    input_format = "%d/%m/%Y %H:%M"
    
    dt_obj = datetime.strptime(date_string, input_format)
    
    return dt_obj.isoformat()

# ============================================================================
# HEALTH CHECK
# ============================================================================

def exchange_google_code(code: str, require_id_token: bool = True) -> dict:
    """
    Troca o authorization code por tokens no endpoint do Google
    e devolve o dict com id_token, access_token, scope e, na primeira
    autorização do usuário, refresh_token.
 
    require_id_token=False serve ao fluxo "só Google Agenda" (escopo sem
    openid), em que o Google não devolve id_token.
    """
    resp = _post_google_token({
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    })
    if resp.status_code != 200:
        logger.warning("Google rejeitou o code: %s", _google_error(resp))
        raise GoogleAuthError("Código de autorização inválido ou expirado.")
    tokens = resp.json()
    if require_id_token and not tokens.get("id_token"):
        raise GoogleAuthError("Resposta do Google sem id_token.")
    return tokens

def _post_google_token(data: dict) -> http_requests.Response:
    """POST no endpoint de token do Google, convertendo falha de rede."""
    try:
        return http_requests.post(settings.GOOGLE_TOKEN_URI, data=data, timeout=10)
    except http_requests.RequestException as exc:
        raise GoogleUnavailableError(str(exc)) from exc
 
 
def _google_error(resp: http_requests.Response) -> str:
    """Extrai o campo 'error' sem estourar se o corpo não for JSON."""
    try:
        return resp.json().get("error", "unknown")
    except ValueError:
        return "unknown"
 
 
def exchange_google_code(code: str) -> dict:
    """
    Troca o authorization code por tokens no endpoint do Google
    e devolve o dict com id_token, access_token, scope e, na primeira
    autorização do usuário, refresh_token.
    """
    resp = _post_google_token({
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    })
    if resp.status_code != 200:
        logger.warning("Google rejeitou o code: %s", _google_error(resp))
        raise GoogleAuthError("Código de autorização inválido ou expirado.")
    tokens = resp.json()
    if not tokens.get("id_token"):
        raise GoogleAuthError("Resposta do Google sem id_token.")
    return tokens
 
 
def save_google_refresh_token(user, tokens: dict) -> None:
    """
    Guarda o refresh token devolvido pelo Google. Ele só vem na primeira
    autorização: se não vier, mantém o que já existe.
    """
    refresh_token = tokens.get("refresh_token")
    if refresh_token and refresh_token != user.google_refresh_token:
        user.google_refresh_token = refresh_token
        user.save(update_fields=["google_refresh_token"])
 
 
def refresh_google_access_token(user) -> str:
    """Troca o refresh token guardado por um access token novo (~1h)."""
    if not user.google_refresh_token:
        raise GoogleAuthError("Usuário sem refresh token do Google.")
 
    resp = _post_google_token({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": user.google_refresh_token,
        "grant_type": "refresh_token",
    })
    if resp.status_code != 200:
        error = _google_error(resp)
        logger.warning("Google rejeitou o refresh token: %s", error)
        if error == "invalid_grant":
            # Acesso revogado ou refresh token expirado: força novo login
            user.google_refresh_token = None
            user.save(update_fields=["google_refresh_token"])
        raise GoogleAuthError("Autorização do Google expirada.")
 
    return resp.json()["access_token"]

def verify_google_id_token(raw_id_token: str) -> dict:
    """Valida assinatura, expiração e audiência (client_id) do id_token."""
    try:
        idinfo = id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise GoogleAuthError("Token do Google inválido.") from exc
 
    if not idinfo.get("email") or not idinfo.get("email_verified"):
        raise GoogleAuthError("E-mail do Google não verificado.")
    return idinfo

def format_date(date):
    return date.strftime("%d/%m/%Y %H:%M")

@extend_schema(
    tags=['Health Check'],
    summary='Teste de conectividade',
    description='Endpoint para verificar se a API está funcionando',
    responses={200: OpenApiTypes.STR},
)
@api_view(['GET'])
@permission_classes([AllowAny])
def hello_world(request):
    """
    GET /hello
    Endpoint de teste
    """
    return Response("Hello World from Agendinha API Unificada", status=status.HTTP_200_OK)
