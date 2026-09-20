from django.core.mail import EmailMultiAlternatives
from google.oauth2 import id_token
from ..models import Notificacao, Usuario, Role, Responsavel
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from ..permissions import IsAdmin, IsAdminOrUser
from .utils import generate_custom_jwt
from google.auth.transport import requests
from ..serializers import (
    NotificationSerializer,
    UserRegisterSerializer,
    UserLoginSerializer, UserLoginResponseSerializer, UserUpdateSerializer,
    UserSerializer,
    UserUpdatePasswordSerializer, UserGoogleLoginSerializer,
    UserRequestNewPasswordSerializer
)
from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.template.loader import render_to_string
from django.db import transaction
from rest_framework.parsers import MultiPartParser, FormParser

# ============================================================================
# VIEWS DE AUTENTICAÇÃO - USUÁRIOS
# ============================================================================

@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Registrar novo usuário',
    description='Registra um novo usuário comum associado a um responsável existente pelo nome',
    request=UserRegisterSerializer,
    responses={
        200: None,
        400: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            'Exemplo de registro',
            value={
                'nome': 'João Silva',
                'email': 'joao@email.com',
                'senha': 'senha123',
                'nome_completo_responsavel': 'Maria Silva'
            },
            request_only=True,
        ),
    ]
)
@api_view(['POST'])
@permission_classes([AllowAny])
def user_register(request):
    """
    POST /usuarios/registrar
    Registra usuário comum
    Migrado de: UserController.addUser()
    """
    serializer = UserRegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assert isinstance(serializer.validated_data, dict)
    
    # Verifica se email já existe
    if Usuario.objects.filter(email=serializer.validated_data['email']).exists():
        return Response(
            {"message": "Email já cadastrado"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Cria usuário
    try:
        user = Usuario(
            nome=serializer.validated_data['nome'],
            email=serializer.validated_data['email'],
            role=Role.USER,
            cadastro_confirmado=False
        )
        user.set_password(serializer.validated_data['senha'])
        user.save()
        user_register_email_confirm(user) 
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"message": "Erro ao inserir usuario."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def user_register_email_confirm(user: Usuario):
    token = user.make_token()
    reset_link = f"{settings.FRONTEND_URL}/conta/{user.id_usuario}/{token}"
    subject = 'Confirmação de cadastro - Agendinha do GRAACC'
    text_content = 'E-mail para confirmação de cadastro'
    html_message = render_to_string('confirm_account_email.html', {'nome': user.nome, 'reset_link': reset_link })
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [user.email])
    msg.attach_alternative(html_message, "text/html")
    msg.send()
    
@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Login de usuário',
    description='Realiza login de usuário comum e retorna token JWT',
    request=UserLoginSerializer,
    responses={200: UserLoginResponseSerializer, 400: None},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    """
    POST /usuarios/login
    Login de usuário comum
    Migrado de: UserController.login()
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

    if user.modo_google:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    user_serializer = UserSerializer(user)

    notifications_obj = Notificacao.objects.filter(usuario=user.id_usuario)
    notifications_data = NotificationSerializer(notifications_obj, many=True).data

    # Gera token JWT customizado
    token = generate_custom_jwt(user)

    response_data = {
        'usuario': user_serializer.data,
        'notificacoes': notifications_data,
        'token': token
    }

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def user_login_google(request):
    serializer = UserGoogleLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assert isinstance(serializer.validated_data, dict)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        id = id_token.verify_oauth2_token(
            serializer.validated_data["token"],
            requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )

        email = id["email"]
        first_name = id.get("given_name", "")
        last_name = id.get("family_name", "")

        user, created = Usuario.objects.get_or_create(email=email)

        # Gera token JWT customizado
        token = generate_custom_jwt(user)

        if created:
            user.nome = f"{first_name} {last_name}"
            user.modo_google = True
            user.save_image_from_url(id['picture'])
            user.save()

            user_serializer = UserSerializer(user)

            response_data = {
                'usuario': user_serializer,
                'notificacoes': [],
                'token': token,
            }
        else:
            if not user.modo_google:
                return Response({
                    "error": "Usuário precisa logar via e-mail.",
                }, status=status.HTTP_403_FORBIDDEN)
            
            user_serializer = UserSerializer(user)

            if not user_serializer.is_valid():
                return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            assert isinstance(user_serializer.data, dict)

            notifications_obj = Notificacao.objects.filter(id_usuario=user_serializer.data['id_usuario'])
            notifications_data = NotificationSerializer(notifications_obj, many=True).data
            
            response_data = {
                'usuario': user_serializer,
                'notificacoes': notifications_data,
                'token': token,
            }

        return Response(response_data, status=status.HTTP_200_OK)

    except ValueError:
        return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def user_request_password_update(request):
    serializer = UserRequestNewPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assert isinstance(serializer.validated_data, dict)

    try:
        user = Usuario.objects.get(email=serializer.validated_data["email"])
        if not user:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        if user.modo_google or not user.cadastro_confirmado:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        user_request_password_update_email(user)

        return Response(status=status.HTTP_200_OK)
    except ValueError:
        return Response(status=status.HTTP_400_BAD_REQUEST)

def user_request_password_update_email(user: Usuario):
    token = user.make_token()
    reset_link = f"{settings.FRONTEND_URL}/senha/{user.id_usuario}/{token}"
    subject = 'Alteração de Senha - Agendinha do GRAACC'
    text_content = 'E-mail para alteração de senha'
    html_message = render_to_string('password_reset_email.html', {'nome': user.nome, 'reset_link': reset_link })
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [user.email])
    msg.attach_alternative(html_message, "text/html")
    msg.send()    

@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Confirmar cadastro',
    description='Confirma o cadastro do usuário autenticado',
    request=None,
    responses={200: None},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def user_confirm(request):
    """
    POST /usuarios/confirmar
    Confirma cadastro do usuário autenticado
    Migrado de: UserController.confirmUser()
    """
    user_info = request.data
    user = None

    if 'id_usuario' in user_info:
        user = Usuario.objects.get(id_usuario=user_info['id_usuario'])
    elif 'email' in user_info:
        user = Usuario.objects.get(email=user_info['email'])
    else:
        return Response(
            {"detail": "id_usuario or email must be provided."},
            status=status.HTTP_400_BAD_REQUEST
        )

    user.cadastro_confirmado = True
    user.save()
    return Response(status=status.HTTP_200_OK)


@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Obter dados do usuário',
    description='Retorna os dados do usuário autenticado',
    request=None,
    responses={200: UserSerializer},
)
@api_view(['GET'])
@permission_classes([IsAdminOrUser])
def user_get(request):
    """
    GET /usuarios
    Retorna dados do usuário autenticado
    Migrado de: UserController.getUser()
    """
    user_info = request.user
    user = Usuario.objects.get(id_usuario=user_info.id_usuario)
    serializer = UserSerializer(user)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assert isinstance(serializer.validated_data, dict)

    notificacoes = Notificacao.objects.filter(usuario=serializer.validated_data['id_usuario'])
    todas_notificacoes = NotificationSerializer(notificacoes, many=True).data

    return Response({
        'usuario': serializer.data,
        'notificacoes': todas_notificacoes
    }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Pesquisar usuário por nome',
    description='Busca usuários pelo nome (apenas ADMIN)',
    parameters=[OpenApiParameter('nome', OpenApiTypes.STR, OpenApiParameter.QUERY)],
    responses={200: UserSerializer(many=True)},
)
@api_view(['GET'])
@permission_classes([IsAdmin])
def user_search_by_name(request):
    """
    GET /usuarios/pesquisar?nome=...
    Pesquisa pacientes por nome
    """
    nome = request.GET.get('nome', '')
    if not nome:
        return Response([], status=status.HTTP_200_OK)
        
    usuarios = Usuario.objects.filter(role=Role.USER, nome__icontains=nome)[:50]
    serializer = UserSerializer(usuarios, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Atualizar dados do usuário',
    description='Atualiza nome, email ou responsável associado do usuário autenticado',
    request=UserUpdateSerializer,
    responses={200: None, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(['PUT'])
@permission_classes([IsAdminOrUser])
def user_update(request):
    """
    PUT /usuarios
    Atualiza dados do usuário autenticado
    Migrado de: UserController.updateUser()
    """
    serializer = UserUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assert isinstance(serializer.validated_data, dict)

    user_info = request.user
    user = Usuario.objects.get(id_usuario=user_info.id_usuario)

    try:
        with transaction.atomic():
            # Atualiza nome se fornecido
            if serializer.validated_data.get('nome'):
                user.nome = serializer.validated_data['nome']
            
            # Atualiza email se fornecido
            if serializer.validated_data.get('email'):
                # Verifica se email já existe (diferente do atual)
                if Usuario.objects.filter(email=serializer.validated_data['email']).exclude(id_usuario=user.id_usuario).exists():
                    return Response(
                        {"message": "Email já cadastrado por outro usuário"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user.email = serializer.validated_data['email']
            
            # Atualiza responsável se fornecido
            if serializer.validated_data.get('nome_completo_responsavel'):
                try:
                    responsavel = Responsavel.objects.get(nome=serializer.validated_data['nome_completo_responsavel'])
                    user.responsavel = responsavel
                except Responsavel.DoesNotExist:
                    return Response(
                        {"message": "Não existe nenhum responsável com esse nome"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            user.save()
            return Response(status=status.HTTP_200_OK)
            
    except Exception as e:
        return Response(
            {"message": "Não foi possível atualizar o Usuário."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
@permission_classes([IsAdminOrUser])
def user_notification_status_update(request):
    user_id = request.data['id']
    appointments = request.data['appointments']

    try:
        user = Usuario.objects.get(id_usuario=user_id)
        user.ativar_notificacoes_consultas = appointments
        user.save()
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"message": "Não foi possível atualizar o status de notificação do Usuário."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@permission_classes([IsAdminOrUser])
@parser_classes([MultiPartParser, FormParser])
def user_avatar_update(request):
    user_id = request.data['id']
    profile_image = request.data['foto_perfil']
    
    try:
        user = Usuario.objects.get(id_usuario=user_id)
        user.foto_perfil = profile_image
        user.save()
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"message": "Não foi possível atualizar o Usuário."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
@permission_classes([IsAdminOrUser])
def user_password_update(request):
    serializer = UserUpdatePasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assert isinstance(serializer.validated_data, dict)

    id = request.data['id']
    try:
        user = Usuario.objects.get(id_usuario=id)
        if not user.check_password(serializer.validated_data['senha_atual']):
            return Response(
                {"message": "Senha atual incompatível."},
                status=status.HTTP_401_UNAUTHORIZED
            )       
        user.set_password(serializer.validated_data['senha_nova'])
        user.save()
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"message": "Não foi possível atualizar a senha do usuário."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
@permission_classes([AllowAny])
def user_password_update_without_auth(request):
    id = request.data['id']
    try:
        user = Usuario.objects.get(id_usuario=id)
        if not user:
            return Response(
                {"message": "Usuário não encontrado."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        user.set_password(request.data['senha_nova'])
        user.save()
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"message": "Não foi possível atualizar a senha do usuário."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Deletar usuário',
    description='Remove o usuário autenticado do sistema',
    request=None,
    responses={200: None, 500: OpenApiTypes.OBJECT},
)
@api_view(['DELETE'])
@permission_classes([IsAdminOrUser])
def user_delete(request):
    """
    DELETE /usuarios
    Deleta usuário autenticado
    Migrado de: UserController.deleteUser()
    """
    user_info = request.user
    
    try:
        user = Usuario.objects.get(id_usuario=user_info.id_usuario)
        user.delete()
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"message": "Não existe nenhum usuario com esse id"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )