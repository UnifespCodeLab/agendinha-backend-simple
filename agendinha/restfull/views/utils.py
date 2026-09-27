from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from datetime import datetime, timedelta
import jwt
from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from datetime import datetime, timedelta
from django.shortcuts import render
from drf_spectacular.utils import extend_schema
from rest_framework import status

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
