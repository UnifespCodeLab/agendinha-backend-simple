# Agendinha Backend - API Django

## 📋 Visão Geral

API Django RESTful para o sistema Agendinha, responsável pelo gerenciamento de usuários, responsáveis, agendamentos e notificações. A aplicação é uma única API Django unificada (originalmente migrada de microserviços Java Spring Boot).

### 🧩 Principais Funcionalidades

- Autenticação JWT customizada e login via Google OAuth2
- Gerenciamento de usuários (comum e administrador)
- Cadastro e busca de responsáveis
- CRUD de agendamentos
- Notificações automáticas e push (Web Push / VAPID)
- Documentação Swagger/OpenAPI integrada
- CORS configurado e banco PostgreSQL

---

## 🚀 Início Rápido

### Pré-requisitos

- Python 3.10+ (a imagem Docker usa Python 3.12)
- PostgreSQL 14+
- Git

### Instalação e Configuração

```bash
# 1. Clone o repositório
git clone https://github.com/UnifespCodeLab/agendinha-backend-simple.git
cd agendinha-backend-simple

# 2. Crie e ative o ambiente virtual
python -m venv env
source env/bin/activate  # Linux/Mac
# ou
env\Scripts\activate     # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure o banco de dados PostgreSQL
# Crie um banco de dados chamado 'agendinha_db'
psql -U postgres
CREATE DATABASE agendinha_db;
\q

# 5. Configure as variáveis de ambiente
# Copie o arquivo de exemplo e preencha os valores
cp .env.example .env

# 6. Entre no diretório do projeto Django e execute as migrações
cd agendinha
python manage.py makemigrations
python manage.py migrate

# 7. (Opcional) Crie um superusuário
python manage.py createsuperuser

# 8. Inicie o servidor
python manage.py runserver
```

A API estará disponível em: **http://localhost:8000**

Documentação Swagger: **http://localhost:8000/api/docs/**

---

## 📡 Endpoints da API

### Base URL
```
http://localhost:8000/agendinha/api/
```

> Os endpoints abaixo refletem as rotas definidas em `agendinha/restfull/urls.py`.

### 🏥 Health Check

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/hello` | Teste de conectividade |

### 🔐 Usuários

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/usuarios/registrar` | Registrar usuário |
| POST | `/usuarios/login` | Login de usuário |
| POST | `/usuarios/login/google` | Login via Google OAuth2 |
| POST | `/usuarios/confirmar` | Confirmar cadastro |
| POST | `/usuarios/confirmar-redefinir-senha` | Confirmar e redefinir senha |
| GET | `/usuarios/<id>` | Buscar usuário por ID |
| POST | `/usuarios/foto` | Atualizar avatar do usuário |
| POST | `/usuarios/email/redefinir-senha` | Solicitar redefinição de senha por e-mail |
| POST | `/usuarios/redefinir-senha` | Redefinir senha |
| GET | `/usuarios` | Obter dados do usuário |
| GET | `/usuarios/pesquisar` | Buscar usuário por nome |
| PUT | `/usuarios/update` | Atualizar usuário |
| DELETE | `/usuarios/delete` | Deletar usuário |

### 👤 Admin

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/admin/registrar` | Registrar administrador |
| POST | `/admin/usuarios/registrar` | Admin registra usuário |
| POST | `/admin/login` | Login de administrador |

### 👥 Responsáveis

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/responsaveis` | Listar responsáveis (ADMIN) |
| POST | `/responsaveis/create` | Criar responsável |
| POST | `/responsaveis/pesquisar` | Buscar por nome |
| GET | `/responsaveis/pesquisar/<id>` | Buscar por ID |
| PUT | `/responsaveis/<id>` | Editar responsável |
| DELETE | `/responsaveis/<id>/delete` | Deletar responsável |

### 📅 Agendamentos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/agendamentos` | Listar todos (ADMIN) |
| POST | `/agendamentos/create` | Criar agendamento |
| GET | `/agendamentos/<id>` | Obter agendamento |
| PUT | `/agendamentos/<id>/update` | Editar agendamento |
| DELETE | `/agendamentos/<id>/delete` | Deletar agendamento |
| GET | `/agendamentos/usuario` | Listar do usuário |
| POST | `/agendamentos/google` | Exportar para o Google Calendar |

