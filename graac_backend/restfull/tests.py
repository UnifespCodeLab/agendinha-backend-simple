"""
Testes Unitários para GRAACC API Unificada
Cobertura completa de models, serializers e views
"""

import pytest
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Usuario, Paciente, Agendamento, Notificacao, Role
from .serializers import (
    UserRegisterSerializer, UserLoginSerializer, UserUpdateSerializer,
    PatientSerializer, AppointmentRequestSerializer, NotificationSerializer
)
import jwt
from django.conf import settings


# ============================================================================
# TESTES DE MODELS
# ============================================================================

class UsuarioModelTest(TestCase):
    """Testes para o model Usuario"""
    
    def setUp(self):
        self.paciente = Paciente.objects.create(nome="Paciente Teste")
        
    def test_create_user(self):
        """Testa criação de usuário comum"""
        user = Usuario.objects.create(
            nome="João Silva",
            email="joao@email.com",
            role=Role.USER,
            id_paciente=self.paciente.id_paciente,
            cadastro_confirmado=False
        )
        user.set_password("senha123")
        user.save()
        
        self.assertEqual(user.nome, "João Silva")
        self.assertEqual(user.email, "joao@email.com")
        self.assertEqual(user.role, Role.USER)
        self.assertFalse(user.cadastro_confirmado)
        self.assertIsNotNone(user.senha)
        
    def test_create_admin(self):
        """Testa criação de administrador"""
        admin = Usuario.objects.create(
            nome="Admin User",
            email="admin@email.com",
            role=Role.ADMIN,
            cadastro_confirmado=True
        )
        admin.set_password("admin123")
        admin.save()
        
        self.assertEqual(admin.role, Role.ADMIN)
        self.assertIsNone(admin.id_paciente)
        
    def test_password_hashing(self):
        """Testa criptografia de senha com bcrypt"""
        user = Usuario.objects.create(
            nome="Test User",
            email="test@email.com",
            role=Role.USER
        )
        raw_password = "senha123"
        user.set_password(raw_password)
        
        # Senha deve ser hasheada
        self.assertNotEqual(user.senha, raw_password)
        # Deve verificar corretamente
        self.assertTrue(user.check_password(raw_password))
        # Senha errada deve falhar
        self.assertFalse(user.check_password("senhaerrada"))
        
    def test_user_str_method(self):
        """Testa representação string do usuário"""
        user = Usuario.objects.create(
            nome="Test User",
            email="test@email.com"
        )
        self.assertEqual(str(user), "Test User (test@email.com)")
        
    def test_unique_email_constraint(self):
        """Testa constraint de email único"""
        Usuario.objects.create(nome="User 1", email="same@email.com")
        
        with self.assertRaises(Exception):
            Usuario.objects.create(nome="User 2", email="same@email.com")


class PacienteModelTest(TestCase):
    """Testes para o model Paciente"""
    
    def test_create_paciente(self):
        """Testa criação de paciente"""
        paciente = Paciente.objects.create(nome="Maria Silva")
        
        self.assertEqual(paciente.nome, "Maria Silva")
        self.assertIsNotNone(paciente.id_paciente)
        
    def test_paciente_str_method(self):
        """Testa representação string do paciente"""
        paciente = Paciente.objects.create(nome="João Santos")
        self.assertEqual(str(paciente), "João Santos")
        
    def test_unique_nome_constraint(self):
        """Testa constraint de nome único"""
        Paciente.objects.create(nome="Mesmo Nome")
        
        with self.assertRaises(Exception):
            Paciente.objects.create(nome="Mesmo Nome")


