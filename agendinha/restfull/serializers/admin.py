from rest_framework import serializers
from ..models import Usuario

class AdminUserRegisterSerializer(serializers.Serializer):
    cpf = serializers.CharField(max_length=14)
    nome = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True, style={'input_type': 'password'})

class AdminRegisterSerializer(serializers.Serializer):
    """
    Serializer para registro de admin
    Migrado de: AdminRegisterRequestDTO
    """
    nome = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True, style={'input_type': 'password'})

class AdminLoginResponseSerializer(serializers.Serializer):
    nome = serializers.CharField()
    token = serializers.CharField()

class AdminUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            'id_usuario',
            'nome',
            'email',
            'cpf',
            'role',
            'cadastro_confirmado',
            'modo_google',
            'ativar_notificacoes_consultas',
            'foto_perfil',
        ]
        read_only_fields = fields