from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from restfull.models import Agendamento, Notificacao
from restfull.services import WhatsAppService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Envia lembretes de consulta via WhatsApp para pacientes com consultas agendadas para amanhã.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando envio de lembretes...'))
        
        # Define o intervalo de "amanhã"
        amanha = timezone.now().date() + timedelta(days=1)
        
        # Busca agendamentos para amanhã que ainda não tiveram lembrete enviado
        agendamentos = Agendamento.objects.filter(
            data__date=amanha,
            lembrete_enviado=False,
            paciente__isnull=False
        ).select_related('paciente')
        
        if not agendamentos.exists():
            self.stdout.write('Nenhum agendamento pendente para amanhã.')
            return

        whatsapp_service = WhatsAppService()
        sucessos = 0
        falhas = 0

        for agendamento in agendamentos:
            paciente = agendamento.paciente
            
            if not paciente.telefone:
                self.stdout.write(self.style.WARNING(f'Paciente {paciente.nome} não possui telefone cadastrado.'))
                falhas += 1
                continue

            # Formata a mensagem conforme especificação
            horario = timezone.localtime(agendamento.data).strftime('%H:%M')
            doutor = agendamento.medico or "seu médico"
            
            mensagem = (
                f"Olá {paciente.nome}, lembrete de sua consulta amanhã às {horario} com {doutor}."
            )

            # Envia via WhatsApp (WuzAPI)
            sucesso, resultado = whatsapp_service.send_reminder(paciente.telefone, mensagem)

            if sucesso:
                # Atualiza status do agendamento
                agendamento.lembrete_enviado = True
                agendamento.save()
                
                # Cria um log na tabela de Notificações
                Notificacao.objects.create(
                    id_agendamento=agendamento.id_agendamento,
                    data=timezone.now(),
                    lida=False,
                    mensagem=mensagem
                )
                
                self.stdout.write(self.style.SUCCESS(f'Lembrete enviado para {paciente.nome}'))
                sucessos += 1
            else:
                self.stdout.write(self.style.ERROR(f'Falha ao enviar para {paciente.nome}: {resultado}'))
                falhas += 1

        self.stdout.write(self.style.SUCCESS(f'Processo concluído. Sucessos: {sucessos}, Falhas: {falhas}'))
