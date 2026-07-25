from django.db import models
import bcrypt
import time
from django.utils.crypto import constant_time_compare
import hmac
import hashlib
from django.conf import settings
from requests import get
from django.core.files.temp import NamedTemporaryFile
import os
from django.core.files import File

class Role(models.TextChoices):
    """Enum para roles de usuário (compatível com Java)"""
    USER = 'ROLE_USER', 'User'
    ADMIN = 'ROLE_ADMIN', 'Admin'


class Usuario(models.Model):
    """
    Model de Usuário
    """
    id_usuario = models.BigAutoField(primary_key=True) # ✅ Restaurado!
    email = models.EmailField(unique=True)
    senha = models.CharField(max_length=255, blank=True)
    cadastro_confirmado = models.BooleanField(default=False)
    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.USER
    )
    foto_perfil = models.ImageField(upload_to='images/', null=True, blank=True)
    modo_google = models.BooleanField(default=False, null=False)
    timeout_seconds = models.BigIntegerField(blank=True, default=10000)
    ativar_notificacoes_consultas = models.BooleanField(default=True, null=False)
    ativar_notificacoes_agendinha = models.BooleanField(default=True, null=False)
    def make_token(self) -> str:
        timestamp = int(time.time())
        hash_value = self._make_hash(timestamp)
        return f"{timestamp}-{hash_value}"

    def check_token(self, token: str) -> bool:
        try:
            timestamp_str, hash_value = token.split("-")
            timestamp = int(timestamp_str)
        except ValueError:
            return False

        # Check expiration
        if (time.time() - timestamp) > self.timeout_seconds:
            return False

        expected_hash = self._make_hash(timestamp)

        return constant_time_compare(expected_hash, hash_value)

    def _make_hash(self, timestamp: int) -> str:
        """
        Build secure hash based on user state.
        If any of these fields change → token invalid.
        """
        value = (
            str(self.id_usuario) +
            str(self.senha) +
            str(self.cadastro_confirmado) +
            str(self.role) +
            str(timestamp)
        )

        return hmac.new(
            key=settings.SECRET_KEY.encode(),
            msg=value.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

    class Meta:
        db_table = 'usuario'
        indexes = [
            models.Index(fields=['email']),
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

    def save_image_from_url(self, url):
        """Fetches and saves an image from a URL."""
        if url:
            response = get(url)
            if response.status_code == 200:
                img_temp = NamedTemporaryFile(delete=True)
                img_temp.write(response.content)
                img_temp.flush()
                self.foto_perfil.save(os.path.basename(url), File(img_temp), save=True)

class Paciente(models.Model):
    queixa_principal = models.CharField(max_length=255, blank=True)
    endereco = models.CharField(max_length=255, blank=True)
    bairro = models.CharField(max_length=255, blank=True)
    cep = models.CharField(max_length=255, blank=True)
    nome = models.CharField(max_length=255)
    responsavel = models.ForeignKey(
        'Responsavel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_responsavel',
        related_name='usuarios'
    )
    rg = models.CharField(max_length=10, blank=True)
    cpf = models.CharField(max_length=11, blank=True)
    telefone = models.CharField(max_length=11, blank=True)

class Responsavel(models.Model):
    id_responsavel = models.BigAutoField(primary_key=True)
    nome = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, unique=True, blank=True)

class Agendamento(models.Model):
    """
    Model de Agendamento
    """
    id_agendamento = models.BigAutoField(primary_key=True)
    titulo = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255)
    data = models.DateTimeField()
    local = models.CharField(max_length=100)
    medico = models.CharField(max_length=255, null=True, blank=True)
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_usuario',
        related_name='agendamentos'
    )
    lembrete_enviado = models.BooleanField(default=False)

    class Meta:
        db_table = 'agendamento'
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'
        indexes = [
            models.Index(fields=['data']),
            models.Index(fields=['usuario']),
        ]
        ordering = ['data']

    def __str__(self):
        return f"{self.titulo} - {self.data.strftime('%d/%m/%Y %H:%M')}"

class Notificacao(models.Model):
    """
    Model de Notificação
    """
    id_notificacao = models.BigAutoField(primary_key=True)
    id_agendamento = models.BigIntegerField()
    data = models.DateTimeField()
    lida = models.BooleanField(default=False)
    titulo = models.TextField(null=True, blank=True)
    descricao = models.TextField(null=True, blank=True)
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_usuario',
        related_name='notificacoes'
    )

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

class PushSubscription(models.Model):
    usuario = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_usuario',
    )
    endpoint = models.URLField(max_length=255)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)

    class Meta:
        db_table = 'pushsubscription'
        verbose_name = 'PushSubscription'
        verbose_name_plural = 'PushSubscriptions'
