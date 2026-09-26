from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from ..permissions import IsAdminOrUser
from ..serializers.appointment import AppointmentRequestSerializer, AppointmentSerializer
from ..models import Usuario, Agendamento
from .utils import convert_to_iso
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from ..permissions import IsAdmin, IsAdminOrUser, IsUser

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
    assert isinstance(serializer.validated_data, dict)
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
    assert isinstance(serializer.validated_data, dict)
    
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
        agendamento.usuario = user
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