from ..permissions import IsAdminOrUser
from ..serializers.appointment import AppointmentRequestSerializer, AppointmentSerializer
from ..models import Usuario, Agendamento, Notificacao
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from django.utils.timezone import make_aware, now
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from ..permissions import IsAdmin, IsAdminOrUser, IsUser
import logging
import requests
from .utils import (
    exchange_google_code, 
    GoogleAuthError, 
    refresh_google_access_token,
    GoogleUnavailableError,
    GOOGLE_EVENTS_URL,
    EVENT_FIELDS
)

logger = logging.getLogger(__name__)
 
# ============================================================================
# VIEWS DE AGENDAMENTOS
# ============================================================================
 
@extend_schema(
    tags=['Agendamentos'],
    summary='Exportar agendamento para o Google Agenda',
    description='Cria o evento na agenda principal do usuário, usando o refresh token guardado',
    request=None,
)
@api_view(['POST'])
@permission_classes([IsAdminOrUser])
def appointment_export_task_to_google_calendar(request):
    event = {k: v for k, v in request.data.items() if k in EVENT_FIELDS}
    if not event.get("summary") or not event.get("start") or not event.get("end"):
        return Response(
            {"message": "Evento inválido: informe título, início e fim."},
            status=status.HTTP_400_BAD_REQUEST,
        )
 
    user = Usuario.objects.get(id_usuario=request.user.id_usuario) 
    code = request.data.get("code")
 
    try:
        if code:
            tokens = exchange_google_code(code)
            access_token = tokens["access_token"]
        else:
            access_token = refresh_google_access_token(user)
    except GoogleAuthError:
        return Response(
            {"message": "Autorização do Google expirada. Entre novamente com o Google."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    except GoogleUnavailableError:
        logger.exception("Google indisponível ao renovar o token")
        return Response(
            {"message": "Não foi possível falar com o Google. Tente novamente."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
 
    try:
        resp = requests.post(
            GOOGLE_EVENTS_URL,
            json=event,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
    except requests.RequestException:
        logger.exception("Falha ao chamar o Google Calendar")
        return Response(
            {"message": "Não foi possível falar com o Google Agenda."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
 
    if resp.status_code in (200, 201):
        return Response(status=status.HTTP_200_OK)
 
    logger.error("Google Calendar respondeu %s: %s", resp.status_code, resp.text)
    if resp.status_code in (401, 403):
        # 403 costuma ser escopo de calendário não concedido
        return Response(
            {"message": "Sem permissão no Google Agenda. Entre novamente com o Google."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    return Response(
        {"message": "O Google Agenda recusou o evento."},
        status=status.HTTP_502_BAD_GATEWAY,
    )

@extend_schema(
    tags=['Agendamentos'],
    summary='Criar agendamento',
    description='Cria um novo agendamento para um usuário (somente ADMIN)',
    request=AppointmentRequestSerializer,
    responses={200: AppointmentSerializer, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(['POST'])
@permission_classes([IsAdmin])
@transaction.atomic
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
        data_agendamento = make_aware(datetime.strptime(
            serializer.validated_data['data'],
            '%d/%m/%Y %H:%M'
        ))
    except ValueError:
        return Response(
            {"message": "Erro ao converter Data do Agendamento - tente novamento no formato dd/MM/yyyy HH:mm"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Cria agendamento
    try:
        data = serializer.validated_data
        agendamento = Agendamento(
            titulo=data['titulo'],
            descricao=data.get('descricao', ''),
            data=data_agendamento,
            local=data['local'],
            usuario=user,
            medico=data.get('medico', '')
        )
        agendamento.save()

        notification = Notificacao(
            agendamento=agendamento,
            lida=False,
            usuario=user,
            data=now(),
            titulo=data['titulo'],
            descricao=f"{data.get('descricao', '')} {data_agendamento}",
        )
        notification.save()
        
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
        data_agendamento = make_aware(datetime.strptime(
            serializer.validated_data['data'],
            '%d/%m/%Y %H:%M'
        ))
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
        agendamento.medico = serializer.validated_data['medico']
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