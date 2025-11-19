"""
Testes de Autenticação - Usuários e Administradores
"""

import pytest
from django.urls import reverse
from rest_framework import status
from .models import Usuario, Paciente, Role


@pytest.mark.django_db
class TestUserRegistration:
    """Testes de registro de usuários"""
    
    def test_register_user_success(self, api_client, paciente):
        """Testa registro de usuário com sucesso"""
        url = reverse('user-register')
        data = {
            'nome': 'Novo User',
            'email': 'novo@email.com',
            'senha': 'senha123',
            'nome_completo_paciente': paciente.nome
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert Usuario.objects.filter(email='novo@email.com').exists()
        
        user = Usuario.objects.get(email='novo@email.com')
        assert user.nome == 'Novo User'
        assert user.role == Role.USER
        assert user.id_paciente == paciente.id_paciente
        assert not user.cadastro_confirmado
        
    def test_register_user_paciente_not_found(self, api_client):
        """Testa registro com paciente inexistente"""
        url = reverse('user-register')
        data = {
            'nome': 'Novo User',
            'email': 'novo@email.com',
            'senha': 'senha123',
            'nome_completo_paciente': 'Paciente Inexistente'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'não existe nenhum paciente' in response.data['message'].lower()
        
    def test_register_user_duplicate_email(self, api_client, user, paciente):
        """Testa registro com email já existente"""
        url = reverse('user-register')
        data = {
            'nome': 'Outro User',
            'email': user.email,  # Email já existe
            'senha': 'senha123',
            'nome_completo_paciente': paciente.nome
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'email já cadastrado' in response.data['message'].lower()
        
    def test_register_user_with_patient_id_success(self, api_client, paciente):
        """Testa registro de usuário com ID do paciente"""
        url = reverse('user-register-patient-id')
        data = {
            'nome': 'User Com ID',
            'email': 'userid@email.com',
            'senha': 'senha123',
            'id_paciente': paciente.id_paciente
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert Usuario.objects.filter(email='userid@email.com').exists()
        
    def test_register_user_with_invalid_patient_id(self, api_client):
        """Testa registro com ID de paciente inválido"""
        url = reverse('user-register-patient-id')
        data = {
            'nome': 'User Com ID',
            'email': 'userid@email.com',
            'senha': 'senha123',
            'id_paciente': 99999  # ID inexistente
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.django_db
class TestUserLogin:
    """Testes de login de usuários"""
    
    def test_login_success(self, api_client, user):
        """Testa login com credenciais válidas"""
        url = reverse('user-login')
        data = {
            'email': user.email,
            'senha': 'senha123'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data
        assert 'nome' in response.data
        assert response.data['nome'] == user.nome
        
    def test_login_invalid_email(self, api_client):
        """Testa login com email inexistente"""
        url = reverse('user-login')
        data = {
            'email': 'inexistente@email.com',
            'senha': 'senha123'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_login_invalid_password(self, api_client, user):
        """Testa login com senha incorreta"""
        url = reverse('user-login')
        data = {
            'email': user.email,
            'senha': 'senhaerrada'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserOperations:
    """Testes de operações de usuário autenticado"""
    
    def test_confirm_user(self, authenticated_client, user_not_confirmed):
        """Testa confirmação de cadastro"""
        url = reverse('user-confirm')
        
        assert not user_not_confirmed.cadastro_confirmado
        
        # Precisa criar novo cliente autenticado para o usuário não confirmado
        from .conftest import user_token
        import jwt
        from django.conf import settings
        from django.utils import timezone
        from datetime import timedelta
        
        payload = {
            'sub': user_not_confirmed.email,
            'iss': settings.SECURITY_EMISSOR,
            'idUsuario': user_not_confirmed.id_usuario,
            'idPaciente': user_not_confirmed.id_paciente,
            'role': user_not_confirmed.role,
            'iat': timezone.now(),
            'exp': timezone.now() + timedelta(hours=24)
        }
        token = jwt.encode(payload, settings.SECURITY_TOKEN, algorithm='HS256')
        
        from rest_framework.test import APIClient
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        user_not_confirmed.refresh_from_db()
        assert user_not_confirmed.cadastro_confirmado
        
    def test_get_user(self, authenticated_client, user):
        """Testa obtenção de dados do usuário"""
        url = reverse('user-get')
        
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email
        assert response.data['nome'] == user.nome
        assert response.data['id_usuario'] == user.id_usuario
        
    def test_update_user_name(self, authenticated_client, user):
        """Testa atualização de nome do usuário"""
        url = reverse('user-update')
        data = {'nome': 'Nome Atualizado'}
        
        response = authenticated_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        user.refresh_from_db()
        assert user.nome == 'Nome Atualizado'
        
    def test_update_user_email(self, authenticated_client, user):
        """Testa atualização de email do usuário"""
        url = reverse('user-update')
        data = {'email': 'novoemail@test.com'}
        
        response = authenticated_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        user.refresh_from_db()
        assert user.email == 'novoemail@test.com'
        
    def test_update_user_duplicate_email(self, authenticated_client, user, admin):
        """Testa atualização com email já existente"""
        url = reverse('user-update')
        data = {'email': admin.email}  # Email do admin
        
        response = authenticated_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_delete_user(self, authenticated_client, user):
        """Testa deleção do usuário"""
        url = reverse('user-delete')
        user_id = user.id_usuario
        
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert not Usuario.objects.filter(id_usuario=user_id).exists()
        
    def test_get_user_unauthenticated(self, api_client):
        """Testa obtenção de dados sem autenticação"""
        url = reverse('user-get')
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAdminRegistration:
    """Testes de registro e login de administradores"""
    
    def test_register_admin_success(self, api_client):
        """Testa registro de admin com sucesso"""
        url = reverse('admin-register')
        data = {
            'nome': 'Novo Admin',
            'email': 'novoadmin@email.com',
            'senha': 'admin123'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert Usuario.objects.filter(email='novoadmin@email.com').exists()
        
        admin = Usuario.objects.get(email='novoadmin@email.com')
        assert admin.role == Role.ADMIN
        assert admin.id_paciente is None
        
    def test_register_admin_duplicate_email(self, api_client, admin):
        """Testa registro de admin com email duplicado"""
        url = reverse('admin-register')
        data = {
            'nome': 'Outro Admin',
            'email': admin.email,
            'senha': 'admin123'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
    def test_admin_login(self, api_client, admin):
        """Testa login de administrador"""
        url = reverse('admin-login')
        data = {
            'email': admin.email,
            'senha': 'admin123'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data
        assert 'nome' in response.data