### 🔔 Notificações

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/notificacoes` | Criar notificação |
| POST | `/notificacoes/conjunto` | Criar em lote |
| GET | `/notificacoes/<id_agendamento>` | Listar por agendamento |
| GET | `/notificacoes/usuario/<id_usuario>` | Listar por usuário |
| GET | `/notificacoes/id/<id_notificacao>` | Deletar por ID |
| POST | `/notificacoes/naoLidas` | Listar não lidas |
| POST | `/notificacoes/<id_notificacao>/lida` | Marcar como lida |
| DELETE | `/notificacoes/<id_agendamento>/delete` | Deletar por agendamento |

### 🔔 Push / Inscrições

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/salvar-inscricao` | Salvar inscrição de push notification |

### 🖥️ Páginas HTML (templates)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/criar-responsavel` | Página para criar responsável |
| GET | `/criar-agendamento` | Página para criar agendamento |
| GET | `/criar-notificacao` | Página para criar notificação |

---

## 🗄️ Estrutura do Banco de Dados

Modelos definidos em `agendinha/restfull/models.py`.

### Tabela: `usuario`
- `id_usuario` (BIGINT, PK)
- `nome`, `email`, `cpf` (único)
- `senha` (BCrypt hash)
- `cadastro_confirmado` (BOOLEAN)
- `id_responsavel` (FK → responsavel, nullable)
- `role` (`ROLE_USER` ou `ROLE_ADMIN`)
- `foto_perfil`, `modo_google`, `timeout_seconds`, `ativar_notificacoes_consultas`

### Tabela: `responsavel`
- `id_responsavel` (BIGINT, PK)
- `nome`
- `telefone` (único)

### Tabela: `agendamento`
- `id_agendamento` (BIGINT, PK)
- `titulo`, `descricao`, `data` (TIMESTAMP), `local`, `medico`
- `id_usuario` (FK → usuario, nullable)
- `lembrete_enviado` (BOOLEAN)

### Tabela: `notificacao`
- `id_notificacao` (BIGINT, PK)
- `id_agendamento` (BIGINT)
- `data` (TIMESTAMP), `lida` (BOOLEAN)
- `titulo`, `descricao`
- `id_usuario` (FK → usuario, nullable)

### Tabela: `pushsubscription`
- `id` (PK)
- `id_usuario` (FK → usuario, nullable)
- `endpoint`, `p256dh`, `auth`

---

## 🔑 Autenticação e Segurança

### JWT Customizado

A autenticação customizada fica em `agendinha/restfull/authentication.py`. Configurações de token em `SIMPLE_JWT` (`core/settings.py`):

- **Algoritmo:** HS256
- **Expiração do access token:** 24 horas
- **Expiração do refresh token:** 7 dias

### Uso do Token

```bash
# 1. Fazer login
curl -X POST http://localhost:8000/agendinha/api/usuarios/login \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@email.com", "senha": "senha123"}'

# 2. Usar token em requisições protegidas
curl -X GET http://localhost:8000/agendinha/api/usuarios \
  -H "Authorization: Bearer SEU_TOKEN"
```

### Roles e Permissões

- **ROLE_USER**: acesso aos próprios dados e agendamentos
- **ROLE_ADMIN**: acesso completo ao sistema

### Criptografia

- **Senhas:** BCrypt
- **Tokens:** JWT com HS256

---

## 📁 Estrutura do Projeto

```
agendinha-backend-simple/
├── agendinha/                   # Projeto Django
│   ├── core/                    # Configurações principais
│   │   ├── settings.py          # JWT, CORS, PostgreSQL, Swagger, OAuth2
│   │   ├── urls.py              # Rotas raiz + documentação
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── restfull/                # App principal
│   │   ├── models.py            # Models (Usuario, Responsavel, Agendamento, Notificacao, PushSubscription)
│   │   ├── serializers/         # Serializers por domínio
│   │   ├── views/               # Views por domínio
│   │   ├── urls.py              # Rotas da API
│   │   ├── permissions.py       # Permission classes
│   │   ├── authentication.py    # JWT customizado
│   │   ├── services.py          # Lógica de serviços (e-mail, etc.)
│   │   ├── schema.py
│   │   ├── admin.py
│   │   ├── migrations/
│   │   └── test_*.py            # Testes
│   ├── templates/               # Templates HTML
│   ├── static/                  # Arquivos estáticos
│   ├── manage.py
│   └── pytest.ini               # Configuração de testes
├── requirements.txt             # Dependências
├── Dockerfile                   # Imagem da aplicação
├── docker-compose.yml           # PostgreSQL + API + Cron
├── .env.example                 # Modelo de variáveis de ambiente
└── README.md                    # Este arquivo
```

