from ..models import Responsavel
from drf_spectacular.utils import extend_schema, OpenApiParameter
from ..serializers import (
    GuardianRequestSerializer, GuardianSerializer
)
from drf_spectacular.types import OpenApiTypes
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from ..permissions import IsAdmin


# ============================================================================
# VIEWS DE RESPONSÁVEIS
# ============================================================================

@extend_schema(
    tags=['Responsáveis'],
    summary='Criar responsável',
    description='Cria um novo responsável no sistema (somente ADMIN)',
    request=GuardianSerializer,
    responses={200: GuardianSerializer, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(['POST'])
@permission_classes([IsAdmin])
def guardian_create(request):
    """
    POST /responsaveis
    Cria novo responsável (ADMIN apenas)
    """
    serializer = GuardianSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assert isinstance(serializer.validated_data, dict)
    
    # Verifica se responsável com mesmo nome já existe
    if Responsavel.objects.filter(nome=serializer.validated_data['nome']).exists():
        return Response(
            {"message": "Responsável ja existe na base de dados."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    try:
        guardian = serializer.save()
        return Response(
            GuardianSerializer(guardian).data,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"message": "Erro ao salvar responsável."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Responsáveis'],
    summary='Listar responsáveis',
    description='Lista todos os responsáveis cadastrados (somente ADMIN)',
    responses={200: GuardianSerializer(many=True), 204: None},
)
@api_view(['GET'])
@permission_classes([IsAdmin])
def guardian_list(request):
    """
    GET /responsaveis
    Lista todos os responsáveis (ADMIN apenas)
    """
    responsaveis = Responsavel.objects.all()
    
    if not responsaveis.exists():
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    serializer = GuardianSerializer(responsaveis, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Responsáveis'],
    summary='Atualizar responsável',
    description='Edita os dados de um responsável existente (somente ADMIN)',
    parameters=[OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    request=GuardianSerializer,
    responses={200: GuardianSerializer, 204: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(['PUT'])
@permission_classes([IsAdmin])
def guardian_update(request, id):
    """
    PUT /responsaveis/{id}
    Edita responsaveis (ADMIN apenas)
    """
    try:
        responsavel = Responsavel.objects.get(id_responsavel=id)
    except Responsavel.DoesNotExist:
        return Response(
            {"message": "Responsável inexistente com esse id na base de dados."},
            status=status.HTTP_204_NO_CONTENT
        )
    
    serializer = GuardianSerializer(responsavel, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        responsavel = serializer.save()
        return Response(
            GuardianSerializer(responsavel).data,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"message": "Erro ao editar responsável."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Responsáveis'],
    summary='Deletar responsável',
    description='Remove um responsável do sistema (somente ADMIN)',
    parameters=[OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    responses={200: None, 500: OpenApiTypes.OBJECT},
)
@api_view(['DELETE'])
@permission_classes([IsAdmin])
def guardian_delete(request, id):
    """
    DELETE /responsaveis/{id}
    Deleta responsável (ADMIN apenas)
    """
    try:
        responsavel = Responsavel.objects.get(id_responsavel=id)
        responsavel.delete()
        return Response(status=status.HTTP_200_OK)
    except Responsavel.DoesNotExist:
        return Response(
            {"message": "Responsável inexistente com esse id na base de dados."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"message": "Erro ao deletar Responsável."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Responsáveis'],
    summary='Buscar responsável por nome',
    description='Busca um responsável pelo nome completo',
    request=GuardianRequestSerializer,
    responses={200: GuardianSerializer, 204: None},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def guardian_search_by_name(request):
    """
    POST /responsaveis/pesquisar
    Busca responsável por nome (público)
    """
    serializer = GuardianRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assert isinstance(serializer.validated_data, dict)

    try:
        responsavel = Responsavel.objects.get(nome=serializer.validated_data['nome'])
        return Response(
            GuardianSerializer(responsavel).data,
            status=status.HTTP_200_OK
        )
    except Responsavel.DoesNotExist:
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=['Responsáveis'],
    summary='Buscar responsável por ID',
    description='Busca um responsável pelo seu identificador',
    parameters=[OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH)],
    responses={200: GuardianSerializer, 204: None},
)
@api_view(['GET'])
@permission_classes([AllowAny])
def guardian_search_by_id(request, id):
    """
    GET /responsaveis/pesquisar/{id}
    Busca responsável por ID (público)
    """
    try:
        responsavel = Responsavel.objects.get(id_responsavel=id)
    except Responsavel.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    return Response(
        GuardianSerializer(responsavel).data,
        status=status.HTTP_200_OK
    )