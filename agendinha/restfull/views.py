from google.oauth2 import id_token
from google.auth.transport import requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
import jwt
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import Usuario, Responsavel, Agendamento, Notificacao, Role
from .serializers import (
    UserRegisterSerializer,
    UserLoginSerializer, UserLoginResponseSerializer, UserUpdateSerializer,
    AdminRegisterSerializer, UserSerializer,
    AppointmentRequestSerializer, AppointmentSerializer,
    AppointmentInfoSerializer, NotificationSerializer,
    UserUpdatePasswordSerializer, UserGoogleLoginSerializer,
    UserRequestNewPasswordSerializer, GuardianSerializer, GuardianRequestSerializer
)
from .permissions import IsAdmin, IsUser, IsAdminOrUser
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from datetime import datetime, timedelta
from .models import PushSubscription
from pywebpush import webpush
#from django.views.decorators.csrf import csrf_exempt
from google_auth_oauthlib.flow import InstalledAppFlow
from django.shortcuts import render

import json

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

    data = serializer.validated_data

    try:
        id = id_token.verify_oauth2_token(
            data["token"],
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

def convert_to_iso(date_string):
    input_format = "%d/%m/%Y %H:%M"
    
    dt_obj = datetime.strptime(date_string, input_format)
    
    return dt_obj.isoformat()

@api_view(['POST'])
@permission_classes([IsAdminOrUser])
def appointment_export_task_to_google_calendar(request):
    appointment = request.data['exam']

    appointment_date = convert_to_iso(appointment['data'])
    dt = datetime.fromisoformat(appointment_date)
    new_dt = dt + timedelta(hours=1)
    new_iso_time = new_dt.isoformat()

    task = {
        'summary': appointment['titulo'],
        'location': appointment['local'],
        'description': appointment['descricao'] + ', Médico responsável: ' + appointment['medico'],
        'start': {
            'dateTime': appointment_date,
            'timeZone': 'America/Sao_Paulo',
        },
        'end': {
            'dateTime': new_iso_time,
            'timeZone': 'America/Sao_Paulo',
        },
        'colorId': 6,
    }

    new_tokens = {}

    try:
        tokens = request.data['tokens']
        credentials = Credentials(
            token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            id_token=tokens['id_token'],
            token_uri=settings.GOOGLE_TOKEN_URI,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=['https://www.googleapis.com/auth/calendar'],
            default_scopes=[]
        )
        service = build('calendar', 'v3', credentials=credentials)
        event = service.events().insert(calendarId='primary', body=task).execute()
    except:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", ['https://www.googleapis.com/auth/calendar']
        )
        credentials = flow.run_local_server(port=8002)
        event = service.events().insert(calendarId='primary', body=task).execute()
        new_tokens = credentials.to_json()
    
    if event['status'] == 'confirmed':
        return Response({"event_id": event["id"], "tokens": new_tokens}, status=status.HTTP_200_OK)
    
    return Response({"error": "Não foi possível criar um agendamento."}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAdminOrUser])
def save_subscription(request):
    data = json.loads(request.body)

    user = Usuario.objects.get(id_usuario=data["id_usuario"])

    PushSubscription.objects.update_or_create(
        usuario=user,
        endpoint=data["endpoint"],
        defaults={
            "p256dh": data["keys"]["p256dh"],
            "auth": data["keys"]["auth"],
        }
    )

    return Response({"status": "saved"}, status=status.HTTP_200_OK)

def send_push(id_usuario, title, body, url="/"):
    subscriptions = PushSubscription.objects.filter(id_usuario=id_usuario)
    for sub in subscriptions:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {
                    "p256dh": sub.p256dh,
                    "auth": sub.auth,
                },
            },
            data=json.dumps({
                "title": title,
                "body": body,
                "url": url,
            }),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": settings.VAPID_ADMIN_EMAIL,
            },
        )    

@api_view(['POST'])
@permission_classes([AllowAny])
def user_request_password_update(request):
    serializer = UserRequestNewPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        user = Usuario.objects.get(email=data["email"])
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

    notificacoes = Notificacao.objects.filter(usuario=serializer.data['id_usuario'])
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
    graacc = request.data['graacc']

    try:
        user = Usuario.objects.get(id_usuario=user_id)
        user.ativar_notificacoes_consultas = appointments
        user.ativar_notificacoes_graacc = graacc
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


# ============================================================================
# VIEWS DE RESPONSÁVEIS
# ============================================================================

