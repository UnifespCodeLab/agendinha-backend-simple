"""
Models para GRAACC API Unificada
Migrados dos microserviços Java Spring Boot
"""

from django.db import models
import bcrypt


# ============================================================================
# USUÁRIOS (migrado do MS Usuários)
# ============================================================================

class Role(models.TextChoices):
    """Enum para roles de usuário (compatível com Java)"""
    USER = 'ROLE_USER', 'User'
    ADMIN = 'ROLE_ADMIN', 'Admin'


class Usuario(models.Model):
    """
    Model de Usuário
    Migrado de: org.codelab.graacc.Usuarios.entity.UserEntity
    """
    id_usuario = models.BigAutoField(primary_key=True)
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    senha = models.CharField(max_length=255, null=True)
    cadastro_confirmado = models.BooleanField(default=False)
    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.USER
    )
    id_paciente = models.BigIntegerField(null=True, blank=True)
    foto_perfil = models.ImageField(upload_to='images/', null=True, blank=True)
    modo_google = models.BooleanField(default=False, null=False)

    class Meta:
        db_table = 'usuario'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['id_paciente']),
        ]

    def set_password(self, raw_password):
        """
        Criptografa senha usando bcrypt (compatível com Java BCryptPasswordEncoder)
        """
        hashed = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt())
        self.senha = hashed.decode('utf-8')

    def check_password(self, raw_password):
        """
        Verifica senha usando bcrypt (compatível com Java BCryptPasswordEncoder)
        """
        return bcrypt.checkpw(
            raw_password.encode('utf-8'), 
            self.senha.encode('utf-8')
        )

    def __str__(self):
        return f"{self.nome} ({self.email})"


# ============================================================================
# PACIENTES E AGENDAMENTOS (migrado do MS Agendamentos)
# ============================================================================

class Paciente(models.Model):
    """
    Model de Paciente
    Migrado de: org.codelab.graacc.Agendamentos.entity.PatientEntity
    """
    id_paciente = models.BigAutoField(primary_key=True)
    nome = models.CharField(max_length=255, unique=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'paciente'
        verbose_name = 'Paciente'
        verbose_name_plural = 'Pacientes'

    def __str__(self):
        return self.nome


class Agendamento(models.Model):
    """
    Model de Agendamento
    Migrado de: org.codelab.graacc.Agendamentos.entity.AppointmentEntity
    """
    id_agendamento = models.BigAutoField(primary_key=True)
    titulo = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255)
    data = models.DateTimeField()
    local = models.CharField(max_length=100)
    medico = models.CharField(max_length=255, null=True, blank=True)
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_paciente',
        related_name='agendamentos'
    )
    lembrete_enviado = models.BooleanField(default=False)

    class Meta:
        db_table = 'agendamento'
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'
        indexes = [
            models.Index(fields=['data']),
            models.Index(fields=['paciente']),
        ]
        ordering = ['data']

    def __str__(self):
        return f"{self.titulo} - {self.data.strftime('%d/%m/%Y %H:%M')}"


# ============================================================================
# NOTIFICAÇÕES (migrado do MS Notificações)
# ============================================================================

class Notificacao(models.Model):
    """
    Model de Notificação
    Migrado de: org.codelab.graacc.Notificacoes.entity.NotificationEntity
    """
    id_notificacao = models.BigAutoField(primary_key=True)
    id_agendamento = models.BigIntegerField()
    data = models.DateTimeField()
    lida = models.BooleanField(default=False)
    mensagem = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'notificacao'
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        indexes = [
            models.Index(fields=['id_agendamento']),
            models.Index(fields=['data']),
            models.Index(fields=['lida']),
        ]
        ordering = ['data']

    def __str__(self):
        return f"Notificação {self.id_notificacao} - Agendamento {self.id_agendamento}"
