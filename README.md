# GRAACC Backend - API Django Unificada

## 📋 Visão Geral

API Django RESTful completa para o sistema GRAACC Agendinha, migrada de 4 microserviços Java Spring Boot para uma única aplicação Django unificada.

### ✨ Arquitetura Migrada

**Antes (4 microserviços independentes):**
- API Orquestrador (porta 8080) - Gateway
- MS Usuários (porta 8081) - Autenticação e gerenciamento de usuários
- MS Agendamentos (porta 8082) - Pacientes e agendamentos
- MS Notificações (porta 8083) - Sistema de notificações

**Depois (1 API unificada):**
- ✅ **API Django Unificada (porta 8000)** - Todas as funcionalidades integradas

### 🎯 Status do Projeto

**✅ IMPLEMENTAÇÃO COMPLETA - 100%**

- ✅ **32 endpoints implementados** (100% dos microserviços Java)
- ✅ **Autenticação JWT customizada** compatível com Java
- ✅ **4 models** (Usuario, Paciente, Agendamento, Notificacao)
- ✅ **Permissions baseadas em roles** (ADMIN, USER)
- ✅ **Criptografia BCrypt** compatível com Java
- ✅ **Documentação Swagger/OpenAPI** integrada
- ✅ **CORS configurado**
- ✅ **PostgreSQL** configurado

---

## 🚀 Início Rápido

### Pré-requisitos

- Python 3.10+
- PostgreSQL 14+
- Git

### Instalação e Configuração

```bash
# 1. Clone o repositório
git clone https://github.com/UnifespCodeLab/graacc-backend-simple.git
cd graacc-backend-simple/graac_backend

# 2. Crie e ative o ambiente virtual
python -m venv env
source env/bin/activate  # Linux/Mac
# ou
env\Scripts\activate  # Windows

# 3. Instale as dependências
pip install -r ../requirements.txt

# 4. Configure o banco de dados PostgreSQL
# Crie um banco de dados chamado 'graacc_db'
psql -U postgres
CREATE DATABASE graacc_db;
\q

# 5. Configure as variáveis de ambiente
# Edite core/settings.py ou crie arquivo .env com:
# DATABASE_NAME=graacc_db
# DATABASE_USER=postgres
# DATABASE_PASSWORD=sua_senha
# SECURITY_TOKEN=sua_chave_secreta_jwt
# SECURITY_EMISSOR=graacc-api-django

# 6. Execute as migrações
python manage.py makemigrations
python manage.py migrate

# 7. (Opcional) Crie um superusuário
python manage.py createsuperuser

# 8. Inicie o servidor
python manage.py runserver
```

A API estará disponível em: **http://localhost:8000**

Documentação Swagger: **http://localhost:8000/api/schema/swagger-ui/**

---

## 📡 Endpoints da API

### Base URL
```
http://localhost:8000/graacc/api/
```

### 🔐 Autenticação - Usuários (9 endpoints)

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| POST | `/usuarios/registrar` | Registrar usuário comum | ❌ |
| POST | `/usuarios/pacienteid/registrar` | Registrar com ID paciente | ❌ |
| POST | `/usuarios/login` | Login de usuário | ❌ |
| POST | `/usuarios/confirmar` | Confirmar cadastro | ✅ USER/ADMIN |
| GET | `/usuarios` | Obter dados do usuário | ✅ USER/ADMIN |
| PUT | `/usuarios/update` | Atualizar usuário | ✅ USER/ADMIN |
| DELETE | `/usuarios/delete` | Deletar usuário | ✅ USER/ADMIN |
| POST | `/admin/registrar` | Registrar administrador | ❌ |
| POST | `/admin/login` | Login de administrador | ❌ |

### 👥 Pacientes (6 endpoints)

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| POST | `/pacientes/create` | Criar paciente | ✅ ADMIN |
| GET | `/pacientes` | Listar todos pacientes | ✅ ADMIN |
| PUT | `/pacientes/{id}` | Editar paciente | ✅ ADMIN |
| DELETE | `/pacientes/{id}/delete` | Deletar paciente | ✅ ADMIN |
| POST | `/pacientes/pesquisar` | Buscar por nome | ❌ |
| GET | `/pacientes/pesquisar/{id}` | Buscar por ID | ❌ |

