FROM python:3.12-slim

# Instala dependências do sistema (incluindo cron)
RUN apt-get update && apt-get install -y \
    cron \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos de requisitos e instala as dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do projeto
COPY . .

# Define o diretório de trabalho para onde está o manage.py
WORKDIR /app/graac_backend

# Script para configurar o cron dinamicamente baseado no .env
RUN echo '#!/bin/bash\n\
# Exporta variáveis de ambiente para serem usadas pelo cron\n\
printenv | grep -v "no_proxy" > /etc/environment\n\
echo "$REMINDER_CRON_SCHEDULE root . /etc/environment; cd /app/graac_backend && python3 manage.py send_reminders >> /var/log/cron.log 2>&1" > /etc/cron.d/whatsapp-cron\n\
chmod 0644 /etc/cron.d/whatsapp-cron\n\
touch /var/log/cron.log\n\
service cron start && tail -f /var/log/cron.log' > /app/start-cron.sh && chmod +x /app/start-cron.sh

# Exponha a porta (opcional para o serviço de cron, mas útil para o app)
EXPOSE 8000

# Comando padrão (será sobrescrito no docker-compose para o serviço de cron)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
