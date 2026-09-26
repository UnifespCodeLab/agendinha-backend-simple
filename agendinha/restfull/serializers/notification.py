from rest_framework import serializers
from ..models import Notificacao

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
        """Formata data no formato dd/MM/yyyy HH:mm"""
        return obj.data.strftime('%d/%m/%Y %H:%M')
