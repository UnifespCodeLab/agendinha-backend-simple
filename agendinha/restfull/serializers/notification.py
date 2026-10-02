from rest_framework import serializers
from ..models import Notificacao
from django.utils.timezone import localtime

# ============================================================================
# SERIALIZERS DE NOTIFICAÇÕES
# ============================================================================

class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer de notificação
    Migrado de: NotificationDTO
    """

    class Meta:
        model = Notificacao
        fields = ['id_notificacao', 'data', 'lida', 'id_agendamento', 'usuario', 'titulo', 'descricao']
        read_only_fields = ['id_notificacao']

    def get_data(self, obj):
        if obj.data:
            return localtime(obj.data).strftime('%d/%m/%Y %H:%M')
        return None
