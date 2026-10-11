<div align="center">

# 📸 Echo-Repost
### Autonomous Instagram Reels Pipeline: Local AI Captioning (Ollama) & Official Graph API Publishing

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Web%20Panel-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![AI Engine: Ollama](https://img.shields.io/badge/AI%20Engine-Local%20Ollama%20(Llama%203.2%20%7C%20Qwen)-orange.svg)](https://ollama.com)
[![Publisher: Meta Graph API](https://img.shields.io/badge/Publishing-Official%20Meta%20Graph%20API-4267B2.svg?logo=meta&logoColor=white)](https://developers.facebook.com)
[![Architecture: Clean & SOLID](https://img.shields.io/badge/Architecture-Clean%20Architecture%20%7C%20SOLID-purple.svg)](https://github.com/Kaio-Comk/Echo-Repost)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-yellow.svg)](https://opensource.org/licenses/GPL-3.0)

**Descobre Reels de perfis autorizados, gera legendas originais com IA local (Ollama) e publica 24/7 pela API Oficial do Instagram.**  
*Painel web de aprovação em FastAPI, túnel Cloudflare integrado e renovação automática de tokens OAuth.*

</div>

---

## ⚠️ Aviso de compliance (leia antes)

O sistema combina **dois caminhos** com níveis de risco diferentes:

| Etapa | Como é feito | Oficial? | Risco |
|---|---|---|---|
| **Descoberta + download** dos Reels de outro perfil | `instagrapi` / `instaloader` (API privada, conta logada) | ❌ Não-oficial | Pode violar o ToS da Meta; a conta usada pode ser **limitada/banida** |
| **Publicação** na sua conta | Instagram Content Publishing API (login por Instagram) | ✅ Oficial | Estável; respeita políticas da Meta |

A ingestão de conteúdo de terceiros, mesmo "autorizado", é **responsabilidade sua** perante
a Meta e o autor original. Use uma conta **descartável** para a descoberta/download, nunca a
conta principal. O núcleo (IA, publicação oficial, token, banco) é independente da ingestão.

---

## 🏗️ Fluxo Operacional 24/7

```mermaid
flowchart TD
    Target["🎯 Perfil Alvo (Instagram)"] --> Ingest["📥 Descoberta & Download (Conta Descartável)"]
    Ingest --> Dedup{"Reel já publicado?"}
    Dedup -->|Sim| Skip["⏭️ Ignora duplicata"]
    Dedup -->|Não| Queue["📂 Fila Local (data/queue.txt)"]
    
    Queue --> LocalAI["🤖 IA Local Ollama (Llama 3.2 / Qwen)"]
    LocalAI --> Caption["✍️ Geração de Legenda Original & Hashtags"]
    
    Caption --> Approval{"Requer Aprovação Manual?"}
    Approval -->|Sim| Panel["🖥️ Painel Web FastAPI (Revisão Humana)"]
    Approval -->|Não (Automático)| Publisher
    Panel -->|"Aprovado"| Publisher["🚀 Publicador Oficial Meta Graph API"]
    
    Publisher --> Tunnel["🌐 Túnel Cloudflare (Hospedagem temporária de vídeo)"]
    Tunnel --> Meta["📸 Servidores Meta (Publicação Final no Perfil)"]
    
    subgraph Maintenance ["Serviços em Segundo Plano"]
        TokenWatch["🔑 Token Watcher (Auto-renovação com < 10 dias de expiração)"]
        RateControl["⏱️ Trava de Cadência Segura (Anti-Spam)"]
    end
```

A **descoberta não é mágica**: ela depende da conta logada conseguir listar o feed do alvo
(API privada). Se a conta cair, a fila para de encher — mas você pode alimentar
`data/queue.txt` manualmente a qualquer momento.

---

## 📊 Quantos posts por dia? (cadência segura)

| Nível | Reels/dia | Intervalo (`POLL_INTERVAL_SECONDS`) |
|---|---|---|
| **Limite técnico da API** | 100/24h | — (recusa acima disso) |
| ✅ **Seguro (recomendado)** | 3–6 | `14400` (4h) a `28800` (8h) |
| ⚠️ Agressivo | 7–10 | `8640` (2.4h) a `12342` (3.4h) |
| 🚫 Arriscado (spam/queda de alcance) | 12+ | < `7200` (2h) |

**Importante:** o limite que importa não é o da API (100) e sim a **saúde da conta**. Postar
demais faz o algoritmo reduzir seu alcance e pode marcar a conta como spam — sobretudo em
contas novas. Comece conservador (4–6/dia) e suba aos poucos observando o alcance.

---

## Arquitetura

```
project/
├── app/
│   ├── config/        # settings (pydantic) + estilos de legenda (YAML)
│   ├── models/        # SQLAlchemy 2.0: Profile, Video, Caption, Job
│   ├── repositories/  # acesso a dados isolado
│   ├── services/      # monitor, download, caption, publish, pipeline
│   ├── sources/       # ingestão: manual | instaloader | discovery (instagrapi)
│   ├── ai/            # gerador de legendas (Ollama) atrás de interface
│   ├── publishers/    # dry_run | instagram_graph (oficial) | instagrapi + token_store
│   ├── schedulers/    # loop 24/7 (1 post/ciclo, fila, trava de intervalo)
│   ├── web/           # painel FastAPI + rota /media (servida ao túnel)
│   └── utils/         # logging, validação/sanitização (remove aspas)
├── tools/             # helpers de setup (token, sessões de login)
├── deploy/            # instarepost.service (systemd)
├── iniciar_auto.sh    # launcher 24/7 (painel + túnel + scheduler)
├── iniciar_painel.sh  # só o painel de aprovação
├── cli.py  requirements.txt  .env.example  pytest.ini
```

**Substituíveis por interface:** `SourceProvider`, `CaptionGenerator`, `Publisher`.

---

## Instalação

```bash
cd Echo-Repost
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # ajuste as variáveis
python cli.py init          # cria diretórios + schema

# IA local:
ollama pull llama3.2:3b      # ou qwen3 / mistral; ajuste OLLAMA_MODEL no .env
python cli.py health
```

---

## Configuração da publicação OFICIAL (uma vez)

1. **@suaconta** convertida para **Professional** (Business/Creator).
2. App em developers.facebook.com → **Create App** → use case **Other** → tipo **Business**.
3. No app: produto **Instagram → "API setup with Instagram business login"**.
4. Em **App roles → Papéis → Instagram Testers**, adicione sua conta e **aceite o convite**
   no app (Configurações → Apps e sites → Convites de testador).
5. **Generate token** ao lado da conta → copie o token (já dura 60 dias).
6. Gere as linhas do `.env`:
   ```bash
   ./venv/bin/python tools/ig_instagram_setup.py --token TOKEN_DO_PAINEL
   ```
   Cole `IG_API_BASE`, `IG_USER_ID`, `IG_ACCESS_TOKEN` no `.env` e `PUBLISHER=instagram_graph`.

### Mídia pública (túnel Cloudflare)
A API oficial **baixa o vídeo de uma URL pública**. O `iniciar_auto.sh` sobe o túnel e
preenche `PUBLIC_MEDIA_BASE_URL` automaticamente. Manual:
```bash
cloudflared tunnel --url http://localhost:8021
# PUBLIC_MEDIA_BASE_URL=https://<sub>.trycloudflare.com/media
```

### Token: renovação automática
O token é gerenciado em `data/ig_token.json` (semeado do `.env`) e **renovado sozinho**
(`ig_refresh_token`) quando faltam < 10 dias. Para trocar manualmente: atualize o `.env`
**e** apague `data/ig_token.json`.
```bash
./venv/bin/python cli.py token            # status (dias restantes)
./venv/bin/python cli.py token --refresh  # força a renovação
```

---

## Configuração da descoberta/download (não-oficial)

```bash
# .env:
SOURCE_PROVIDER=instaloader
TARGET_USERNAME=perfil_alvo
INSTALOADER_USER=conta_descartavel
INSTALOADER_PASSWORD=...        # usado pelo instagrapi (descoberta)
AUTO_DISCOVERY=true

# Sessão do instaloader (download) a partir do Firefox logado na conta descartável:
./venv/bin/python tools/import_firefox_session.py conta_descartavel
```
A descoberta (instagrapi) salva sua própria sessão em `data/discovery_session.json`.

---

## Rodar 24/7

### Serviço systemd (recomendado — sobrevive a reboot)
```bash
cp deploy/instarepost.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now instarepost.service
loginctl enable-linger "$USER"     # roda mesmo sem login
```
> O `.service` espera o projeto em `~/InstaRepost` (`%h/InstaRepost`). Se estiver em outra
> pasta, ajuste `WorkingDirectory` e `ExecStart`. Os scripts `iniciar_*.sh` acham a própria
> pasta sozinhos.

### Ou manual
```bash
./iniciar_auto.sh     # painel + túnel + scheduler em um terminal
```

### Gerenciar
```bash
systemctl --user status instarepost     # estado
systemctl --user stop instarepost        # PAUSAR (para de postar)
systemctl --user start instarepost       # retomar
tail -f logs/instarepost.log             # acompanhar
```

---

## Uso manual (sem o loop)

```bash
python cli.py fetch <url_reel> [url...]   # baixa Reels específicos e processa
python cli.py publish                     # publica os pendentes/aprovados
python cli.py web                         # painel de aprovação (http://127.0.0.1:8000)
python cli.py token                       # status do token
```

Alimentar a fila do scheduler: cole URLs (1 por linha) em `data/queue.txt`.

---

## Variáveis de ambiente (principais)

| Variável | Padrão | Descrição |
|---|---|---|
| `SOURCE_PROVIDER` | `manual` | `manual` / `instaloader` |
| `TARGET_USERNAME` | — | Perfil de origem |
| `AUTO_DISCOVERY` | `false` | Enche a fila sozinho via instagrapi |
| `DISCOVERY_AMOUNT` | `8` | Quantos Reels buscar por ciclo |
| `INSTALOADER_USER/PASSWORD` | — | Conta descartável (descoberta/download) |
| `OLLAMA_MODEL` | `qwen3` | Modelo local de legenda |
| `REQUIRE_MANUAL_APPROVAL` | `true` | `false` = publica sozinho |
| `PUBLISHER` | `dry_run` | `dry_run` / `instagram_graph` / `instagrapi` |
| `IG_API_BASE` | `https://graph.instagram.com/v25.0` | Base da API oficial |
| `IG_USER_ID` / `IG_ACCESS_TOKEN` | — | Credenciais (helper gera) |
| `PUBLIC_MEDIA_BASE_URL` | — | URL pública (túnel) p/ `/media` |
| `POLL_INTERVAL_SECONDS` | `900` | Intervalo entre posts (ver cadência segura) |
| `URL_QUEUE_FILE` | `data/queue.txt` | Fila de URLs |

---

## Testes

```bash
pytest      # banco em memória + IA mockada; não depende de Ollama/rede/Instagram
```

---

## Riscos e manutenção

- **Conta de descoberta** pode ser limitada/banida pela Meta → a fila para de encher
  (aparece erro no log). A publicação oficial segue funcionando se você alimentar a fila.
- **Sem revisão humana** (`REQUIRE_MANUAL_APPROVAL=false`): reposta tudo do alvo. Para algo
  específico, use `systemctl --user stop instarepost` ou `REQUIRE_MANUAL_APPROVAL=true`.
- **Cadência:** não exagere (ver tabela). Conta nova = comece com 4–6/dia.
- **Túnel Cloudflare** (quick tunnel) muda de URL a cada start — o `iniciar_auto.sh`
  resolve sozinho. Para URL fixa, configure um túnel nomeado do Cloudflare.
- **Token** renova sozinho; só falha se ficar > 60 dias sem o serviço rodar.

---

## 🤝 Contribuindo
Melhorias são bem-vindas! Leia o [CONTRIBUTING.md](CONTRIBUTING.md) para preparar o ambiente,
rodar os testes e abrir um pull request. Falhas de segurança: veja o [SECURITY.md](SECURITY.md).

## 📄 Licença
[GPL-3.0](LICENSE). Você pode usar, estudar, modificar e redistribuir o código. Quem
distribuir uma versão modificada precisa mantê-la aberta, sob a mesma licença.