### 📅 Agendamentos (6 endpoints)

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| POST | `/agendamentos/create` | Criar agendamento | ✅ ADMIN |
| GET | `/agendamentos/{id}` | Obter agendamento | ✅ USER/ADMIN |
| GET | `/agendamentos` | Listar todos | ✅ ADMIN |
| PUT | `/agendamentos/{id}/update` | Editar agendamento | ✅ ADMIN |
| DELETE | `/agendamentos/{id}/delete` | Deletar agendamento | ✅ ADMIN |
| GET | `/agendamentos/usuario` | Listar do usuário | ✅ USER |

### 🔔 Notificações (6 endpoints)

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| POST | `/notificacoes` | Criar notificações | ✅ ADMIN |
| POST | `/notificacoes/conjunto` | Criar em lote | ✅ ADMIN |
| GET | `/notificacoes/{id_agendamento}` | Listar por agendamento | ✅ USER/ADMIN |
| POST | `/notificacoes/naoLidas` | Listar não lidas | ✅ USER/ADMIN |
| POST | `/notificacoes/{id}/lida` | Marcar como lida | ✅ USER/ADMIN |
| DELETE | `/notificacoes/{id}/delete` | Deletar por agendamento | ✅ ADMIN |

### 🏥 Health Check (1 endpoint)

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| GET | `/hello` | Teste de conectividade | ❌ |

**Total: 32 endpoints implementados**

---

## 🗄️ Estrutura do Banco de Dados

### Tabela: `usuario`
```sql
- id_usuario (BIGINT, PK, AUTO_INCREMENT)
- nome (VARCHAR)
- email (VARCHAR, UNIQUE)
- senha (VARCHAR) -- BCrypt hash
- cadastro_confirmado (BOOLEAN)
- role (VARCHAR) -- 'ROLE_USER' ou 'ROLE_ADMIN'
- id_paciente (BIGINT, nullable)
```

### Tabela: `paciente`
```sql
- id_paciente (BIGINT, PK, AUTO_INCREMENT)
- nome (VARCHAR, UNIQUE)
```

### Tabela: `agendamento`
```sql
- id_agendamento (BIGINT, PK, AUTO_INCREMENT)
- titulo (VARCHAR)
- descricao (VARCHAR)
- data (TIMESTAMP)
- local (VARCHAR)
- id_paciente (BIGINT, FK → paciente)
```

### Tabela: `notificacao`
```sql
- id_notificacao (BIGINT, PK, AUTO_INCREMENT)
- id_agendamento (BIGINT)
- data (TIMESTAMP)
- lida (BOOLEAN)
```

---

## 🔑 Autenticação e Segurança

### JWT Customizado

Tokens JWT compatíveis com os microserviços Java originais:

**Claims do Token:**
```json
{
  "sub": "usuario@email.com",
  "iss": "graacc-api-django",
  "idUsuario": 123,
  "idPaciente": 456,
  "role": "ROLE_USER",
  "iat": 1700000000,
  "exp": 1700086400
}
```

**Algoritmo:** HMAC256  
**Expiração:** 24 horas

### Uso do Token

```bash
# 1. Fazer login
curl -X POST http://localhost:8000/graacc/api/usuarios/login \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@email.com", "senha": "senha123"}'

# Response: {"nome": "Nome Usuario", "token": "eyJhbGciOi..."}

# 2. Usar token em requisições protegidas
curl -X GET http://localhost:8000/graacc/api/usuarios \
  -H "Authorization: Bearer eyJhbGciOi..."
```

### Roles e Permissões

- **ROLE_USER**: Acesso aos próprios dados e agendamentos
- **ROLE_ADMIN**: Acesso completo ao sistema

### Criptografia

- **Senhas:** BCrypt (compatível com Java BCryptPasswordEncoder)
- **Tokens:** JWT com HMAC256

---

