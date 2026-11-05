# Testes - app `restfull`

Esta pasta reúne a suíte de testes automatizados do app `restfull`, usando
`pytest` + `pytest-django`.

## 📁 Organização

```
restfull/
└── tests/
    ├── __init__.py
    ├── conftest.py              # Fixtures compartilhadas (clientes, usuários, tokens JWT, etc.)
    ├── test_auth.py             # Autenticação: registro/login de usuários e admins
    ├── test_patients.py         # Endpoints de cadastro/busca (domínio responsável/paciente)
    ├── test_appointments.py     # CRUD de agendamentos
    └── test_notifications.py    # Criação, listagem e leitura de notificações
```

Os arquivos foram movidos da raiz do app (`restfull/`) para esta pasta
`restfull/tests/` para separar código de produção de código de teste. Por isso,
os imports internos usam o nível de pacote pai:

```python
from ..models import Usuario, Agendamento, Notificacao, Role
```

## ▶️ Como executar

A configuração do pytest fica em `agendinha/pytest.ini`
(`DJANGO_SETTINGS_MODULE = core.settings`, `testpaths = restfull`). Rode a partir
do diretório `agendinha/`:

```bash
cd agendinha

# Toda a suíte
pytest

# Um arquivo específico
pytest restfull/tests/test_auth.py

# Um teste específico
pytest restfull/tests/test_auth.py::TestUserLogin::test_login_success
```

O pytest descobre os testes recursivamente a partir de `testpaths`, então a
subpasta `tests/` é encontrada automaticamente.

## ⚠️ Estado atual da suíte (importante)

> Esta reorganização foi **apenas estrutural** (mover arquivos + ajustar imports).
> Nenhuma lógica de teste foi alterada.

A suíte está **desatualizada em relação ao modelo de dados atual** e, no estado
em que se encontra, **não passa**. Os principais descompassos identificados:

| Testes esperam | Código atual (`models.py` / `urls.py`) |
|----------------|-----------------------------------------|
| Model `Paciente` | Model `Responsavel` |
| Campo `usuario.id_paciente` | FK `usuario.responsavel` (coluna `id_responsavel`) |
| Campo `agendamento.paciente` | FK `agendamento.usuario` |
| Rotas `patient-*` e `user-register-patient-id` | Rotas `responsaveis/*`; não existe registro por ID de paciente |
| Claim JWT `idPaciente` | Token atual não usa esse claim |

### O que precisa ser feito (follow-up, fora do escopo desta mudança)

Para reabilitar a suíte, será necessário atualizar os testes e as fixtures para
o domínio atual:

1. `conftest.py`: trocar `Paciente` por `Responsavel`, ajustar fixtures `user`,
   `admin`, `agendamento` (usar `responsavel`/`usuario`) e os payloads de token.
2. `test_patients.py`: migrar para os endpoints `responsaveis/*` e o model
   `Responsavel`.
3. `test_auth.py`: remover/atualizar os casos de `user-register-patient-id` e o
   uso de `id_paciente`.
4. `test_appointments.py` e `test_notifications.py`: ajustar vínculos para
   `usuario` conforme os models atuais.

Recomenda-se tratar essa atualização como uma tarefa própria, validada rodando
`pytest` em um ambiente com Python e PostgreSQL configurados.
