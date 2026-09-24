"""
URLs para API Unificada
Compatível com estrutura dos microserviços Java
"""

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    admin_views, appointment_views, guardian_views,
    notification_views, subscription_views, user_views
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
    path('usuarios/registrar', user_views.user_register, name='user-register'),
    path('usuarios/login', user_views.user_login, name='user-login'),
    path('usuarios/login/google', user_views.user_login_google, name='user-login-google'),
    path('usuarios/confirmar', user_views.user_confirm, name='user-confirm'),
    path('usuarios/foto', user_views.user_avatar_update, name='user-avatar-update'),
    path('usuarios/email/redefinir-senha', user_views.user_request_password_update, name='user-request-password-update'),
    path('usuarios/redefinir-senha/sem-autenticar', user_views.user_password_update_without_auth, name='user-password-update-without-auth'),
    path('usuarios/redefinir-senha', user_views.user_password_update, name='user-password-update'),
    path('usuarios', user_views.user_get, name='user-get'),  # GET
    path('usuarios/pesquisar', user_views.user_search_by_name, name='user-search-name'),  # GET
    # Nota: PUT e DELETE para /usuarios serão tratados na mesma view com método HTTP

    # ========================================================================
    # AUTENTICAÇÃO - ADMIN
    # ========================================================================
    path('admin/registrar', admin_views.admin_register, name='admin-register'),
    path('admin/usuarios/registrar', admin_views.user_register, name='admin-user-register'),
    path('admin/login', admin_views.admin_login, name='admin-login'),

    # ========================================================================
    # RESPONSÁVEIS
    # ========================================================================
    path('responsaveis', guardian_views.guardian_list, name='guardian-list'),  # GET (ADMIN)
    path('responsaveis/pesquisar', guardian_views.guardian_search_by_name, name='guardian-search-name'),  # POST
    path('responsaveis/pesquisar/<int:id>', guardian_views.guardian_search_by_id, name='guardian-search-id'),  # GET
    path('responsaveis/<int:id>', guardian_views.guardian_update, name='guardian-update'),  # PUT
    # Nota: POST para criar responsável será tratado na mesma URL /responsaveis

    # ========================================================================
    # AGENDAMENTOS
    # ========================================================================
    path('agendamentos', appointment_views.appointment_list, name='appointment-list'),  # GET (ADMIN)
    path('agendamentos/<int:id>', appointment_views.appointment_get, name='appointment-get'),  # GET
    path('agendamentos/usuario', appointment_views.appointment_list_user, name='appointment-list-user'),  # GET (USER)
    path('agendamentos/google', appointment_views.appointment_export_task_to_google_calendar, name='appointment-export-task-to-google-calendar'),  # POST (USER)
    # Nota: POST, PUT, DELETE serão tratados com views específicas

    # ========================================================================
    # NOTIFICAÇÕES
    # ========================================================================
    path('notificacoes', notification_views.notification_create, name='notification-create'),  # POST
    path('notificacoes/conjunto', notification_views.notification_create_batch, name='notification-create-batch'),  # POST
    path('notificacoes/<int:id_agendamento>', notification_views.notification_list_by_appointment, name='notification-list'),  # GET
    path('notificacoes/usuario/<int:id_usuario>', notification_views.notification_list_by_user, name='notification-list-by-user'),  # GET
    path('notificacoes/id/<int:id_notificacao>', notification_views.notification_delete_by_id, name='notification-delete-by-id'),  # GET
    path('notificacoes/naoLidas', notification_views.notification_list_unread, name='notification-list-unread'),  # POST
    path('notificacoes/<int:id_notificacao>/lida', notification_views.notification_mark_as_read, name='notification-mark-read'),  # POST

    path("salvar-inscricao", subscription_views.save_subscription, name="save_subscription"),
]

# URLs que precisam de tratamento especial para métodos HTTP diferentes
urlpatterns += [
    # Usuário: GET, PUT, DELETE em /usuarios
    path('usuarios/update', user_views.user_update, name='user-update'),  # PUT
    path('usuarios/delete', user_views.user_delete, name='user-delete'),  # DELETE

    # Responsáveis: POST em /responsaveis, DELETE em /responsaveis/{id}
    path('responsaveis/create', guardian_views.guardian_create, name='guardian-create'),  # POST
    path('responsaveis/<int:id>/delete', guardian_views.guardian_delete, name='guardian-delete'),  # DELETE

    # Agendamento: POST, PUT, DELETE
    path('agendamentos/create', appointment_views.appointment_create, name='appointment-create'),  # POST
    path('agendamentos/<int:id>/update', appointment_views.appointment_update, name='appointment-update'),  # PUT
    path('agendamentos/<int:id>/delete', appointment_views.appointment_delete, name='appointment-delete'),  # DELETE

    # Notificação: DELETE
    path('notificacoes/<int:id_agendamento>/delete', notification_views.notification_delete_by_appointment, name='notification-delete'),  # DELETE
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )