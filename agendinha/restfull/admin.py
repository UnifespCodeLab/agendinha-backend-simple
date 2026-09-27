from django.contrib import admin
from .models import Usuario, Responsavel, Agendamento, Notificacao

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'role')
    search_fields = ('nome', 'email')

@admin.register(Responsavel)
class ResponsavelAdmin(admin.ModelAdmin):
    list_display = ('nome', 'telefone')
    search_fields = ('nome', 'telefone')

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'usuario', 'data', 'medico', 'lembrete_enviado')
    list_filter = ('data', 'lembrete_enviado')
    search_fields = ('titulo', 'medico')

@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ('id_agendamento', 'data', 'lida')
    list_filter = ('lida', 'data')