---

## 🧪 Testes

Os testes usam `pytest` + `pytest-django` (configuração em `agendinha/pytest.ini`)
e ficam em `agendinha/restfull/tests/`. Veja detalhes em
[`agendinha/restfull/tests/README.md`](agendinha/restfull/tests/README.md).

```bash
# A partir do diretório agendinha/
cd agendinha

# Todos os testes
pytest

# Testes específicos
pytest restfull/tests/test_auth.py
pytest restfull/tests/test_patients.py
pytest restfull/tests/test_appointments.py
pytest restfull/tests/test_notifications.py
```

> ⚠️ A suíte está desatualizada em relação ao modelo de dados atual
> (`Responsavel` em vez de `Paciente`) e no momento não passa. A reorganização
> em `tests/` foi apenas estrutural; a atualização dos testes está documentada
> como follow-up no README da pasta de testes.

---

## 🐳 Docker

O `docker-compose.yml` define três serviços: `postgres`, `api` e `cron`.

```bash
# Subir todos os serviços
docker-compose up -d

# Parar os serviços
docker-compose down
```

As variáveis de ambiente são lidas do arquivo `.env` (veja `.env.example`).

---

## 📋 Exemplos de Uso

### 1. Registrar Administrador

```bash
curl -X POST http://localhost:8000/agendinha/api/admin/registrar \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Admin Teste",
    "email": "admin@teste.com",
    "senha": "senha123"
  }'
```

### 2. Login e Obter Token

```bash
curl -X POST http://localhost:8000/agendinha/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@teste.com",
    "senha": "senha123"
  }'
```

### 3. Criar Responsável

```bash
curl -X POST http://localhost:8000/agendinha/api/responsaveis/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -d '{
    "nome": "João Silva",
    "telefone": "11999999999"
  }'
```

### 4. Criar Agendamento

```bash
curl -X POST http://localhost:8000/agendinha/api/agendamentos/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -d '{
    "titulo": "Consulta Pediátrica",
    "descricao": "Dr. Carlos",
    "data": "25/12/2025 14:30",
    "local": "Sala 3",
    "nome_completo_paciente": "João Silva"
  }'
```

---

## 🛠️ Tecnologias Utilizadas

### Backend
- **Django 5.2.8** / **Django REST Framework 3.15.2**
- **djangorestframework-simplejwt 5.3.1** / **PyJWT 2.10.1**

### Banco de Dados
- **PostgreSQL** / **psycopg2-binary 2.9.10**

### Documentação
- **drf-spectacular 0.27.2** (OpenAPI/Swagger)

### Segurança
- **bcrypt 4.2.1** / **django-cors-headers 4.5.0**

### Integrações
- **django-allauth 65.14.3** + **google-auth** / **google-api-python-client** (Google OAuth2 e Calendar)
- **pywebpush 2.3.0** (Web Push / VAPID)

### Testes
- **pytest-django 4.9.0**

---

## 📚 Documentação Adicional

| Recurso | URL |
|---------|-----|
| Swagger UI | `http://localhost:8000/api/docs/` |
| ReDoc | `http://localhost:8000/api/redoc/` |
| OpenAPI Schema | `http://localhost:8000/api/schema/` |

---

## 🤝 Contribuindo

```bash
# 1. Crie uma branch para sua feature
git checkout -b feature/minha-feature

# 2. Faça suas alterações e teste
cd agendinha && pytest

# 3. Commit e push
git add .
git commit -m "feat: adiciona minha feature"
git push origin feature/minha-feature

# 4. Abra um Pull Request
```

### Padrões de Código

- **PEP 8** para Python
- **Docstrings** em funções relevantes
- **Testes** para novas funcionalidades

---

## 📞 Suporte e Contato

**Projeto:** Agendinha
**Organização:** UnifespCodeLab
**Repositório:** https://github.com/UnifespCodeLab/agendinha-backend-simple

---

## 📄 Licença

Este projeto é mantido pela UnifespCodeLab.
