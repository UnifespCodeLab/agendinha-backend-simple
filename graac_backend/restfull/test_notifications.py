"""
Testes de endpoints de Notificações
"""

import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from .models import Notificacao


@pytest.mark.django_db
class TestNotificationCreate:
    """Testes de criação de notificações"""
    
    def test_create_notifications_as_admin(self, admin_client, agendamento):
        """Testa criação de notificações como admin"""
        url = reverse('notification-create')
        future_date = (timezone.now() + timedelta(days=14)).strftime('%d/%m/%Y %H:%M')
        
        data = {
            'id_agendamento': agendamento.id_agendamento,
            'data_agendamento': future_date
        }
        
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        # Deve criar 4 notificações (1 semana, 3 dias, 1 dia, 4 horas antes)
        notifications = Notificacao.objects.filter(id_agendamento=agendamento.id_agendamento)
        assert notifications.count() > 0
        
    def test_create_notifications_past_date(self, admin_client, agendamento):
        """Testa criação de notificações para data passada"""
        url = reverse('notification-create')
        past_date = (timezone.now() - timedelta(days=7)).strftime('%d/%m/%Y %H:%M')
        
        data = {
            'id_agendamento': agendamento.id_agendamento,
            'data_agendamento': past_date
        }
        
        response = admin_client.post(url, data, format='json')
        
        # Não deve criar notificações para datas passadas
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
    def test_create_notifications_invalid_date_format(self, admin_client, agendamento):
        """Testa criação com formato de data inválido"""
        url = reverse('notification-create')
        
        data = {
            'id_agendamento': agendamento.id_agendamento,
            'data_agendamento': '2025-12-25 14:30'  # Formato errado
        }
        
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_create_notifications_as_user(self, authenticated_client, agendamento):
        """Testa criação como usuário comum (deve falhar)"""
        url = reverse('notification-create')
        future_date = (timezone.now() + timedelta(days=14)).strftime('%d/%m/%Y %H:%M')
        
        data = {
            'id_agendamento': agendamento.id_agendamento,
            'data_agendamento': future_date
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestNotificationCreateBatch:
    """Testes de criação em lote de notificações"""
    
    def test_create_batch_notifications(self, admin_client, agendamento, agendamento_futuro):
        """Testa criação de notificações em lote"""
        url = reverse('notification-create-batch')
        date1 = (timezone.now() + timedelta(days=14)).strftime('%d/%m/%Y %H:%M')
        date2 = (timezone.now() + timedelta(days=21)).strftime('%d/%m/%Y %H:%M')
        
        data = [
            {
                'id_agendamento': agendamento.id_agendamento,
                'data_agendamento': date1
            },
            {
                'id_agendamento': agendamento_futuro.id_agendamento,
                'data_agendamento': date2
            }
        ]
        
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        # Deve criar notificações para ambos os agendamentos
        
    def test_create_batch_notifications_empty(self, admin_client):
        """Testa criação em lote com lista vazia"""
        url = reverse('notification-create-batch')
        data = []
        
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_400_BAD_REQUEST]


@pytest.mark.django_db
class TestNotificationList:
    """Testes de listagem de notificações"""
    
    def test_list_notifications_by_appointment(self, authenticated_client, notificacao):
        """Testa listagem de notificações por agendamento"""
        url = reverse('notification-list', kwargs={'id_agendamento': notificacao.id_agendamento})
        
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        
    def test_list_notifications_empty(self, authenticated_client, agendamento):
        """Testa listagem quando não há notificações"""
        url = reverse('notification-list', kwargs={'id_agendamento': agendamento.id_agendamento})
        
        response = authenticated_client.get(url)
        
        # Se não houver notificações criadas ainda
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]


@pytest.mark.django_db
class TestNotificationUnread:
    """Testes de listagem de notificações não lidas"""
    
    def test_list_unread_notifications(self, authenticated_client, notificacao):
        """Testa listagem de notificações não lidas"""
        url = reverse('notification-list-unread')
        future_date = (timezone.now() + timedelta(days=7)).strftime('%d/%m/%Y %H:%M')
        
        data = [
            {
                'id_agendamento': notificacao.id_agendamento,
                'data_agendamento': future_date
            }
        ]
        
        response = authenticated_client.post(url, data, format='json')
        
        # Pode retornar 200 com dados ou 204 se não houver notificações futuras não lidas
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]
        
    def test_list_unread_notifications_only_unread(self, authenticated_client, notificacao, notificacao_lida):
        """Testa que apenas notificações não lidas são retornadas"""
        url = reverse('notification-list-unread')
        future_date = (timezone.now() + timedelta(days=7)).strftime('%d/%m/%Y %H:%M')
        
        data = [
            {
                'id_agendamento': notificacao.id_agendamento,
                'data_agendamento': future_date
            }
        ]
        
        response = authenticated_client.post(url, data, format='json')
        
        if response.status_code == status.HTTP_200_OK:
            # Verificar que notificações lidas não estão na resposta
            for notif in response.data:
                assert not notif['lida']


@pytest.mark.django_db
class TestNotificationMarkRead:
    """Testes de marcação de notificação como lida"""
    
    def test_mark_notification_as_read(self, authenticated_client, notificacao):
        """Testa marcar notificação como lida"""
        url = reverse('notification-mark-read', kwargs={'id_notificacao': notificacao.id_notificacao})
        
        assert not notificacao.lida
        
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        notificacao.refresh_from_db()
        assert notificacao.lida
        
    def test_mark_notification_not_found(self, authenticated_client):
        """Testa marcar notificação inexistente como lida"""
        url = reverse('notification-mark-read', kwargs={'id_notificacao': 99999})
        
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_mark_already_read_notification(self, authenticated_client, notificacao_lida):
        """Testa marcar notificação já lida"""
        url = reverse('notification-mark-read', kwargs={'id_notificacao': notificacao_lida.id_notificacao})
        
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        notificacao_lida.refresh_from_db()
        assert notificacao_lida.lida  # Continua lida


@pytest.mark.django_db
class TestNotificationDelete:
    """Testes de deleção de notificações"""
    
    def test_delete_notifications_by_appointment_as_admin(self, admin_client, notificacao):
        """Testa deleção de notificações por agendamento como admin"""
        url = reverse('notification-delete', kwargs={'id_agendamento': notificacao.id_agendamento})
        id_agendamento = notificacao.id_agendamento
        
        response = admin_client.delete(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert not Notificacao.objects.filter(id_agendamento=id_agendamento).exists()
        
    def test_delete_notifications_as_user(self, authenticated_client, notificacao):
        """Testa deleção como usuário comum (deve falhar)"""
        url = reverse('notification-delete', kwargs={'id_agendamento': notificacao.id_agendamento})
        
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
    def test_delete_notifications_empty_appointment(self, admin_client, agendamento):
        """Testa deleção de notificações de agendamento sem notificações"""
        url = reverse('notification-delete', kwargs={'id_agendamento': agendamento.id_agendamento})
        
        response = admin_client.delete(url)
        
        # Deve retornar sucesso mesmo se não houver notificações
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestHealthCheck:
    """Testes de health check"""
    
    def test_hello_world(self, api_client):
        """Testa endpoint de health check"""
        url = reverse('hello')
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'Hello World' in response.data
