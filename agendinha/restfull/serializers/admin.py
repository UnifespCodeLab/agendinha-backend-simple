from rest_framework import serializers

class AdminUserRegisterSerializer(serializers.Serializer):
    cpf = serializers.CharField(max_length=14)
    nome = serializers.CharField(max_length=255)

class AdminRegisterSerializer(serializers.Serializer):
    """
    Serializer para registro de admin
    Migrado de: AdminRegisterRequestDTO
    """
    nome = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True, style={'input_type': 'password'})