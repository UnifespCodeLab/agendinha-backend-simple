"""
Testes de endpoints de Agendamentos
"""

import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from .models import Agendamento


@pytest.mark.django_db
class TestAppointmentCreate:
    """Testes de criação de agendamentos"""
    
    def test_create_appointment_as_admin(self, admin_client, paciente):
        """Testa criação de agendamento como admin"""
        url = reverse('appointment-create')
        future_date = (timezone.now() + timedelta(days=7)).strftime('%d/%m/%Y %H:%M')
        
        data = {
            'titulo': 'Consulta Teste',
            'descricao': 'Descrição da consulta',
            'data': future_date,
            'local': 'Hospital GRAACC',
            'nome_completo_paciente': paciente.nome
        }
        
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert Agendamento.objects.filter(titulo='Consulta Teste').exists()
        
    def test_create_appointment_invalid_date_format(self, admin_client, paciente):
        """Testa criação com formato de data inválido"""
        url = reverse('appointment-create')
        
        data = {
            'titulo': 'Consulta Teste',
            'descricao': 'Descrição',
            'data': '2025-12-25 14:30',  # Formato errado
            'local': 'Hospital',
            'nome_completo_paciente': paciente.nome
        }
        
        response = admin_client.post(url, data, format='json')
        
        # Pode retornar 400 (validação) ou 500 (erro ao converter data)
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR]
        
    def test_create_appointment_patient_not_found(self, admin_client):
        """Testa criação com paciente inexistente"""
        url = reverse('appointment-create')
        future_date = (timezone.now() + timedelta(days=7)).strftime('%d/%m/%Y %H:%M')
        
        data = {
            'titulo': 'Consulta Teste',
            'descricao': 'Descrição',
            'data': future_date,
            'local': 'Hospital',
            'nome_completo_paciente': 'Paciente Inexistente'
        }
        
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
    def test_create_appointment_as_user(self, authenticated_client, paciente):
        """Testa criação como usuário comum (deve falhar)"""
        url = reverse('appointment-create')
        future_date = (timezone.now() + timedelta(days=7)).strftime('%d/%m/%Y %H:%M')
        
        data = {
            'titulo': 'Consulta',
            'descricao': 'Teste',
            'data': future_date,
            'local': 'Hospital',
            'nome_completo_paciente': paciente.nome
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAppointmentGet:
    """Testes de obtenção de agendamento"""
    
    def test_get_appointment_as_admin(self, admin_client, agendamento):
        """Testa obtenção de agendamento como admin"""
        url = reverse('appointment-get', kwargs={'id': agendamento.id_agendamento})
        
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['titulo'] == agendamento.titulo
        assert response.data['id_agendamento'] == agendamento.id_agendamento
        
    def test_get_appointment_as_user(self, authenticated_client, agendamento):
        """Testa obtenção de agendamento como usuário"""
        url = reverse('appointment-get', kwargs={'id': agendamento.id_agendamento})
        
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        
    def test_get_appointment_not_found(self, admin_client):
        """Testa obtenção de agendamento inexistente"""
        url = reverse('appointment-get', kwargs={'id': 99999})
        
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestAppointmentList:
    """Testes de listagem de agendamentos"""
    
    def test_list_appointments_as_admin(self, admin_client, agendamento, agendamento_futuro):
        """Testa listagem de todos os agendamentos como admin"""
        url = reverse('appointment-list')
        
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
        
    def test_list_appointments_empty(self, admin_client):
        """Testa listagem quando não há agendamentos"""
        url = reverse('appointment-list')
        
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
    def test_list_appointments_as_user(self, authenticated_client):
        """Testa listagem como usuário comum (deve falhar)"""
        url = reverse('appointment-list')
        
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAppointmentListUser:
    """Testes de listagem de agendamentos do usuário"""
    
    def test_list_user_appointments(self, authenticated_client, user, agendamento):
        """Testa listagem de agendamentos do usuário autenticado"""
        url = reverse('appointment-list-user')
        
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Deve retornar agendamentos do paciente associado ao usuário
        
    def test_list_user_appointments_empty(self, authenticated_client, user):
        """Testa listagem quando usuário não tem agendamentos"""
        # Não criar nenhum agendamento
        url = reverse('appointment-list-user')
        
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
    def test_list_user_appointments_as_admin(self, admin_client):
        """Testa endpoint de usuário como admin (deve falhar)"""
        url = reverse('appointment-list-user')
        
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAppointmentUpdate:
    """Testes de atualização de agendamentos"""
    
    def test_update_appointment_as_admin(self, admin_client, agendamento, paciente):
        """Testa atualização de agendamento como admin"""
        url = reverse('appointment-update', kwargs={'id': agendamento.id_agendamento})
        new_date = (timezone.now() + timedelta(days=14)).strftime('%d/%m/%Y %H:%M')
        
        data = {
            'titulo': 'Título Atualizado',
            'descricao': 'Nova descrição',
            'data': new_date,
            'local': 'Novo Local',
            'nome_completo_paciente': paciente.nome
        }
        
        response = admin_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        agendamento.refresh_from_db()
        assert agendamento.titulo == 'Título Atualizado'
        
    def test_update_appointment_not_found(self, admin_client, paciente):
        """Testa atualização de agendamento inexistente"""
        url = reverse('appointment-update', kwargs={'id': 99999})
        future_date = (timezone.now() + timedelta(days=7)).strftime('%d/%m/%Y %H:%M')
        
        data = {
            'titulo': 'Teste',
            'descricao': 'Teste',
            'data': future_date,
            'local': 'Local',
            'nome_completo_paciente': paciente.nome
        }
        
        response = admin_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
    def test_update_appointment_as_user(self, authenticated_client, agendamento, paciente):
        """Testa atualização como usuário comum (deve falhar)"""
        url = reverse('appointment-update', kwargs={'id': agendamento.id_agendamento})
        future_date = (timezone.now() + timedelta(days=7)).strftime('%d/%m/%Y %H:%M')
        
        data = {
            'titulo': 'Novo Título',
            'descricao': 'Teste',
            'data': future_date,
            'local': 'Local',
            'nome_completo_paciente': paciente.nome
        }
        
        response = authenticated_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAppointmentDelete:
    """Testes de deleção de agendamentos"""
    
    def test_delete_appointment_as_admin(self, admin_client, agendamento):
        """Testa deleção de agendamento como admin"""
        url = reverse('appointment-delete', kwargs={'id': agendamento.id_agendamento})
        appointment_id = agendamento.id_agendamento
        
        response = admin_client.delete(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert not Agendamento.objects.filter(id_agendamento=appointment_id).exists()
        
    def test_delete_appointment_not_found(self, admin_client):
        """Testa deleção de agendamento inexistente"""
        url = reverse('appointment-delete', kwargs={'id': 99999})
        
        response = admin_client.delete(url)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
    def test_delete_appointment_as_user(self, authenticated_client, agendamento):
        """Testa deleção como usuário comum (deve falhar)"""
        url = reverse('appointment-delete', kwargs={'id': agendamento.id_agendamento})
        
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
