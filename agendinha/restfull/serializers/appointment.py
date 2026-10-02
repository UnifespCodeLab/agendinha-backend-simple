from rest_framework import serializers
from ..models import Agendamento
from datetime import datetime
from django.utils.timezone import localtime

# ============================================================================
# SERIALIZERS DE AGENDAMENTOS
# ============================================================================

class AppointmentRequestSerializer(serializers.Serializer):
    """
    Serializer para criação/edição de agendamento
    Migrado de: AppointmentRequestDTO
    """
    titulo = serializers.CharField(max_length=100)
    descricao = serializers.CharField(max_length=255, required=False, allow_blank=True)
    data = serializers.CharField()  # Formato: "dd/MM/yyyy HH:mm"
    local = serializers.CharField(max_length=100)
    medico = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    id_usuario = serializers.IntegerField()

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
    id_paciente = serializers.IntegerField(source='usuario.id_usuario', read_only=True)
    nome_paciente = serializers.CharField(source='usuario.nome', read_only=True)
    data = serializers.SerializerMethodField()

    class Meta:
        model = Agendamento
        fields = ['id_agendamento', 'titulo', 'descricao', 'data', 'local', 'medico', 'id_paciente', 'nome_paciente', 'lembrete_enviado']
        read_only_fields = ['id_agendamento', 'id_paciente', 'nome_paciente', 'lembrete_enviado']

    def get_data(self, obj):
        if obj.data:
            return localtime(obj.data).strftime('%d/%m/%Y %H:%M')
        return None

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