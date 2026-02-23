"""
Views para GRAACC API Unificada
Migradas dos Controllers dos microserviços Java Spring Boot
"""
from google.oauth2 import id_token
from google.auth.transport import requests
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

from .models import Usuario, Paciente, Agendamento, Notificacao, Role
from .serializers import (
    UserRegisterSerializer, UserRegisterWithPatientIdSerializer,
    UserLoginSerializer, UserLoginResponseSerializer, UserUpdateSerializer,
    AdminRegisterSerializer, UserSerializer,
    PatientSerializer, PatientRequestSerializer,
    AppointmentRequestSerializer, AppointmentSerializer,
    AppointmentInfoSerializer, NotificationSerializer,
    UserUpdatePasswordSerializer, UserGoogleLoginSerializer
)
from .permissions import IsAdmin, IsUser, IsAdminOrUser


# ============================================================================
# UTILIDADES JWT
# ============================================================================

def generate_custom_jwt(user):
    """
    Gera JWT customizado compatível com os microserviços Java
    Claims: idUsuario, idPaciente, email, role
    """
    payload = {
        'sub': user.email,
        'iss': settings.SECURITY_EMISSOR,
        'idUsuario': user.id_usuario,
        'idPaciente': user.id_paciente,
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
    description='Registra um novo usuário comum associado a um paciente existente pelo nome',
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
                'nome_completo_paciente': 'Maria Silva'
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
    Registra usuário comum associado a um paciente
    Migrado de: UserController.addUser()
    """
    serializer = UserRegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Busca paciente pelo nome
    try:
        paciente = Paciente.objects.get(nome=serializer.validated_data['nome_completo_paciente'])
    except Paciente.DoesNotExist:
        return Response(
            {"message": "Não existe nenhum paciente com esse nome"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
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
            id_paciente=paciente.id_paciente,
            cadastro_confirmado=False
        )
        user.set_password(serializer.validated_data['senha'])
        user.save()
        
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"message": "Erro ao inserir usuario."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Registrar usuário com ID do paciente',
    description='Registra um novo usuário comum associado a um paciente pelo ID',
    request=UserRegisterWithPatientIdSerializer,
    responses={200: None, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def user_register_with_patient_id(request):
    """
    POST /usuarios/pacienteid/registrar
    Registra usuário com ID do paciente direto
    Migrado de: UserController.addUserWithPatientId()
    """
    serializer = UserRegisterWithPatientIdSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Verifica se paciente existe
    try:
        paciente = Paciente.objects.get(id_paciente=serializer.validated_data['id_paciente'])
    except Paciente.DoesNotExist:
        return Response(
            {"message": "Não existe nenhum paciente com esse id"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
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
            id_paciente=paciente.id_paciente,
            cadastro_confirmado=False
        )
        user.set_password(serializer.validated_data['senha'])
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
    
    try:
        user = Usuario.objects.get(email=serializer.validated_data['email'])
    except Usuario.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    
    # Verifica senha
    if not user.check_password(serializer.validated_data['senha']):
        return Response(status=status.HTTP_400_BAD_REQUEST)
    
    if user.modo_google:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    # Gera token JWT customizado
    token = generate_custom_jwt(user)
    
    response_data = {
        'nome': user.nome,
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

        if created:
            user.nome = f"{first_name} {last_name}"
            user.modo_google = True
            user.save()
        else:
            if not user.modo_google:
                return Response({
                    "error": "Usuário precisa logar via e-mail.",
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Gera token JWT customizado
        token = generate_custom_jwt(user)
        
        response_data = {
            'nome': user.nome,
            'token': token,
            'cadastro_confirmado': user.cadastro_confirmado
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

    except ValueError:
        return Response(status=status.HTTP_400_BAD_REQUEST)    



@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Confirmar cadastro',
    description='Confirma o cadastro do usuário autenticado',
    request=None,
    responses={200: None},
)
@api_view(['POST'])
@permission_classes([IsAdminOrUser])
def user_confirm(request):
    """
    POST /usuarios/confirmar
    Confirma cadastro do usuário autenticado
    Migrado de: UserController.confirmUser()
    """
    user_info = request.user
    user = Usuario.objects.get(id_usuario=user_info.id_usuario)
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
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Autenticação - Usuários'],
    summary='Atualizar dados do usuário',
    description='Atualiza nome, email ou paciente associado do usuário autenticado',
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
            
            # Atualiza paciente se fornecido
            if serializer.validated_data.get('nome_completo_paciente'):
                try:
                    paciente = Paciente.objects.get(nome=serializer.validated_data['nome_completo_paciente'])
                    user.id_paciente = paciente.id_paciente
                except Paciente.DoesNotExist:
                    return Response(
                        {"message": "Não existe nenhum paciente com esse nome"},
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
            id_paciente=None,
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
# VIEWS DE PACIENTES
# ============================================================================

@extend_schema(
    tags=['Pacientes'],
    summary='Criar paciente',
    description='Cria um novo paciente no sistema (somente ADMIN)',
    request=PatientSerializer,
    responses={200: PatientSerializer, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(['POST'])
@permission_classes([IsAdmin])
def patient_create(request):
    """
    POST /pacientes
    Cria novo paciente (ADMIN apenas)
    Migrado de: PatientController.addPatient()
    """
    serializer = PatientSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Verifica se paciente com mesmo nome já existe
    if Paciente.objects.filter(nome=serializer.validated_data['nome']).exists():
        return Response(
            {"message": "Paciente ja existe na base de dados."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    try:
        paciente = serializer.save()
        return Response(
            PatientSerializer(paciente).data,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"message": "Erro ao salvar paciente."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Pacientes'],
    summary='Listar pacientes',
    description='Lista todos os pacientes cadastrados (somente ADMIN)',
    responses={200: PatientSerializer(many=True), 204: None},
)
@api_view(['GET'])
@permission_classes([IsAdmin])
def patient_list(request):
    """
    GET /pacientes
    Lista todos os pacientes (ADMIN apenas)
    Migrado de: PatientController.findAll()
    """
    pacientes = Paciente.objects.all()
    
    if not pacientes.exists():
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    serializer = PatientSerializer(pacientes, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Pacientes'],
    summary='Atualizar paciente',
    description='Edita os dados de um paciente existente (somente ADMIN)',
    parameters=[OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    request=PatientSerializer,
    responses={200: PatientSerializer, 204: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(['PUT'])
@permission_classes([IsAdmin])
def patient_update(request, id):
    """
    PUT /pacientes/{id}
    Edita paciente (ADMIN apenas)
    Migrado de: PatientController.editPatient()
    """
    try:
        paciente = Paciente.objects.get(id_paciente=id)
    except Paciente.DoesNotExist:
        return Response(
            {"message": "Paciente inexistente com esse id na base de dados."},
            status=status.HTTP_204_NO_CONTENT
        )
    
    serializer = PatientSerializer(paciente, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        paciente = serializer.save()
        return Response(
            PatientSerializer(paciente).data,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"message": "Erro ao editar paciente."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Pacientes'],
    summary='Deletar paciente',
    description='Remove um paciente do sistema (somente ADMIN)',
    parameters=[OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    responses={200: None, 500: OpenApiTypes.OBJECT},
)
@api_view(['DELETE'])
@permission_classes([IsAdmin])
def patient_delete(request, id):
    """
    DELETE /pacientes/{id}
    Deleta paciente (ADMIN apenas)
    Migrado de: PatientController.deletePatient()
    """
    try:
        paciente = Paciente.objects.get(id_paciente=id)
        paciente.delete()
        return Response(status=status.HTTP_200_OK)
    except Paciente.DoesNotExist:
        return Response(
            {"message": "Paciente inexistente com esse id na base de dados."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"message": "Erro ao deletar Paciente."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Pacientes'],
    summary='Buscar paciente por nome',
    description='Busca um paciente pelo nome completo',
    request=PatientRequestSerializer,
    responses={200: PatientSerializer, 204: None},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def patient_search_by_name(request):
    """
    POST /pacientes/pesquisar
    Busca paciente por nome (público)
    Migrado de: PatientController.findPatientByName()
    """
    serializer = PatientRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        paciente = Paciente.objects.get(nome=serializer.validated_data['nome'])
        return Response(
            PatientSerializer(paciente).data,
            status=status.HTTP_200_OK
        )
    except Paciente.DoesNotExist:
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=['Pacientes'],
    summary='Buscar paciente por ID',
    description='Busca um paciente pelo seu identificador',
    parameters=[OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    responses={200: PatientSerializer, 204: None},
)
@api_view(['GET'])
@permission_classes([AllowAny])
def patient_search_by_id(request, id):
    """
    GET /pacientes/pesquisar/{id}
    Busca paciente por ID (público)
    Migrado de: PatientController.findPatientById()
    """
    try:
        paciente = Paciente.objects.get(id_paciente=id)
        return Response(
            PatientSerializer(paciente).data,
            status=status.HTTP_200_OK
        )
    except Paciente.DoesNotExist:
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================================
# VIEWS DE AGENDAMENTOS
# ============================================================================

@extend_schema(
    tags=['Agendamentos'],
    summary='Criar agendamento',
    description='Cria um novo agendamento para um paciente (somente ADMIN)',
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
    
    # Busca paciente pelo nome
    try:
        paciente = Paciente.objects.get(nome=serializer.validated_data['nome_completo_paciente'])
    except Paciente.DoesNotExist:
        return Response(
            {"message": "Erro ao inserir Agendamento - Paciente nao encontrado."},
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
            paciente=paciente
        )
        agendamento.save()
        
        return Response(
            AppointmentSerializer(agendamento).data,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"message": "Erro ao inserir Agendamento."},
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
    
    # Busca paciente pelo nome
    try:
        paciente = Paciente.objects.get(nome=serializer.validated_data['nome_completo_paciente'])
    except Paciente.DoesNotExist:
        return Response(
            {"message": "Erro ao editar Agendamento - Paciente nao encontrado."},
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
        agendamento.paciente = paciente
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
    description='Lista os agendamentos do paciente associado ao usuário autenticado',
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
    
    # Busca agendamentos do paciente associado ao usuário
    agendamentos = Agendamento.objects.filter(paciente__id_paciente=user_info.id_paciente)
    
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
    
    # Cria notificações
    notifications = []
    for data in future_dates:
        notificacao = Notificacao(
            id_agendamento=serializer.validated_data['id_agendamento'],
            data=data,
            lida=False
        )
        notificacao.save()
        notifications.append(notificacao)
    
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
    return Response("Hello World from GRAACC API Unificada", status=status.HTTP_200_OK)
