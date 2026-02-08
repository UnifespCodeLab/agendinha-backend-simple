"""
URLs para GRAACC API Unificada
Compatível com estrutura dos microserviços Java
"""

from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ========================================================================
    # HEALTH CHECK
    # ========================================================================
    path('hello', views.hello_world, name='hello'),
    
    # ========================================================================
    # AUTENTICAÇÃO - USUÁRIOS
    # ========================================================================
    path('usuarios/registrar', views.user_register, name='user-register'),
    path('usuarios/pacienteid/registrar', views.user_register_with_patient_id, name='user-register-patient-id'),
    path('usuarios/login', views.user_login, name='user-login'),
    path('usuarios/confirmar', views.user_confirm, name='user-confirm'),
    path('usuarios/foto', views.user_avatar_update, name='user-avatar-update'),
    path('usuarios', views.user_get, name='user-get'),  # GET
    # Nota: PUT e DELETE para /usuarios serão tratados na mesma view com método HTTP
    
    # ========================================================================
    # AUTENTICAÇÃO - ADMIN
    # ========================================================================
    path('admin/registrar', views.admin_register, name='admin-register'),
    path('admin/login', views.admin_login, name='admin-login'),
    
    # ========================================================================
    # PACIENTES
    # ========================================================================
    path('pacientes', views.patient_list, name='patient-list'),  # GET (ADMIN)
    path('pacientes/pesquisar', views.patient_search_by_name, name='patient-search-name'),  # POST
    path('pacientes/pesquisar/<int:id>', views.patient_search_by_id, name='patient-search-id'),  # GET
    path('pacientes/<int:id>', views.patient_update, name='patient-update'),  # PUT
    # Nota: POST para criar paciente será tratado na mesma URL /pacientes
    
    # ========================================================================
    # AGENDAMENTOS
    # ========================================================================
    path('agendamentos', views.appointment_list, name='appointment-list'),  # GET (ADMIN)
    path('agendamentos/<int:id>', views.appointment_get, name='appointment-get'),  # GET
    path('agendamentos/usuario', views.appointment_list_user, name='appointment-list-user'),  # GET (USER)
    # Nota: POST, PUT, DELETE serão tratados com views específicas
    
    # ========================================================================
    # NOTIFICAÇÕES
    # ========================================================================
    path('notificacoes', views.notification_create, name='notification-create'),  # POST
    path('notificacoes/conjunto', views.notification_create_batch, name='notification-create-batch'),  # POST
    path('notificacoes/<int:id_agendamento>', views.notification_list_by_appointment, name='notification-list'),  # GET
    path('notificacoes/naoLidas', views.notification_list_unread, name='notification-list-unread'),  # POST
    path('notificacoes/<int:id_notificacao>/lida', views.notification_mark_as_read, name='notification-mark-read'),  # POST
]

# URLs que precisam de tratamento especial para métodos HTTP diferentes
# Adicionar views que tratam PUT e DELETE
from django.views.decorators.http import require_http_methods

# Criar wrappers para views que aceitam múltiplos métodos HTTP
urlpatterns += [
    # Usuário: GET, PUT, DELETE em /usuarios
    path('usuarios/update', views.user_update, name='user-update'),  # PUT
    path('usuarios/delete', views.user_delete, name='user-delete'),  # DELETE
    
    # Paciente: POST em /pacientes, DELETE em /pacientes/{id}
    path('pacientes/create', views.patient_create, name='patient-create'),  # POST
    path('pacientes/<int:id>/delete', views.patient_delete, name='patient-delete'),  # DELETE
    
    # Agendamento: POST, PUT, DELETE
    path('agendamentos/create', views.appointment_create, name='appointment-create'),  # POST
    path('agendamentos/<int:id>/update', views.appointment_update, name='appointment-update'),  # PUT
    path('agendamentos/<int:id>/delete', views.appointment_delete, name='appointment-delete'),  # DELETE
    
    # Notificação: DELETE
    path('notificacoes/<int:id_agendamento>/delete', views.notification_delete_by_appointment, name='notification-delete'),  # DELETE
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
