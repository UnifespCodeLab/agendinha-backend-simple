"""
Testes de endpoints de Pacientes
"""

import pytest
from django.urls import reverse
from rest_framework import status
from .models import Paciente


@pytest.mark.django_db
class TestPatientCreate:
    """Testes de criação de pacientes"""
    
    def test_create_patient_as_admin(self, admin_client):
        """Testa criação de paciente como admin"""
        url = reverse('patient-create')
        data = {'nome': 'Novo Paciente'}
        
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert Paciente.objects.filter(nome='Novo Paciente').exists()
        assert 'id_paciente' in response.data
        
    def test_create_patient_as_user(self, authenticated_client):
        """Testa criação de paciente como usuário comum (deve falhar)"""
        url = reverse('patient-create')
        data = {'nome': 'Novo Paciente'}
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
    def test_create_patient_duplicate_name(self, admin_client, paciente):
        """Testa criação de paciente com nome duplicado"""
        url = reverse('patient-create')
        data = {'nome': paciente.nome}
        
        response = admin_client.post(url, data, format='json')
        
        # Pode retornar 400 (validação) ou 500 (erro interno)
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR]
        if response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            assert 'ja existe' in response.data['message'].lower()
        
    def test_create_patient_unauthenticated(self, api_client):
        """Testa criação sem autenticação"""
        url = reverse('patient-create')
        data = {'nome': 'Novo Paciente'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPatientList:
    """Testes de listagem de pacientes"""
    
    def test_list_patients_as_admin(self, admin_client, paciente, paciente2):
        """Testa listagem de pacientes como admin"""
        url = reverse('patient-list')
        
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
        
    def test_list_patients_empty(self, admin_client):
        """Testa listagem quando não há pacientes"""
        url = reverse('patient-list')
        
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
    def test_list_patients_as_user(self, authenticated_client):
        """Testa listagem como usuário comum (deve falhar)"""
        url = reverse('patient-list')
        
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestPatientUpdate:
    """Testes de atualização de pacientes"""
    
    def test_update_patient_as_admin(self, admin_client, paciente):
        """Testa atualização de paciente como admin"""
        url = reverse('patient-update', kwargs={'id': paciente.id_paciente})
        data = {'nome': 'Nome Atualizado'}
        
        response = admin_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        paciente.refresh_from_db()
        assert paciente.nome == 'Nome Atualizado'
        
    def test_update_patient_not_found(self, admin_client):
        """Testa atualização de paciente inexistente"""
        url = reverse('patient-update', kwargs={'id': 99999})
        data = {'nome': 'Novo Nome'}
        
        response = admin_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
    def test_update_patient_as_user(self, authenticated_client, paciente):
        """Testa atualização como usuário comum (deve falhar)"""
        url = reverse('patient-update', kwargs={'id': paciente.id_paciente})
        data = {'nome': 'Novo Nome'}
        
        response = authenticated_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestPatientDelete:
    """Testes de deleção de pacientes"""
    
    def test_delete_patient_as_admin(self, admin_client, paciente):
        """Testa deleção de paciente como admin"""
        url = reverse('patient-delete', kwargs={'id': paciente.id_paciente})
        patient_id = paciente.id_paciente
        
        response = admin_client.delete(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert not Paciente.objects.filter(id_paciente=patient_id).exists()
        
    def test_delete_patient_not_found(self, admin_client):
        """Testa deleção de paciente inexistente"""
        url = reverse('patient-delete', kwargs={'id': 99999})
        
        response = admin_client.delete(url)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
    def test_delete_patient_as_user(self, authenticated_client, paciente):
        """Testa deleção como usuário comum (deve falhar)"""
        url = reverse('patient-delete', kwargs={'id': paciente.id_paciente})
        
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestPatientSearch:
    """Testes de busca de pacientes"""
    
    def test_search_patient_by_name(self, api_client, paciente):
        """Testa busca de paciente por nome"""
        url = reverse('patient-search-name')
        data = {'nome': paciente.nome}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['nome'] == paciente.nome
        assert response.data['id_paciente'] == paciente.id_paciente
        
    def test_search_patient_by_name_not_found(self, api_client):
        """Testa busca de paciente inexistente"""
        url = reverse('patient-search-name')
        data = {'nome': 'Paciente Inexistente'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
    def test_search_patient_by_id(self, api_client, paciente):
        """Testa busca de paciente por ID"""
        url = reverse('patient-search-id', kwargs={'id': paciente.id_paciente})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['nome'] == paciente.nome
        
    def test_search_patient_by_id_not_found(self, api_client):
        """Testa busca por ID inexistente"""
        url = reverse('patient-search-id', kwargs={'id': 99999})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