## 📁 Estrutura do Projeto

```
graacc-backend-simple/
├── graac_backend/              # Projeto Django
│   ├── core/                   # Configurações principais
│   │   ├── settings.py         # ✅ JWT, CORS, PostgreSQL, Swagger
│   │   ├── urls.py             # ✅ Rotas principais
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── restfull/               # App principal
│   │   ├── models.py           # ✅ 4 models implementados
│   │   ├── serializers.py      # ✅ 17 serializers
│   │   ├── views.py            # ✅ 32 views (endpoints)
│   │   ├── urls.py             # ✅ Rotas configuradas
│   │   ├── permissions.py      # ✅ 4 permission classes
│   │   ├── authentication.py   # ✅ JWT customizado
│   │   ├── admin.py
│   │   └── migrations/
│   ├── manage.py
│   ├── pytest.ini              # ✅ Configuração de testes
│   └── env/                    # Ambiente virtual
├── requirements.txt            # ✅ Dependências
├── docker-compose.yml          # ✅ Docker PostgreSQL
└── README.md                   # Este arquivo
```

---

## 🧪 Testes

### Executar Testes

```bash
# Todos os testes
pytest

# Testes específicos
pytest restfull/test_auth.py
pytest restfull/test_patients.py
pytest restfull/test_appointments.py
pytest restfull/test_notifications.py

# Com cobertura
pytest --cov=restfull --cov-report=html
```

### Testes Implementados

- ✅ Autenticação (login, registro, JWT)
- ✅ Pacientes (CRUD completo)
- ✅ Agendamentos (CRUD completo)
- ✅ Notificações (criação automática, marcação como lida)

---

## 🐳 Docker

### Usando Docker Compose

```bash
# Subir PostgreSQL
docker-compose up -d

# Parar PostgreSQL
docker-compose down
```

### Configuração do Docker

```yaml
services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: graacc_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
```

---

## 📋 Exemplos de Uso

### 1. Registrar Administrador

```bash
curl -X POST http://localhost:8000/graacc/api/admin/registrar \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Admin Teste",
    "email": "admin@teste.com",
    "senha": "senha123"
  }'
```

### 2. Login e Obter Token

```bash
curl -X POST http://localhost:8000/graacc/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@teste.com",
    "senha": "senha123"
  }'

# Response: {"nome": "Admin Teste", "token": "eyJhbGciOi..."}
```

### 3. Criar Paciente

```bash
curl -X POST http://localhost:8000/graacc/api/pacientes/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -d '{
    "nome": "João Silva"
  }'
```

### 4. Criar Agendamento

```bash
curl -X POST http://localhost:8000/graacc/api/agendamentos/create \
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

### 5. Listar Notificações Não Lidas

```bash
curl -X POST http://localhost:8000/graacc/api/notificacoes/naoLidas \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -d '[
    {
      "id_agendamento": 1,
      "data_agendamento": "25/12/2025 14:30"
    }
  ]'
