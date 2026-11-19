# Cantinho do Pastel — Consulta de Cardápio

Projeto Integrador III-A do curso de Análise e Desenvolvimento de Sistemas (ADS) da
Pontifícia Universidade Católica de Goiás (PUC Goiás).

Aplicação cliente-servidor para consulta do cardápio da pastelaria **Cantinho do Pastel**:

- o **atendente** consulta itens, preços, ingredientes e se a loja está aberta;
- o **dono** entra numa área protegida por senha para editar o cardápio, marcar itens
  como esgotados e atualizar os dados e horários da loja.

## Arquitetura

```
Navegador ──HTTP──► web.py (http.server, é o CLIENTE) ──socket + TLS──► servidor.py ──► dados/*.json
```

- **Navegador**: páginas HTML/CSS/JS puras (`static/`).
- **web.py**: serve as páginas e repassa os pedidos do navegador (`POST /api`) ao servidor,
  usando `cliente.py`. Só deixa passar as ações de uma lista permitida.
- **servidor.py**: recebe pedidos por socket TCP com TLS, executa a ação e responde.
- **protocolo.py**: cada mensagem é um JSON precedido de 4 bytes com o tamanho.
- **dados/**: o cardápio e os dados da loja ficam em arquivos JSON.

## Requisitos

- Python 3.11 ou mais novo
- Biblioteca `cryptography` (só para gerar o certificado TLS) — instalada pelo `requirements.txt`

Todo o resto usa apenas a biblioteca padrão do Python. Não há frameworks web nem bibliotecas JavaScript.

## Como rodar (passo a passo)

No Windows (PowerShell), dentro da pasta do projeto:

1. Criar e ativar o ambiente virtual:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
2. Instalar as dependências:
   ```powershell
   pip install -r requirements.txt
   ```
3. Gerar o certificado TLS (cria `certs/servidor.crt` e `certs/servidor.key`):
   ```powershell
   python gerar_certificado.py
   ```
4. Definir a senha da área do dono (mínimo 8 caracteres; grava só o hash em `dados/admin.json`):
   ```powershell
   python definir_senha.py
   ```
5. Em um terminal, subir o servidor:
   ```powershell
   python servidor.py
   ```
6. Em outro terminal (com o `.venv` ativado), subir a interface web:
   ```powershell
   python web.py
   ```
7. Abrir no navegador:
   - Tela do atendente: <http://127.0.0.1:8080>
   - Área do dono: <http://127.0.0.1:8080/admin>

## Medidas de segurança

| Medida | Onde |
|---|---|
| Comunicação web.py ↔ servidor criptografada com **TLS** (mínimo 1.2; na prática negocia **TLS 1.3**) | `servidor.py`, `cliente.py` |
| O cliente **verifica o certificado** do servidor e o nome `localhost` antes de enviar qualquer dado | `cliente.py` |
| **Allowlist de campos públicos**: o atendente nunca recebe custo nem fornecedor | `servidor.py` (`CAMPOS_PUBLICOS`) |
| **Allowlist de ações** aceitas pela interface web | `web.py` (`ACOES_PERMITIDAS`) |
| Senha guardada como **hash PBKDF2-SHA256 com salt** (600 mil iterações), nunca em texto puro; comparação em tempo constante | `seguranca.py` |
| **Token de sessão** aleatório com **expiração** (2 horas); logout invalida o token | `seguranca.py`, `admin.py` |
| **Bloqueio após 5 tentativas** de senha erradas (5 minutos) | `seguranca.py` |
| Ações restritas exigem login (decorador `@exige_login`) | `admin.py` |
| **Validação de entrada**: tipos, tamanhos, faixa de preço, formato de horário | `admin.py` |
| **Gravação atômica**: grava num arquivo temporário e troca de lugar, sem corromper os dados | `admin.py` |
| **Logs sem senha nem token** (aparecem como `***`) | `servidor.py`, `admin.py` (`mascarar`) |
| Proteção contra **path traversal**: só serve arquivos que estão diretamente em `static/` | `web.py` |
| Proteção contra **XSS**: a tela é montada com `createElement`/`textContent`, nunca `innerHTML` com dados | `static/app.js`, `static/admin.js` |
| **Content-Security-Policy** `default-src 'self'` (bloqueia scripts inline e de outros sites), além de `X-Content-Type-Options` e `Referrer-Policy` | `web.py` |
| Limite de tamanho das mensagens e do corpo das requisições | `protocolo.py`, `web.py` |
| Certificado, chave privada e hash da senha **fora do Git** | `.gitignore` |

## Estrutura de pastas

```
.
├── servidor.py           # servidor TLS: ações públicas + ações do dono
├── admin.py              # login, logout e ações restritas (editar cardápio e loja)
├── seguranca.py          # hash de senha, sessões e bloqueio de tentativas
├── cliente.py            # consultar(pedido): conversa com o servidor via TLS
├── web.py                # interface web (http.server) e rota /api
├── protocolo.py          # mensagens JSON com prefixo de tamanho
├── config.py             # endereços, portas e caminhos
├── gerar_certificado.py  # gera o certificado TLS autoassinado
├── definir_senha.py      # define a senha do dono
├── requirements.txt
├── dados/
│   ├── cardapio.json     # itens do cardápio
│   ├── loja.json         # nome, contato, horários e pagamentos
│   └── admin.json        # hash da senha (gerado, fora do Git)
├── certs/                # certificado e chave (gerados, fora do Git)
└── static/
    ├── index.html, app.js      # tela do atendente
    ├── admin.html, admin.js    # área do dono
    └── estilo.css
```
