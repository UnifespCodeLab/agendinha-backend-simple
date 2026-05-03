"""
URLs para GRAACC API Unificada
Compatível com estrutura dos microserviços Java
"""

from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ========================================================================
    # PÁGINAS HTML ESTÁTICAS
    # ========================================================================
    path('criar-paciente', views.create_patient_page, name='create-patient-page'),
    path('criar-agendamento', views.create_appointment_page, name='create-appointment-page'),
    path('criar-notificacao', views.create_notification_page, name='create-notification-page'),

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================
    path('hello', views.hello_world, name='hello'),
    
    # ========================================================================
    # AUTENTICAÇÃO - USUÁRIOS
    # ========================================================================
    path('usuarios/registrar', views.user_register, name='user-register'),
    path('usuarios/login', views.user_login, name='user-login'),
    path('usuarios/login/google', views.user_login_google, name='user-login-google'),
    path('usuarios/confirmar', views.user_confirm, name='user-confirm'),
    path('usuarios/foto', views.user_avatar_update, name='user-avatar-update'),
    path('usuarios/email/redefinir-senha', views.user_request_password_update, name='user-request-password-update'),
    path('usuarios/redefinir-senha-sl', views.user_password_update_without_auth, name='user-password-update-without-auth'),
    path('usuarios/redefinir-senha', views.user_password_update, name='user-password-update'),
    path('usuarios', views.user_get, name='user-get'),  # GET
    # Nota: PUT e DELETE para /usuarios serão tratados na mesma view com método HTTP
    
    # ========================================================================
    # AUTENTICAÇÃO - ADMIN
    # ========================================================================
    path('admin/registrar', views.admin_register, name='admin-register'),
    path('admin/login', views.admin_login, name='admin-login'),
    
    # ========================================================================
    # RESPONSÁVEIS
    # ========================================================================
    path('responsaveis', views.guardian_list, name='guardian-list'),  # GET (ADMIN)
    path('responsaveis/pesquisar', views.guardian_search_by_name, name='guardian-search-name'),  # POST
    path('responsaveis/pesquisar/<int:id>', views.guardian_search_by_id, name='guardian-search-id'),  # GET
    path('responsaveis/<int:id>', views.guardian_update, name='guardian-update'),  # PUT
    # Nota: POST para criar responsável será tratado na mesma URL /responsaveos
    
    # ========================================================================
    # AGENDAMENTOS
    # ========================================================================
    path('agendamentos', views.appointment_list, name='appointment-list'),  # GET (ADMIN)
    path('agendamentos/<int:id>', views.appointment_get, name='appointment-get'),  # GET
    path('agendamentos/usuario', views.appointment_list_user, name='appointment-list-user'),  # GET (USER)
    path('agendamentos/google', views.appointment_export_task_to_google_calendar, name='appointment-export-task-to-google-calendar'),  # POST (USER)
    # Nota: POST, PUT, DELETE serão tratados com views específicas
    
    # ========================================================================
    # NOTIFICAÇÕES
    # ========================================================================
    path('notificacoes', views.notification_create, name='notification-create'),  # POST
    path('notificacoes/conjunto', views.notification_create_batch, name='notification-create-batch'),  # POST
    path('notificacoes/<int:id_agendamento>', views.notification_list_by_appointment, name='notification-list'),  # GET
    path('notificacoes/usuario/<int:id_usuario>', views.notification_list_by_user, name='notification-list-by-user'),  # GET
    path('notificacoes/id/<int:id_notificacao>', views.notification_delete_by_id, name='notification-delete-by-id'),  # GET
    path('notificacoes/naoLidas', views.notification_list_unread, name='notification-list-unread'),  # POST
    path('notificacoes/<int:id_notificacao>/lida', views.notification_mark_as_read, name='notification-mark-read'),  # POST

    path("salvar-inscricao", views.save_subscription, name="save_subscription"),
]

# URLs que precisam de tratamento especial para métodos HTTP diferentes
# Adicionar views que tratam PUT e DELETE
from django.views.decorators.http import require_http_methods

# Criar wrappers para views que aceitam múltiplos métodos HTTP
urlpatterns += [
    # Usuário: GET, PUT, DELETE em /usuarios
    path('usuarios/update', views.user_update, name='user-update'),  # PUT
    path('usuarios/delete', views.user_delete, name='user-delete'),  # DELETE
    
    # Responsáveis: POST em /responsaveis, DELETE em /responsaveis/{id}
    path('responsaveis/create', views.guardian_create, name='guardian-create'),  # POST
    path('responsaveis/<int:id>/delete', views.guardian_delete, name='guardian-delete'),  # DELETE
    
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