@extend_schema(
    tags=['Responsáveis'],
    summary='Criar responsável',
    description='Cria um novo responsável no sistema (somente ADMIN)',
    request=GuardianSerializer,
    responses={200: GuardianSerializer, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(['POST'])
@permission_classes([IsAdmin])
def guardian_create(request):
    """
    POST /responsaveis
    Cria novo responsável (ADMIN apenas)
    """
    serializer = GuardianSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Verifica se responsável com mesmo nome já existe
    if Responsavel.objects.filter(nome=serializer.validated_data['nome']).exists():
        return Response(
            {"message": "Responsável ja existe na base de dados."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    try:
        guardian = serializer.save()
        return Response(
            GuardianSerializer(guardian).data,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"message": "Erro ao salvar responsável."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Responsáveis'],
    summary='Listar responsáveis',
    description='Lista todos os responsáveis cadastrados (somente ADMIN)',
    responses={200: GuardianSerializer(many=True), 204: None},
)
@api_view(['GET'])
@permission_classes([IsAdmin])
def guardian_list(request):
    """
    GET /responsaveis
    Lista todos os responsáveis (ADMIN apenas)
    """
    responsaveis = Responsavel.objects.all()
    
    if not responsaveis.exists():
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    serializer = GuardianSerializer(responsaveis, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Responsáveis'],
    summary='Atualizar responsável',
    description='Edita os dados de um responsável existente (somente ADMIN)',
    parameters=[OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    request=GuardianSerializer,
    responses={200: GuardianSerializer, 204: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(['PUT'])
@permission_classes([IsAdmin])
def guardian_update(request, id):
    """
    PUT /responsaveis/{id}
    Edita responsaveis (ADMIN apenas)
    """
    try:
        responsavel = Responsavel.objects.get(id_responsavel=id)
    except Responsavel.DoesNotExist:
        return Response(
            {"message": "Responsável inexistente com esse id na base de dados."},
            status=status.HTTP_204_NO_CONTENT
        )
    
    serializer = GuardianSerializer(responsavel, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        responsavel = serializer.save()
        return Response(
            GuardianSerializer(responsavel).data,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"message": "Erro ao editar responsável."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Responsáveis'],
    summary='Deletar responsável',
    description='Remove um responsável do sistema (somente ADMIN)',
    parameters=[OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    responses={200: None, 500: OpenApiTypes.OBJECT},
)
@api_view(['DELETE'])
@permission_classes([IsAdmin])
def guardian_delete(request, id):
    """
    DELETE /responsaveis/{id}
    Deleta responsável (ADMIN apenas)
    """
    try:
        responsavel = Responsavel.objects.get(id_responsavel=id)
        responsavel.delete()
        return Response(status=status.HTTP_200_OK)
    except Responsavel.DoesNotExist:
        return Response(
            {"message": "Responsável inexistente com esse id na base de dados."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"message": "Erro ao deletar Responsável."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Responsáveis'],
    summary='Buscar responsável por nome',
    description='Busca um responsável pelo nome completo',
    request=GuardianRequestSerializer,
    responses={200: GuardianSerializer, 204: None},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def guardian_search_by_name(request):
    """
    POST /responsaveis/pesquisar
    Busca responsável por nome (público)
    """
    serializer = GuardianRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        responsavel = Responsavel.objects.get(nome=serializer.validated_data['nome'])
        return Response(
            GuardianSerializer(responsavel).data,
            status=status.HTTP_200_OK
        )
    except Responsavel.DoesNotExist:
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=['Responsáveis'],
    summary='Buscar responsável por ID',
    description='Busca um responsável pelo seu identificador',
    parameters=[OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    responses={200: GuardianSerializer, 204: None},
)
@api_view(['GET'])
@permission_classes([AllowAny])
def guardian_search_by_id(request, id):
    """
    GET /responsaveis/pesquisar/{id}
    Busca responsável por ID (público)
    """
    try:
        responsavel = Responsavel.objects.get(id_responsavel=id)
    except Responsavel.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    return Response(
        GuardianSerializer(responsavel).data,
        status=status.HTTP_200_OK
    )


# ============================================================================
# VIEWS DE AGENDAMENTOS
# ============================================================================

@extend_schema(
    tags=['Agendamentos'],
    summary='Criar agendamento',
    description='Cria um novo agendamento para um usuário (somente ADMIN)',
    request=AppointmentRequestSerializer,
    responses={200: AppointmentSerializer, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(['POST'])
@permission_classes([IsAdmin])
def appointment_create(request):
    """
    POST /agendamentos
    Cria novo agendamento (ADMIN apenas)
    Migrado de: AppointmentController.addAppointment()
    """
    serializer = AppointmentRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Busca usuário por id
    try:
        user = Usuario.objects.get(id_usuario=request.data['id_usuario'])
    except Usuario.DoesNotExist:
        return Response(
            {"message": "Erro ao inserir Agendamento - Usuário não encontrado."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Converte data string para datetime
    try:
        data_agendamento = datetime.strptime(
            serializer.validated_data['data'],
            '%d/%m/%Y %H:%M'
        )
    except ValueError:
        return Response(
            {"message": "Erro ao converter Data do Agendamento - tente novamento no formato dd/MM/yyyy HH:mm"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Cria agendamento
    try:
        agendamento = Agendamento(
            titulo=serializer.validated_data['titulo'],
            descricao=serializer.validated_data['descricao'],
            data=data_agendamento,
            local=serializer.validated_data['local'],
            usuario=user,
            medico=request.data['medico']
        )
        agendamento.save()
        
        return Response(
            AppointmentSerializer(agendamento).data,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"message": "Erro ao inserir Agendamento.", "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Agendamentos'],
    summary='Obter agendamento',
    description='Retorna os dados de um agendamento específico',
    parameters=[OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    responses={200: AppointmentSerializer, 204: None},
)
@api_view(['GET'])
@permission_classes([IsAdminOrUser])
def appointment_get(request, id):
    """
    GET /agendamentos/{id}
    Obtém agendamento por ID
    Migrado de: AppointmentController.getAppointment()
    """
    try:
        agendamento = Agendamento.objects.get(id_agendamento=id)
        return Response(
            AppointmentSerializer(agendamento).data,
            status=status.HTTP_200_OK
        )
    except Agendamento.DoesNotExist:
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=['Agendamentos'],
    summary='Listar agendamentos',
    description='Lista todos os agendamentos do sistema (somente ADMIN)',
    responses={200: AppointmentSerializer(many=True), 204: None},
)
@api_view(['GET'])
@permission_classes([IsAdmin])
def appointment_list(request):
    """
    GET /agendamentos
    Lista todos os agendamentos (ADMIN apenas)
    Migrado de: AppointmentController.getAll()
    """
    agendamentos = Agendamento.objects.all()
    
    if not agendamentos.exists():
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    serializer = AppointmentSerializer(agendamentos, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Agendamentos'],
    summary='Atualizar agendamento',
    description='Edita os dados de um agendamento existente (somente ADMIN)',
    parameters=[OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    request=AppointmentRequestSerializer,
    responses={200: AppointmentSerializer, 204: None, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(['PUT'])
@permission_classes([IsAdmin])
def appointment_update(request, id):
    """
    PUT /agendamentos/{id}
    Edita agendamento (ADMIN apenas)
    Migrado de: AppointmentController.editAppointment()
    """
    try:
        agendamento = Agendamento.objects.get(id_agendamento=id)
    except Agendamento.DoesNotExist:
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    serializer = AppointmentRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Busca usuário pelo ID
    try:
        user = Usuario.objects.get(id_usuario=request.data['id_usuario'])
    except Usuario.DoesNotExist:
        return Response(
            {"message": "Erro ao editar Agendamento - Usuário nao encontrado."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Converte data string para datetime
    try:
        data_agendamento = datetime.strptime(
            serializer.validated_data['data'],
            '%d/%m/%Y %H:%M'
        )
    except ValueError:
        return Response(
            {"message": "Erro ao converter Data do Agendamento - tente novamento no formato dd/MM/yyyy HH:mm"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Atualiza agendamento
    try:
        agendamento.titulo = serializer.validated_data['titulo']
        agendamento.descricao = serializer.validated_data['descricao']
        agendamento.data = data_agendamento
        agendamento.local = serializer.validated_data['local']
        agendamento.user = user
        agendamento.save()
        
        return Response(
            AppointmentSerializer(agendamento).data,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"message": "Erro ao editar Agendamento."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Agendamentos'],
    summary='Deletar agendamento',
    description='Remove um agendamento do sistema (somente ADMIN)',
    parameters=[OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    responses={200: None, 500: OpenApiTypes.OBJECT},
)
@api_view(['DELETE'])
@permission_classes([IsAdmin])
def appointment_delete(request, id):
    """
    DELETE /agendamentos/{id}
    Deleta agendamento (ADMIN apenas)
    Migrado de: AppointmentController.deleteAppointment()
    """
    try:
        agendamento = Agendamento.objects.get(id_agendamento=id)
        agendamento.delete()
        return Response(status=status.HTTP_200_OK)
    except Agendamento.DoesNotExist:
        return Response(
            {"message": "Não foi possível deletar Agendamento, pois não foi encontrado nenhum Agendamento com esse id."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"message": "Erro ao deletar Agendamento."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Agendamentos'],
    summary='Listar agendamentos do usuário',
    description='Lista os agendamentos do usuário associado ao usuário autenticado',
    responses={200: AppointmentSerializer(many=True), 204: None},
)
@api_view(['GET'])
@permission_classes([IsUser])
def appointment_list_user(request):
    """
    GET /agendamentos/usuario
    Lista agendamentos do usuário autenticado (USER apenas)
    Migrado de: AppointmentUserController.getAppointment()
    """
    user_info = request.user
    
    # Busca agendamentos do usuário
    agendamentos = Agendamento.objects.filter(usuario__id_usuario=user_info.id_usuario)
    
    if not agendamentos.exists():
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    serializer = AppointmentSerializer(agendamentos, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ============================================================================
# VIEWS DE NOTIFICAÇÕES
# ============================================================================

@extend_schema(
    tags=['Notificações'],
    summary='Criar notificações',
    description='Cria notificações automáticas para um agendamento (1 semana, 3 dias, 1 dia e 4 horas antes)',
    request=AppointmentInfoSerializer,
    responses={200: NotificationSerializer(many=True), 204: None, 400: OpenApiTypes.OBJECT},
)
@api_view(['POST'])
@permission_classes([IsAdmin])
@transaction.atomic
def notification_create(request):
    """
    POST /notificacoes
    Cria notificações para um agendamento (ADMIN apenas)
    Migrado de: NotificationController.registerNotifications()
    """
    serializer = AppointmentInfoSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Converte data string para datetime
    try:
        data_agendamento = datetime.strptime(
            serializer.validated_data['data_agendamento'],
            '%d/%m/%Y %H:%M'
        )
        # Torna timezone-aware
        data_agendamento = timezone.make_aware(data_agendamento)
    except ValueError:
        return Response(
            {"message": "Formato de data inválido. Use dd/MM/yyyy HH:mm"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Gera datas das notificações
    notification_dates = [
        data_agendamento - timedelta(weeks=1),      # 1 semana antes
        data_agendamento - timedelta(days=3),       # 3 dias antes
        data_agendamento - timedelta(days=1),       # 1 dia antes
        data_agendamento - timedelta(hours=4),      # 4 horas antes
    ]
    
    # Filtra apenas datas futuras
    now = timezone.now()
    future_dates = [d for d in notification_dates if d > now]
    
    if not future_dates:
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    user = Usuario.objects.get(id_usuario=serializer.validated_data['id_usuario'])

    # Cria notificações
    notifications = []
    for data in future_dates:
        notificacao = Notificacao(
            id_agendamento=serializer.validated_data['id_agendamento'],
            data=data,
            lida=False,
            user=user,
            titulo=serializer.validated_data['titulo'],
            descricao=serializer.validated_data['descricao'],
        )
        notificacao.save()
        notifications.append(notificacao)

        send_push(user.id_usuario, "Notificação", "Novo agendamento marcado.")
    
    response_serializer = NotificationSerializer(notifications, many=True)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notificações'],
    summary='Criar notificações em lote',
    description='Cria notificações para múltiplos agendamentos de uma só vez',
    request=AppointmentInfoSerializer(many=True),
    responses={200: NotificationSerializer(many=True), 204: None},
)
@api_view(['POST'])
@permission_classes([IsAdmin])
@transaction.atomic
def notification_create_batch(request):
    """
    POST /notificacoes/conjunto
    Cria notificações para múltiplos agendamentos (ADMIN apenas)
    Migrado de: NotificationController.registerMultipleNotifications()
    """
    serializer = AppointmentInfoSerializer(data=request.data, many=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    all_notifications = []
    now = timezone.now()
    
    for appointment_info in serializer.validated_data:
        # Converte data string para datetime
        try:
            data_agendamento = datetime.strptime(
                appointment_info['data_agendamento'],
                '%d/%m/%Y %H:%M'
            )
            # Torna timezone-aware
            data_agendamento = timezone.make_aware(data_agendamento)
        except ValueError:
            continue
        
        # Gera datas das notificações
        notification_dates = [
            data_agendamento - timedelta(weeks=1),
            data_agendamento - timedelta(days=3),
            data_agendamento - timedelta(days=1),
            data_agendamento - timedelta(hours=4),
        ]
        
        # Filtra apenas datas futuras
        future_dates = [d for d in notification_dates if d > now]
        
        # Cria notificações
        for data in future_dates:
            notificacao = Notificacao(
                id_agendamento=appointment_info['id_agendamento'],
                data=data,
                lida=False
            )
            notificacao.save()
            all_notifications.append(notificacao)
    
    if not all_notifications:
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    response_serializer = NotificationSerializer(all_notifications, many=True)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notificações'],
    summary='Listar notificações por agendamento',
    description='Retorna todas as notificações de um agendamento específico',
    parameters=[OpenApiParameter('id_agendamento', OpenApiTypes.INT, OpenApiParameter.PATH)],
    responses={200: NotificationSerializer(many=True), 204: None},
)
@api_view(['GET'])
@permission_classes([IsAdminOrUser])
def notification_list_by_appointment(request, id_agendamento):
    """
    GET /notificacoes/{idAgendamento}
    Lista notificações de um agendamento
    Migrado de: NotificationController.findNotification()
    """
    notificacoes = Notificacao.objects.filter(id_agendamento=id_agendamento)
    
    if not notificacoes.exists():
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    serializer = NotificationSerializer(notificacoes, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAdminOrUser])
def notification_list_by_user(request, id_usuario):
    """
    GET /notificacoes/{idUsuario}
    Lista notificações de um agendamento
    Migrado de: NotificationController.findNotification()
    """
    notificacoes = Notificacao.objects.filter(usuario=id_usuario)
    
    if not notificacoes.exists():
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    serializer = NotificationSerializer(notificacoes, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    tags=['Notificações'],
    summary='Listar notificações não lidas',
    description='Retorna notificações não lidas com datas futuras para os agendamentos informados',
    request=AppointmentInfoSerializer(many=True),
    responses={200: NotificationSerializer(many=True), 204: None, 400: OpenApiTypes.OBJECT},
)
@api_view(['POST'])
@permission_classes([IsAdminOrUser])
def notification_list_unread(request):
    """
    POST /notificacoes/naoLidas
    Lista notificações não lidas com datas futuras
    Migrado de: NotificationController.findNotReadNotification()
    """
    serializer = AppointmentInfoSerializer(data=request.data, many=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    now = timezone.now()
    all_notifications = []
    
    for appointment_info in serializer.validated_data:
        notificacoes = Notificacao.objects.filter(
            id_agendamento=appointment_info['id_agendamento'],
            lida=False,
            data__gt=now
        )
        all_notifications.extend(notificacoes)
    
    if not all_notifications:
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    response_serializer = NotificationSerializer(all_notifications, many=True)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notificações'],
    summary='Marcar notificação como lida',
    description='Marca uma notificação específica como lida',
    parameters=[OpenApiParameter('id_notificacao', OpenApiTypes.INT, OpenApiParameter.PATH)],
    responses={200: NotificationSerializer, 400: None},
)
@api_view(['POST'])
@permission_classes([IsAdminOrUser])
def notification_mark_as_read(request, id_notificacao):
    """
    POST /notificacoes/{idNotificacao}/lida
    Marca notificação como lida
    Migrado de: NotificationController.readNotification()
    """
    try:
        notificacao = Notificacao.objects.get(id_notificacao=id_notificacao)
        notificacao.lida = True
        notificacao.save()
        
        serializer = NotificationSerializer(notificacao)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Notificacao.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Notificações'],
    summary='Deletar notificações por agendamento',
    description='Remove todas as notificações de um agendamento (somente ADMIN)',
    parameters=[OpenApiParameter('id_agendamento', OpenApiTypes.INT, OpenApiParameter.PATH)],
    responses={200: None, 500: OpenApiTypes.OBJECT},
)
@api_view(['DELETE'])
@permission_classes([IsAdmin])
@transaction.atomic
def notification_delete_by_appointment(request, id_agendamento):
    """
    DELETE /notificacoes/{idAgendamento}
    Deleta todas as notificações de um agendamento (ADMIN apenas)
    Migrado de: NotificationController.deleteNotifications()
    """
    try:
        Notificacao.objects.filter(id_agendamento=id_agendamento).delete()
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"message": "Erro ao deletar notificações."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAdminOrUser])
@transaction.atomic
def notification_delete_by_id(request, id_notificacao):
    """
    DELETE /notificacoes/id/{idNotificacao}
    Deleta a notificação a partir de um id
    Migrado de: NotificationController.deleteNotifications()
    """
    try:
        Notificacao.objects.filter(id_notificacao=id_notificacao).delete()
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"message": "Erro ao deletar notificação."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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
