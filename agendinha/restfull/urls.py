"""
URLs para API Unificada
Compatível com estrutura dos microserviços Java
"""

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    admin, appointment, guardian, notification, subscription, user
)
from .views.utils import (
    create_appointment_page, create_notification_page, create_guardian_page, hello_world
)

urlpatterns = [
    # ========================================================================
    # PÁGINAS HTML ESTÁTICAS
    # ========================================================================
    path('criar-responsavel', create_guardian_page, name='create-guardian-page'),
    path('criar-agendamento', create_appointment_page, name='create-appointment-page'),
    path('criar-notificacao', create_notification_page, name='create-notification-page'),

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================
    path('hello', hello_world, name='hello'),

    # ========================================================================
    # AUTENTICAÇÃO - USUÁRIOS
    # ========================================================================
    path('usuarios/registrar', user.user_register, name='user-register'),
    path('usuarios/login', user.user_login, name='user-login'),
    path('usuarios/login/google', user.user_login_google, name='user-login-google'),
    path('usuarios/confirmar', user.user_confirm, name='user-confirm'),
    path('usuarios/foto', user.user_avatar_update, name='user-avatar-update'),
    path('usuarios/email/redefinir-senha', user.user_request_password_update, name='user-request-password-update'),
    path('usuarios/redefinir-senha', user.user_password_update, name='user-password-update'),
    path('usuarios', user.user_get, name='user-get'),  # GET
    path('usuarios/pesquisar', user.user_search_by_name, name='user-search-name'),  # GET
    # Nota: PUT e DELETE para /usuarios serão tratados na mesma view com método HTTP

    # ========================================================================
    # AUTENTICAÇÃO - ADMIN
    # ========================================================================
    path('admin/registrar', admin.admin_register, name='admin-register'),
    path('admin/usuarios/registrar', admin.user_register, name='admin-user-register'),
    path('admin/login', admin.admin_login, name='admin-login'),

    # ========================================================================
    # RESPONSÁVEIS
    # ========================================================================
    path('responsaveis', guardian.guardian_list, name='guardian-list'),  # GET (ADMIN)
    path('responsaveis/pesquisar', guardian.guardian_search_by_name, name='guardian-search-name'),  # POST
    path('responsaveis/pesquisar/<int:id>', guardian.guardian_search_by_id, name='guardian-search-id'),  # GET
    path('responsaveis/<int:id>', guardian.guardian_update, name='guardian-update'),  # PUT
    # Nota: POST para criar responsável será tratado na mesma URL /responsaveis

    # ========================================================================
    # AGENDAMENTOS
    # ========================================================================
    path('agendamentos', appointment.appointment_list, name='appointment-list'),  # GET (ADMIN)
    path('agendamentos/<int:id>', appointment.appointment_get, name='appointment-get'),  # GET
    path('agendamentos/usuario', appointment.appointment_list_user, name='appointment-list-user'),  # GET (USER)
    path('agendamentos/google', appointment.appointment_export_task_to_google_calendar, name='appointment-export-task-to-google-calendar'),  # POST (USER)
    # Nota: POST, PUT, DELETE serão tratados com views específicas

    # ========================================================================
    # NOTIFICAÇÕES
    # ========================================================================
    path('notificacoes', notification.notification_create, name='notification-create'),  # POST
    path('notificacoes/conjunto', notification.notification_create_batch, name='notification-create-batch'),  # POST
    path('notificacoes/<int:id_agendamento>', notification.notification_list_by_appointment, name='notification-list'),  # GET
    path('notificacoes/usuario/<int:id_usuario>', notification.notification_list_by_user, name='notification-list-by-user'),  # GET
    path('notificacoes/id/<int:id_notificacao>', notification.notification_delete_by_id, name='notification-delete-by-id'),  # GET
    path('notificacoes/naoLidas', notification.notification_list_unread, name='notification-list-unread'),  # POST
    path('notificacoes/<int:id_notificacao>/lida', notification.notification_mark_as_read, name='notification-mark-read'),  # POST

    path("salvar-inscricao", subscription.save_subscription, name="save_subscription"),
]

# URLs que precisam de tratamento especial para métodos HTTP diferentes
urlpatterns += [
    # Usuário: GET, PUT, DELETE em /usuarios
    path('usuarios/update', user.user_update, name='user-update'),  # PUT
    path('usuarios/delete', user.user_delete, name='user-delete'),  # DELETE

    # Responsáveis: POST em /responsaveis, DELETE em /responsaveis/{id}
    path('responsaveis/create', guardian.guardian_create, name='guardian-create'),  # POST
    path('responsaveis/<int:id>/delete', guardian.guardian_delete, name='guardian-delete'),  # DELETE

    # Agendamento: POST, PUT, DELETE
    path('agendamentos/create', appointment.appointment_create, name='appointment-create'),  # POST
    path('agendamentos/<int:id>/update', appointment.appointment_update, name='appointment-update'),  # PUT
    path('agendamentos/<int:id>/delete', appointment.appointment_delete, name='appointment-delete'),  # DELETE

    # Notificação: DELETE
    path('notificacoes/<int:id_agendamento>/delete', notification.notification_delete_by_appointment, name='notification-delete'),  # DELETE
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )