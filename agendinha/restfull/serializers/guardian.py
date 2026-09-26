from rest_framework import serializers
from ..models import Responsavel

class GuardianSerializer(serializers.ModelSerializer):
    id_responsavel = serializers.IntegerField(read_only=True)
    nome = serializers.CharField(max_length=255)

    class Meta:
        model = Responsavel
        fields = ['id_responsavel', 'nome']
        read_only_fields = ['id_responsavel']

class GuardianRequestSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=255)