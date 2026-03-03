"""
Serializers para GRAACC API Unificada
Migrados dos DTOs dos microserviços Java Spring Boot
"""

from rest_framework import serializers
from .models import Usuario, Paciente, Agendamento, Notificacao
from datetime import datetime


# ============================================================================
# SERIALIZERS DE USUÁRIOS
# ============================================================================

class UserRegisterSerializer(serializers.Serializer):
    """
    Serializer para registro de usuário comum
    Migrado de: UserRegisterRequestDTO
    """
    nome = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True, style={'input_type': 'password'})
    nome_completo_paciente = serializers.CharField(max_length=255)


class UserRegisterWithPatientIdSerializer(serializers.Serializer):
    """
    Serializer para registro de usuário com ID do paciente
    Migrado de: UserRegisterWithPatientIdRequestDTO
    """
    nome = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True, style={'input_type': 'password'})
    id_paciente = serializers.IntegerField()


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer para login
    Migrado de: UserLoginRequestDTO
    """
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True, style={'input_type': 'password'})

class UserGoogleLoginSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)
    email = serializers.EmailField()

class UserLoginResponseSerializer(serializers.Serializer):
    """
    Serializer para resposta de login
    Migrado de: UserLoginResponseDTO
    """
    nome = serializers.CharField()
    token = serializers.CharField()

class UserRequestNewPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class UserUpdateSerializer(serializers.Serializer):
    """
    Serializer para atualização de usuário
    Migrado de: UserUpdateRequestDTO
    """
    nome = serializers.CharField(max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    nome_completo_paciente = serializers.CharField(max_length=255, required=False, allow_blank=True)

class UserUpdatePasswordSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    senha_atual = serializers.CharField(write_only=True, style={'input_type': 'password'})
    senha_nova = serializers.CharField(write_only=True, style={'input_type': 'password'})

class AdminRegisterSerializer(serializers.Serializer):
    """
    Serializer para registro de admin
    Migrado de: AdminRegisterRequestDTO
    """
    nome = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True, style={'input_type': 'password'})


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer completo de usuário
    Migrado de: UserDTO
    """
    id_usuario = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nome', 'email', 'cadastro_confirmado', 'role', 'id_paciente', 'foto_perfil']
        read_only_fields = ['id_usuario', 'cadastro_confirmado', 'role', 'id_paciente']


# ============================================================================
# SERIALIZERS DE PACIENTES
# ============================================================================

class PatientRequestSerializer(serializers.Serializer):
    """
    Serializer para busca de paciente por nome
    Migrado de: PatientRequestDTO (record)
    """
    nome = serializers.CharField(max_length=255)


class PatientSerializer(serializers.ModelSerializer):
    """
    Serializer de paciente
    Migrado de: PatientResponseDTO
    """
    id_paciente = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Paciente
        fields = ['id_paciente', 'nome', 'telefone']
        read_only_fields = ['id_paciente']


# ============================================================================
# SERIALIZERS DE AGENDAMENTOS
# ============================================================================

class AppointmentRequestSerializer(serializers.Serializer):
    """
    Serializer para criação/edição de agendamento
    Migrado de: AppointmentRequestDTO
    """
    titulo = serializers.CharField(max_length=100)
    descricao = serializers.CharField(max_length=255)
    data = serializers.CharField()  # Formato: "dd/MM/yyyy HH:mm"
    local = serializers.CharField(max_length=100)
    medico = serializers.CharField(max_length=255, required=False, allow_blank=True)
    id_paciente = serializers.IntegerField(read_only=True)

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
    id_agendamento = serializers.IntegerField(read_only=True)
    data = serializers.SerializerMethodField()
    id_paciente = serializers.IntegerField(source='paciente.id_paciente', read_only=True)
    
    class Meta:
        model = Agendamento
        fields = ['id_agendamento', 'titulo', 'descricao', 'data', 'local', 'medico', 'id_paciente', 'lembrete_enviado']
        read_only_fields = ['id_agendamento', 'id_paciente', 'lembrete_enviado']

    def get_data(self, obj):
        """Formata data no formato dd/MM/yyyy HH:mm"""
        return obj.data.strftime('%d/%m/%Y %H:%M')


# ============================================================================
# SERIALIZERS DE NOTIFICAÇÕES
# ============================================================================

class AppointmentInfoSerializer(serializers.Serializer):
    """
    Serializer para informação de agendamento
    Migrado de: AppointmentInfoDTO
    """
    id_agendamento = serializers.IntegerField()
    data_agendamento = serializers.CharField()  # Formato: "dd/MM/yyyy HH:mm"

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


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer de notificação
    Migrado de: NotificationDTO
    """
    id_notificacao = serializers.IntegerField(read_only=True)
    data = serializers.SerializerMethodField()
    
    class Meta:
        model = Notificacao
        fields = ['id_notificacao', 'data', 'lida', 'id_agendamento']
        read_only_fields = ['id_notificacao']

    def get_data(self, obj):
        """Formata data no formato dd/MM/yyyy HH:mm"""
        return obj.data.strftime('%d/%m/%Y %H:%M')
