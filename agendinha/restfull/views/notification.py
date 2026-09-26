
from ..models import Notificacao, Usuario
from drf_spectacular.utils import extend_schema, OpenApiParameter
from ..permissions import IsAdmin, IsAdminOrUser
from ..serializers.appointment import AppointmentInfoSerializer
from ..serializers.notification import NotificationSerializer
from drf_spectacular.types import OpenApiTypes
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from datetime import datetime, timedelta
from django.utils import timezone
from .subscription import send_push

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
    assert isinstance(serializer.validated_data, dict)
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
    assert isinstance(serializer.validated_data, dict)
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
    assert isinstance(serializer.validated_data, dict)

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