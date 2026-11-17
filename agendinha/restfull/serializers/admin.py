from rest_framework import serializers
from ..models import Usuario
from .guardian import GuardianSerializer

class AdminUserRegisterSerializer(serializers.Serializer):
    telefone = serializers.CharField(max_length=14)
    nome = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    senha = serializers.CharField(write_only=True, style={'input_type': 'password'})
    id_responsavel = serializers.IntegerField(required=False, allow_null=True)

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
    responsavel = GuardianSerializer(read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id_usuario',
            'nome',
            'email',
            'telefone',
            'cadastro_confirmado',
            'modo_google',
            'role',
            'responsavel',
            'ativar_notificacoes_consultas',
            'foto_perfil',
        ]
        read_only_fields = fields

class AdminUserUpdateSerializer(serializers.Serializer):
    nome = serializers.CharField(required=False, min_length=2, max_length=255)
    telefone = serializers.CharField(max_length=14, required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    id_responsavel = serializers.IntegerField(required=False, allow_null=True)