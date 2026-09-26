from rest_framework import serializers
from ..models import Usuario

# ============================================================================
# SERIALIZERS DE USUÁRIOS
# ============================================================================

class UserRegisterSerializer(serializers.Serializer):
    """
    Serializer para registro de usuário comum
    Migrado de: UserRegisterRequestDTO
    """
    cpf = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True, style={'input_type': 'password'})

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
    id = serializers.IntegerField()
    senha_atual = serializers.CharField(
        required=False, 
        allow_null=True, 
        allow_blank=True, 
        write_only=True, 
        style={'input_type': 'password'}
    )
    senha_nova = serializers.CharField(write_only=True, style={'input_type': 'password'})

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer completo de usuário
    Migrado de: UserDTO
    """
    id_usuario = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Usuario
        fields = [
            'id_usuario', 
            'nome', 
            'email', 
            'cadastro_confirmado', 
            'role', 
            'responsavel', 
            'foto_perfil', 
            'ativar_notificacoes_consultas',
        ]
        read_only_fields = ['id_usuario', 'cadastro_confirmado', 'role', 'responsavel']