from rest_framework import serializers
from ..models import Agendamento
from datetime import datetime

# ============================================================================
# SERIALIZERS DE AGENDAMENTOS
# ============================================================================

class AppointmentRequestSerializer(serializers.Serializer):
    """
    Serializer para criação/edição de agendamento
    Migrado de: AppointmentRequestDTO
    """
    class Meta:
        model = Agendamento
        fields = [
            'titulo',
            'descricao',
            'data',
            'local',
            'medico',
            'id_usuario',
        ]

        extra_kwargs = {
            'data': {
                'format': '%d/%m/%Y %H:%M',
            }
        }

    def validate_data(self, value):
        """
        Valida formato de data dd/MM/yyyy HH:mm
        """
        try:
            datetime.strptime(value, '%d/%m/%Y %H:%M')
            return value
        except ValueError:
            raise serializers.ValidationError(
                "Formato de data inválido. Use dd/MM/yyyy HH:mm"
            )


class AppointmentSerializer(serializers.ModelSerializer):
    """
    Serializer de agendamento
    Migrado de: AppointmentResponseDTO
    """   
    class Meta:
        model = Agendamento
        fields = ['id_agendamento', 'titulo', 'descricao', 'data', 'local', 'medico', 'lembrete_enviado']
        read_only_fields = ['id_agendamento', 'lembrete_enviado']

    def get_data(self, obj):
        """Formata data no formato dd/MM/yyyy HH:mm"""
        return obj.data.strftime('%d/%m/%Y %H:%M')

class AppointmentInfoSerializer(serializers.Serializer):
    """
    Serializer para informação de agendamento
    Migrado de: AppointmentInfoDTO
    """
    id_agendamento = serializers.IntegerField()
    data_agendamento = serializers.CharField()  # Formato: "dd/MM/yyyy HH:mm"
    id_usuario = serializers.IntegerField(source='usuario.id_usuario', read_only=True)
    descricao = serializers.CharField(max_length=100)
    titulo = serializers.CharField(max_length=100)

    def validate_data_agendamento(self, value):
        """
        Valida formato de data dd/MM/yyyy HH:mm
        """
        try:
            datetime.strptime(value, '%d/%m/%Y %H:%M')
            return value
        except ValueError:
            raise serializers.ValidationError(
                "Formato de data inválido. Use dd/MM/yyyy HH:mm"
            )