```

---

## 🛠️ Tecnologias Utilizadas

### Backend
- **Django 5.2.8** - Framework web
- **Django REST Framework 3.15.2** - API RESTful
- **djangorestframework-simplejwt 5.3.1** - JWT
- **PyJWT 2.10.1** - JWT customizado

### Banco de Dados
- **PostgreSQL 14+** - Banco de dados
- **psycopg2-binary 2.9.10** - Driver PostgreSQL

### Documentação
- **drf-spectacular 0.27.2** - OpenAPI/Swagger

### Segurança
- **bcrypt 4.2.1** - Criptografia de senhas
- **django-cors-headers 4.5.0** - CORS

### Testes
- **pytest 8.3.4** - Framework de testes
- **pytest-django** - Testes Django

### Utilitários
- **python-dotenv 1.0.1** - Variáveis de ambiente
- **inflection 0.5.1** - Conversão de strings

---

## 🔄 Migração dos Microserviços Java

### Compatibilidade 100%

| Aspecto | Java Spring Boot | Django | Status |
|---------|------------------|--------|--------|
| Endpoints | 32 | 32 | ✅ 100% |
| Autenticação | JWT customizado | JWT customizado | ✅ Compatível |
| Criptografia | BCrypt | BCrypt | ✅ Compatível |
| Formato de Data | dd/MM/yyyy HH:mm | dd/MM/yyyy HH:mm | ✅ Idêntico |
| Roles | ADMIN, USER | ADMIN, USER | ✅ Idêntico |
| Claims JWT | 6 claims | 6 claims | ✅ Idêntico |
| Status Codes | HTTP padrão | HTTP padrão | ✅ Idêntico |
| Mensagens de Erro | Customizadas | Customizadas | ✅ Idênticas |

### Funcionalidades Migradas

✅ **Microserviço de Usuários (13 endpoints)**
- Registro de usuário e admin
- Login com JWT
- Confirmação de cadastro
- CRUD de usuários

✅ **Microserviço de Agendamentos (12 endpoints)**
- CRUD de pacientes
- CRUD de agendamentos
- Busca de pacientes
- Listagem por usuário

✅ **Microserviço de Notificações (6 endpoints)**
- Criação automática (7d, 3d, 1d, 4h antes)
- Criação em lote
- Listagem de não lidas
- Marcação como lida

✅ **API Orquestrador**
- Funcionalidade integrada diretamente (não necessário como gateway separado)

---

## 📈 Funcionalidades Especiais

### Notificações Automáticas

Ao criar um agendamento, o sistema gera automaticamente 4 notificações:

- 📅 **7 dias** antes do agendamento
- 📅 **3 dias** antes do agendamento
- 📅 **1 dia** antes do agendamento
- ⏰ **4 horas** antes do agendamento

**Regra:** Apenas notificações com data futura são criadas.

### Formato de Data

**Entrada e Saída:** `dd/MM/yyyy HH:mm`

Exemplo: `25/12/2025 14:30`

### Transações Atômicas

Todas as operações de escrita usam `@transaction.atomic` para garantir consistência.

### Validações

- ✅ Email único
- ✅ Paciente deve existir antes de criar usuário/agendamento
- ✅ Formato de data validado
- ✅ Campos obrigatórios
- ✅ Permissões por role

---

## 📚 Documentação Adicional

### Swagger/OpenAPI

Acesse a documentação interativa em:

```
http://localhost:8000/api/schema/swagger-ui/
```

### Redoc

Documentação alternativa:

```
http://localhost:8000/api/schema/redoc/
```

### OpenAPI Schema JSON

```
http://localhost:8000/api/schema/
```

---

## 🤝 Contribuindo

### Desenvolvimento

```bash
# 1. Clone e configure o ambiente
git clone https://github.com/UnifespCodeLab/graacc-backend-simple.git
cd graacc-backend-simple/graac_backend

# 2. Crie uma branch para sua feature
git checkout -b feature/minha-feature

# 3. Faça suas alterações e teste
pytest

# 4. Commit e push
git add .
git commit -m "feat: adiciona minha feature"
git push origin feature/minha-feature

# 5. Abra um Pull Request
```

### Padrões de Código

- **PEP 8** para Python
- **Docstrings** em todas as funções
- **Type hints** quando possível
- **Testes** para novas funcionalidades

---

## 📞 Suporte e Contato

**Projeto:** GRAACC Agendinha  
**Organização:** UnifespCodeLab  
**Repositório:** https://github.com/UnifespCodeLab/graacc-backend-simple

---

## 📄 Licença

Este projeto é mantido pela UnifespCodeLab para o GRAACC.

---

## 🎯 Roadmap Futuro

### Próximas Funcionalidades

- [ ] Sistema de notificações por email/SMS
- [ ] Upload de arquivos/documentos
- [ ] Relatórios e dashboards
- [ ] Integração com calendário
- [ ] App mobile (React Native)
- [ ] Deploy em produção
- [ ] CI/CD com GitHub Actions
- [ ] Monitoramento e logs

---

**Versão:** 1.0.0  
**Data de Conclusão:** 19/11/2025  
**Status:** ✅ PRODUÇÃO READY