class AgendamentoModelTest(TestCase):
    """Testes para o model Agendamento"""
    
    def setUp(self):
        self.paciente = Paciente.objects.create(nome="Paciente Teste")
        
    def test_create_agendamento(self):
        """Testa criação de agendamento"""
        data_agendamento = timezone.now() + timedelta(days=7)
        agendamento = Agendamento.objects.create(
            titulo="Consulta",
            descricao="Consulta de rotina",
            data=data_agendamento,
            local="Hospital GRAACC",
            paciente=self.paciente
        )
        
        self.assertEqual(agendamento.titulo, "Consulta")
        self.assertEqual(agendamento.descricao, "Consulta de rotina")
        self.assertEqual(agendamento.local, "Hospital GRAACC")
        self.assertEqual(agendamento.paciente, self.paciente)
        
    def test_agendamento_str_method(self):
        """Testa representação string do agendamento"""
        data = datetime(2025, 12, 25, 14, 30)
        agendamento = Agendamento.objects.create(
            titulo="Exame",
            descricao="Exame de sangue",
            data=data,
            local="Lab",
            paciente=self.paciente
        )
        self.assertIn("Exame", str(agendamento))
        self.assertIn("25/12/2025", str(agendamento))
        
    def test_agendamento_without_paciente(self):
        """Testa agendamento sem paciente (cascade SET_NULL)"""
        agendamento = Agendamento.objects.create(
            titulo="Consulta",
            descricao="Teste",
            data=timezone.now(),
            local="Hospital",
            paciente=self.paciente
        )
        
        # Deleta paciente
        self.paciente.delete()
        agendamento.refresh_from_db()
        
        # Agendamento deve permanecer mas sem paciente
        self.assertIsNone(agendamento.paciente)


class NotificacaoModelTest(TestCase):
    """Testes para o model Notificacao"""
    
    def setUp(self):
        self.paciente = Paciente.objects.create(nome="Paciente Teste")
        self.agendamento = Agendamento.objects.create(
            titulo="Consulta",
            descricao="Teste",
            data=timezone.now() + timedelta(days=7),
            local="Hospital",
            paciente=self.paciente
        )
        
    def test_create_notificacao(self):
        """Testa criação de notificação"""
        data_notificacao = timezone.now() + timedelta(days=3)
        notificacao = Notificacao.objects.create(
            id_agendamento=self.agendamento.id_agendamento,
            data=data_notificacao,
            lida=False
        )
        
        self.assertEqual(notificacao.id_agendamento, self.agendamento.id_agendamento)
        self.assertFalse(notificacao.lida)
        
    def test_notificacao_str_method(self):
        """Testa representação string da notificação"""
        notificacao = Notificacao.objects.create(
            id_agendamento=self.agendamento.id_agendamento,
            data=timezone.now(),
            lida=False
        )
        str_repr = str(notificacao)
        self.assertIn("Notificação", str_repr)
        self.assertIn(str(self.agendamento.id_agendamento), str_repr)
        
    def test_mark_notificacao_as_read(self):
        """Testa marcar notificação como lida"""
        notificacao = Notificacao.objects.create(
            id_agendamento=self.agendamento.id_agendamento,
            data=timezone.now(),
            lida=False
        )
        
        self.assertFalse(notificacao.lida)
        
        notificacao.lida = True
        notificacao.save()
        
        self.assertTrue(notificacao.lida)


# ============================================================================
# TESTES DE SERIALIZERS
# ============================================================================

class SerializerTest(TestCase):
    """Testes para serializers"""
    
    def test_user_register_serializer_valid(self):
        """Testa serializer de registro válido"""
        data = {
            'nome': 'João Silva',
            'email': 'joao@email.com',
            'senha': 'senha123',
            'nome_completo_paciente': 'Maria Silva'
        }
        serializer = UserRegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
    def test_user_register_serializer_invalid_email(self):
        """Testa serializer com email inválido"""
        data = {
            'nome': 'João Silva',
            'email': 'email_invalido',
            'senha': 'senha123',
            'nome_completo_paciente': 'Maria Silva'
        }
        serializer = UserRegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        
    def test_appointment_date_format_validation(self):
        """Testa validação de formato de data"""
        data = {
            'titulo': 'Consulta',
            'descricao': 'Teste',
            'data': '25/12/2025 14:30',
            'local': 'Hospital',
            'nome_completo_paciente': 'Test'
        }
        serializer = AppointmentRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
    def test_appointment_invalid_date_format(self):
        """Testa validação de formato de data inválido"""
        data = {
            'titulo': 'Consulta',
            'descricao': 'Teste',
            'data': '2025-12-25 14:30',  # Formato errado
            'local': 'Hospital',
            'nome_completo_paciente': 'Test'
        }
        serializer = AppointmentRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())


# Continua nos próximos blocos...

