"""
Fixtures compartilhadas para testes pytest
"""

import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from .models import Usuario, Paciente, Agendamento, Notificacao, Role
import jwt
from django.conf import settings


@pytest.fixture
def api_client():
    """Cliente de API para testes"""
    return APIClient()


@pytest.fixture
def paciente():
    """Fixture de paciente padrão"""
    return Paciente.objects.create(nome="Paciente Teste")


@pytest.fixture
def paciente2():
    """Fixture de segundo paciente"""
    return Paciente.objects.create(nome="Paciente Dois")


@pytest.fixture
def user(paciente):
    """Fixture de usuário comum"""
    user = Usuario.objects.create(
        nome="User Test",
        email="user@test.com",
        role=Role.USER,
        id_paciente=paciente.id_paciente,
        cadastro_confirmado=True
    )
    user.set_password("senha123")
    user.save()
    return user


@pytest.fixture
def user_not_confirmed(paciente):
    """Fixture de usuário não confirmado"""
    user = Usuario.objects.create(
        nome="User Not Confirmed",
        email="notconfirmed@test.com",
        role=Role.USER,
        id_paciente=paciente.id_paciente,
        cadastro_confirmado=False
    )
    user.set_password("senha123")
    user.save()
    return user


@pytest.fixture
def admin():
    """Fixture de administrador"""
    admin = Usuario.objects.create(
        nome="Admin Test",
        email="admin@test.com",
        role=Role.ADMIN,
        cadastro_confirmado=True
    )
    admin.set_password("admin123")
    admin.save()
    return admin


@pytest.fixture
def user_token(user):
    """Fixture de token JWT para usuário comum"""
    payload = {
        'sub': user.email,
        'iss': settings.SECURITY_EMISSOR,
        'idUsuario': user.id_usuario,
        'idPaciente': user.id_paciente,
        'role': user.role,
        'iat': timezone.now(),
        'exp': timezone.now() + timedelta(hours=24)
    }
    token = jwt.encode(payload, settings.SECURITY_TOKEN, algorithm='HS256')
    return token


@pytest.fixture
def admin_token(admin):
    """Fixture de token JWT para administrador"""
    payload = {
        'sub': admin.email,
        'iss': settings.SECURITY_EMISSOR,
        'idUsuario': admin.id_usuario,
        'idPaciente': admin.id_paciente,
        'role': admin.role,
        'iat': timezone.now(),
        'exp': timezone.now() + timedelta(hours=24)
    }
    token = jwt.encode(payload, settings.SECURITY_TOKEN, algorithm='HS256')
    return token


@pytest.fixture
def agendamento(paciente):
    """Fixture de agendamento"""
    return Agendamento.objects.create(
        titulo="Consulta de rotina",
        descricao="Consulta médica mensal",
        data=timezone.now() + timedelta(days=7),
        local="Hospital GRAACC - Sala 101",
        paciente=paciente
    )


@pytest.fixture
def agendamento_futuro(paciente):
    """Fixture de agendamento futuro"""
    return Agendamento.objects.create(
        titulo="Exame de sangue",
        descricao="Coleta de sangue para análise",
        data=timezone.now() + timedelta(days=14),
        local="Laboratório",
        paciente=paciente
    )


@pytest.fixture
def notificacao(agendamento):
    """Fixture de notificação"""
    return Notificacao.objects.create(
        id_agendamento=agendamento.id_agendamento,
        data=timezone.now() + timedelta(days=3),
        lida=False
    )


@pytest.fixture
def notificacao_lida(agendamento):
    """Fixture de notificação já lida"""
    return Notificacao.objects.create(
        id_agendamento=agendamento.id_agendamento,
        data=timezone.now() + timedelta(days=1),
        lida=True
    )


@pytest.fixture
def authenticated_client(api_client, user_token):
    """Cliente autenticado como usuário comum"""
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {user_token}')
    return api_client


@pytest.fixture
def admin_client(api_client, admin_token):
    """Cliente autenticado como administrador"""
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
    return api_client
