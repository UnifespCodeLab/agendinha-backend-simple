from django.core.mail import EmailMultiAlternatives
from ..models import Notificacao, Usuario, Role, Responsavel
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from ..permissions import IsAdmin, IsAdminOrUser
from .utils import generate_custom_jwt
from rest_framework.pagination import PageNumberPagination
from ..serializers.admin import (
    AdminUserRegisterSerializer, AdminUserListSerializer,
    AdminUserUpdateSerializer
)
from ..serializers.notification import NotificationSerializer
from ..serializers.user import (
    UserRegisterSerializer,
    UserLoginSerializer, UserLoginResponseSerializer, UserUpdateSerializer,
    UserSerializer, UserIdentifierSerializer,
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
from django.db import transaction, IntegrityError
from rest_framework.parsers import MultiPartParser, FormParser
from ..utils import is_number
from .utils import (
    verify_google_id_token,
    GoogleAuthError,
    GoogleUnavailableError,
    exchange_google_code,
    CALENDAR_SCOPE,
    save_google_refresh_token
)
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

GOOGLE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
EVENT_FIELDS = ("summary", "location", "description", "start", "end", "colorId")

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
    
    if Usuario.objects.filter(email=serializer.validated_data['email']):
        return Response(
            {"message": "E-mail já está cadastrado."},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Atualiza pré-cadastro do usuário
    data = serializer.validated_data
    try:
        user = Usuario.objects.get(email=data['email'])
        if user.cadastro_confirmado:
            return Response(
                {"message": "Usuário já está cadastrado."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        user.email = data['email']
        user.set_password(data['senha'])
        user.save()
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"message": "Erro ao inserir usuario."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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
        return Response({"error": "E-mail inválido."}, status=status.HTTP_400_BAD_REQUEST)

    # Verifica senha
    if not user.check_password(serializer.validated_data['senha']):
        return Response(
            {"error": "Senha inválida."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if user.modo_google:
        return Response(
            {"error": "Usuário apenas pode fazer autenticação com Google."},
            status=status.HTTP_401_UNAUTHORIZED
        )

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
 
@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Login de usuário com Google OAuth2',
    description='Recebe o authorization code do Google, valida no servidor e retorna token JWT',
    request=UserGoogleLoginSerializer,
    responses={200: UserLoginResponseSerializer, 400: None, 401: None, 403: None, 502: None},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def user_login_google(request):
    serializer = UserGoogleLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
    try:
        google_tokens = exchange_google_code(serializer.validated_data["code"])
        idinfo = verify_google_id_token(google_tokens["id_token"])
    except GoogleUnavailableError:
        logger.exception("Falha de comunicação com o Google")
        return Response(
            {"message": "Não foi possível contatar o Google. Tente novamente."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except GoogleAuthError as exc:
        return Response({"message": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
 
    try:
        user = Usuario.objects.get(email=idinfo["email"])
    except Usuario.DoesNotExist:
        return Response(
            {"message": "E-mail não está cadastrado."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
 
    if user.cadastro_confirmado and not user.modo_google:
        return Response(
            {"message": "Usuário precisa logar via e-mail."},
            status=status.HTTP_403_FORBIDDEN,
        )
 
    if not user.modo_google:
        first_name = idinfo.get("given_name", "")
        last_name = idinfo.get("family_name", "")
        user.nome = user.nome or f"{first_name} {last_name}".strip()
        user.modo_google = True
        user.cadastro_confirmado = True
 
    picture = idinfo.get("picture")
    if picture:
        try:
            user.save_image_from_url(picture)
        except Exception:
            logger.warning("Não foi possível salvar a foto do usuário %s", user.pk)
 
    user.save()
    save_google_refresh_token(user, google_tokens)
 
    token = generate_custom_jwt(user)
 
    notifications = Notificacao.objects.filter(usuario_id=user.id_usuario)
 
    calendar_granted = CALENDAR_SCOPE in google_tokens.get("scope", "").split()
    google_access_token = google_tokens.get("access_token") if calendar_granted else None
 
    return Response(
        {
            "usuario": UserSerializer(user).data,
            "notificacoes": NotificationSerializer(notifications, many=True).data,
            "token": token,
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Pedido de alteração de senha do usuário',
    description='Envia um pedido de alteração de senha para o e-mail do usuário',
    request=UserRequestNewPasswordSerializer,
    responses={200: None, 400: None},
)
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
    subject = 'Alteração de Senha - Agendinha'
    text_content = 'E-mail para alteração de senha'
    html_message = render_to_string('password_reset_email.html', {'nome': user.nome, 'reset_link': reset_link })
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [user.email])
    msg.attach_alternative(html_message, "text/html")
    msg.send()    

@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Confirmar cadastro',
    description='Confirma o cadastro do usuário autenticado',
    request=UserIdentifierSerializer,
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
    serializer = UserIdentifierSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assert isinstance(serializer.validated_data, dict)
    
    user_info = serializer.validated_data
    user = None

    if is_number(user_info['identifier']):
        user = Usuario.objects.get(id_usuario=user_info['identifier'])
    elif isinstance(user_info['identifier'], str):
        user = Usuario.objects.get(email=user_info['identifier'])
    else:
        return Response(
            {"detail": "O id_usuario ou o email deve ser fornecido, ou os dados informados não foram preenchidos corretamente."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if user.cadastro_confirmado:
        return Response({"message": "Usuário já confirmou o cadastro."}, status=status.HTTP_403_FORBIDDEN)

    user.cadastro_confirmado = True
    user.save()
    return Response(status=status.HTTP_200_OK)

@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Confirmar cadastro e redefinir senha',
    description='Confirma o cadastro e atualiza senha do do usuário autenticado',
    request=UserUpdatePasswordSerializer,
    responses={200: None, 400: None},
)
@api_view(['PUT'])
@permission_classes([AllowAny])
def user_confirm_with_password_update(request):
    serializer = UserUpdatePasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assert isinstance(serializer.validated_data, dict)

    try:
        user = Usuario.objects.get(id_usuario=serializer.validated_data['id'])
        user.cadastro_confirmado = True
        user.set_password(serializer.validated_data['senha_nova'])
        user.save()
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"message": "Não foi possível atualizar a senha do usuário.",
             "error": e},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )   

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
    user = Usuario.objects.get(id_usuario=request.user.id_usuario)
    serializer = UserSerializer(user)

    notificacoes = Notificacao.objects.filter(usuario=user.id_usuario)
    todas_notificacoes = NotificationSerializer(notificacoes, many=True).data

    return Response({
        'usuario': serializer.data,
        'notificacoes': todas_notificacoes
    }, status=status.HTTP_200_OK)

@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Pesquisar usuário por id',
    description='Busca usuários pelo id, apenas se estiver com login',
    responses={200: UserSerializer()},
)
@api_view(['GET'])
@permission_classes([IsAdminOrUser])
def user_search_by_id(request):
    """
    GET /usuarios/pesquisar?id=...
    Pesquisa pacientes por id
    """
    id = request.GET.get('id', '')
    if not id:
        return Response({}, status=status.HTTP_200_OK)
        
    user = Usuario.objects.get(id_usuario=id)
    user_serializer = UserSerializer(user)

    notificacoes = Notificacao.objects.filter(usuario=id)
    todas_notificacoes = NotificationSerializer(notificacoes, many=True).data

    return Response({
        'usuario': user_serializer.data,
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
            {"message": "Não foi possível atualizar o usuário."},
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

@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Atualizar senha do usuário (com ou sem autenticação)',
    description='Atualiza senha do usuário.',
    request=UserUpdatePasswordSerializer,
    responses={200: None, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(['PUT'])
@permission_classes([AllowAny])
def user_password_update(request):
    serializer = UserUpdatePasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assert isinstance(serializer.validated_data, dict)

    if 'senha_atual' in request.data:
        try:
            auth_header = request.headers.get('Authorization')
            if not user.check_password(serializer.validated_data['senha_atual']):
                return Response(
                    {"message": "Senha atual incompatível."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not auth_header or not auth_header.startswith('Bearer '):
                return Response(
                    {"message": "Autenticação incompatível."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            user = Usuario.objects.get(id_usuario=serializer.validated_data['id'])
            user.set_password(serializer.validated_data['senha_nova'])
            user.save()
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": "Não foi possível atualizar a senha do usuário.",
                "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    try:
        user = Usuario.objects.get(id_usuario=serializer.validated_data['id'])
        user.set_password(serializer.validated_data['senha_nova'])
        user.save()
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        print(e)
        return Response(
            {"message": "Não foi possível atualizar a senha do usuário.",
             "error": str(e)},
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
            {"message": "Não existe nenhum usuário com esse ID."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@extend_schema(
    tags=['Gerenciamento - Admin'],
    summary='Deletar usuário',
    description='Remove o usuário a partir de um id',
    request=None,
    responses={
        200: None,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(['DELETE'])
@permission_classes([IsAdmin])
def user_admin_delete(request, id):
    """
    DELETE /admin/usuarios/<id>/delete
    Admin remove qualquer usuário pelo id.
    """
    # Evita o admin apagar a própria conta por engano
    if getattr(request.user, 'id_usuario', None) == id:
        return Response(
            {"message": "Você não pode apagar o próprio usuário por aqui."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = Usuario.objects.get(id_usuario=id)
    except Usuario.DoesNotExist:
        return Response(
            {"message": "Não existe nenhum usuário com esse ID."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        user.delete()
        return Response(status=status.HTTP_200_OK)
    except Exception:
        logger.exception("Erro ao deletar usuário %s", id)
        return Response(
            {"message": "Não foi possível deletar o usuário."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

@extend_schema(
    tags=['Gerenciamento - Admin'],
    summary='Atualizar usuário',
    description='Atualiza nome, telefone e responsável de um usuário a partir do id',
    request=AdminUserUpdateSerializer,
    responses={
        200: None,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        409: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(['PUT'])
@permission_classes([IsAdmin])
def user_admin_update(request, id):
    """
    PUT /admin/usuarios/<id>/update
    Admin atualiza qualquer usuário.
 
    Regra de contato: usuário COM responsável usa o e-mail do responsável e
    não tem telefone próprio (telefone é único, então dependentes não podem
    repeti-lo). Usuário SEM responsável usa e-mail/telefone próprios.
    """
    serializer = AdminUserUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    data = serializer.validated_data
 
    try:
        user = Usuario.objects.select_related('responsavel').get(id_usuario=id)
    except Usuario.DoesNotExist:
        return Response(
            {"message": "Não existe nenhum usuário com esse ID."},
            status=status.HTTP_404_NOT_FOUND,
        )
 
    was_linked = user.responsavel_id is not None
    responsavel = user.responsavel
    if 'id_responsavel' in data:
        if data['id_responsavel'] is None:
            responsavel = None
        else:
            try:
                responsavel = Responsavel.objects.get(id_responsavel=data['id_responsavel'])
            except Responsavel.DoesNotExist:
                return Response(
                    {"message": "Não existe nenhum responsável com esse id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
 
    if 'nome' in data:
        user.nome = data['nome']
 
    if responsavel:
        user.email = responsavel.email
        user.telefone = None
    else:
        if 'email' in data:
            user.email = data['email'] or None
 
        telefone = (data['telefone'] or None) if 'telefone' in data else user.telefone
 
        if was_linked and not telefone:
            return Response(
                {"message": "Informe um telefone ao remover o responsável."},
                status=status.HTTP_400_BAD_REQUEST,
            )
 
        if telefone and Usuario.objects.filter(telefone=telefone).exclude(
            id_usuario=user.id_usuario
        ).exists():
            return Response(
                {"message": "Já existe um usuário com o telefone requisitado."},
                status=status.HTTP_409_CONFLICT,
            )
        user.telefone = telefone
 
    user.responsavel = responsavel
 
    try:
        with transaction.atomic():
            user.save()
        return Response(status=status.HTTP_200_OK)
    except IntegrityError:
        return Response(
            {"message": "Já existe um usuário com o telefone requisitado."},
            status=status.HTTP_409_CONFLICT,
        )
    except Exception:
        logger.exception("Erro ao atualizar usuário %s", id)
        return Response(
            {"message": "Não foi possível atualizar o usuário."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

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
    tags=['Gerenciamento - Admin'],
    summary='Criar usuário',
    description='Realiza a criação de usuário, opcionalmente vinculado a um responsável',
    request=AdminUserRegisterSerializer,
)
@api_view(['POST'])
@permission_classes([IsAdmin])
def user_admin_register(request):
    """
    POST /admin/usuarios/registrar
    Registra usuário comum (admin). Se houver responsável, o e-mail do
    usuário é o do responsável e o telefone próprio fica vazio.
    """
    serializer = AdminUserRegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
    data = serializer.validated_data
 
    responsavel = None
    id_responsavel = data.get('id_responsavel')
    if id_responsavel:
        try:
            responsavel = Responsavel.objects.get(id_responsavel=id_responsavel)
        except Responsavel.DoesNotExist:
            return Response(
                {"message": "Não existe nenhum responsável com esse id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
 
    if responsavel:
        email = responsavel.email
        telefone = None
    else:
        email = data.get('email') or None
        telefone = data.get('telefone') or None  # '' colidiria com unique=True
 
        if not email or not telefone:
            return Response(
                {"message": "E-mail e telefone são obrigatórios para usuários sem responsável."},
                status=status.HTTP_400_BAD_REQUEST,
            )
 
        if Usuario.objects.filter(telefone=telefone).exists():
            return Response(
                {"message": "Já existe um usuário com o telefone requisitado."},
                status=status.HTTP_409_CONFLICT,
            )
 
    try:
        with transaction.atomic():
            user = Usuario(
                telefone=telefone,
                nome=data['nome'],
                email=email,
                responsavel=responsavel,
            )
            user.set_password(data['senha'])
            user.save()
            user_register_email_confirm(user)  # se falhar, o usuário não é criado
        return Response(status=status.HTTP_200_OK)
    except IntegrityError:
        # Corrida entre o exists() acima e o save()
        return Response(
            {"message": "Já existe um usuário com o telefone requisitado."},
            status=status.HTTP_409_CONFLICT,
        )
    except Exception:
        logger.exception("Erro ao cadastrar usuário")
        return Response(
            {"message": "Erro ao cadastrar usuario."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

def user_register_email_confirm(user: Usuario) -> None:
    token = user.make_token()
    reset_link = f"{settings.FRONTEND_URL}/conta/{user.id_usuario}/{token}"
    subject = settings.EMAIL_SUBJECT_REGISTER_USER
    text_content = settings.EMAIL_TEXT_CONTENT_REGISTER_USER
    html_message = render_to_string('confirm_account_email.html', {'nome': user.nome, 'reset_link': reset_link })
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [user.email])
    msg.attach_alternative(html_message, "text/html")
    msg.send()


class UserListPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema(
    tags=['Gerenciamento - Admin'],
    summary='Listar usuários',
    description='Lista todos os usuários cadastrados, com paginação, busca e filtros opcionais',
    parameters=[
        OpenApiParameter('search', OpenApiTypes.STR, description='Busca por nome, email ou telefone'),
        OpenApiParameter('role', OpenApiTypes.STR, enum=['ROLE_USER', 'ROLE_ADMIN']),
        OpenApiParameter('cadastro_confirmado', OpenApiTypes.BOOL),
        OpenApiParameter('page', OpenApiTypes.INT),
        OpenApiParameter('page_size', OpenApiTypes.INT),
    ],
    responses={200: AdminUserListSerializer(many=True)},
)
@api_view(['GET'])
@permission_classes([IsAdmin])
def user_list(request):
    """
    GET /usuarios
    Lista todos os usuários (ADMIN apenas)
    """
    queryset = Usuario.objects.all().order_by('nome', 'id_usuario')

    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(
            Q(nome__icontains=search) |
            Q(email__icontains=search) |
            Q(telefone__icontains=search)
        )

    role = request.query_params.get('role')
    if role in Role.values:
        queryset = queryset.filter(role=role)

    confirmado = request.query_params.get('cadastro_confirmado')
    if confirmado is not None:
        queryset = queryset.filter(cadastro_confirmado=confirmado.lower() in ('true', '1'))

    paginator = UserListPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = AdminUserListSerializer(page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)