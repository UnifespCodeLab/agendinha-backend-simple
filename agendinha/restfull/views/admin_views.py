from ..models import Usuario, Role
from .utils import generate_custom_jwt
from ..serializers import (
    AdminRegisterSerializer, UserLoginSerializer, UserLoginResponseSerializer
)
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

# ============================================================================
# VIEWS DE AUTENTICAÇÃO - ADMIN
# ============================================================================

@extend_schema(
    tags=['Autenticação - Admin'],
    summary='Registrar administrador',
    description='Registra um novo usuário administrador no sistema',
    request=AdminRegisterSerializer,
    responses={200: None, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def admin_register(request):
    """
    POST /admin/registrar
    Registra administrador
    Migrado de: AdminController.addAdmin()
    """
    serializer = AdminRegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assert isinstance(serializer.validated_data, dict)
    
    # Verifica se email já existe
    if Usuario.objects.filter(email=serializer.validated_data['email']).exists():
        return Response(
            {"message": "Email já cadastrado"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Cria admin
    try:
        admin = Usuario(
            nome=serializer.validated_data['nome'],
            email=serializer.validated_data['email'],
            role=Role.ADMIN,
            cadastro_confirmado=False
        )
        admin.set_password(serializer.validated_data['senha'])
        admin.save()
        
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"message": "Erro ao inserir usuario ADMIN."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Autenticação - Admin'],
    summary='Login de administrador',
    description='Realiza login de administrador e retorna token JWT',
    request=UserLoginSerializer,
    responses={200: UserLoginResponseSerializer, 400: None},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    """
    POST /admin/login
    Login de administrador
    Migrado de: AdminController.login()
    """
    serializer = UserLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assert isinstance(serializer.validated_data, dict)
    
    try:
        user = Usuario.objects.get(email=serializer.validated_data['email'])
    except Usuario.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    
    # Verifica senha
    if not user.check_password(serializer.validated_data['senha']):
        return Response(status=status.HTTP_400_BAD_REQUEST)
    
    # Gera token JWT customizado
    token = generate_custom_jwt(user)
    
    response_data = {
        'nome': user.nome,
        'token': token
    }
    
    return Response(response_data, status=status.HTTP_200_OK)