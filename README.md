# C1.A2 — Serviço de Inferência Distribuído

Sistemas Distribuídos e Computação em Nuvem · FAESA · 2026/2

## Integrantes

- Arthur Coutinho Chagas
- Enzo Sampaio Lopes Herzog de Azeredo
- Luan Gonçalves dos Santos
- Lucas Machado de Magalhães
- Vinícius de Souza Silva

Serviço que recebe um texto e devolve uma classificação de sentimento
(positivo/negativo), exposto por duas interfaces de comunicação — **REST**
e **gRPC** — e desacoplado da inferência em si por uma **fila** (Redis), para
que o cliente nunca fique esperando o modelo rodar.

## Arquitetura

```
                         ┌──────────────┐
        REST (síncrono)  │              │
    ┌───────────────────▶│  api_rest.py │──────┐
    │   /predict-sync     │  (FastAPI)   │      │ chama o modelo
    │                     └──────────────┘      │ diretamente
    │                                            ▼
cliente                                     modelo.py (em memória,
    │                     ┌──────────────┐  carregado 1x por processo)
    │   REST (assíncrono) │              │      ▲
    ├────────────────────▶│  api_rest.py │      │
    │   POST /predict      │  /predict    │      │
    │   GET  /resultado/id  └──────┬───────┘      │
    │                              │ enfileira     │
    │                              ▼               │
    │                       ┌─────────────┐         │
    │                       │    Redis    │         │
    │                       │ fila.py     │         │
    │                       └──────┬──────┘         │
    │                              │ consome         │
    │                              ▼                 │
    │                       ┌──────────────┐         │
    │                       │  worker.py   │─────────┘
    │                       │ (1..N        │
    │                       │  processos)  │
    │                       └──────────────┘
    │
    │   gRPC (síncrono, unário e em lote)
    └────────────────────▶ servidor_grpc.py ──▶ modelo.py
        Prever / PreverLote
```

Cada serviço é um **processo independente** (REST, gRPC e worker rodam em
terminais separados) e só se comunicam via rede ou via Redis — nenhum
importa o estado interno do outro. Isso permite escalar o worker
horizontalmente (subir 2+ instâncias) sem tocar nas interfaces.

- **`app/modelo.py`** — classificador de sentimento (scikit-learn), treinado
  uma vez e cacheado em `modelo.joblib`. Carregado uma única vez por
  processo (no `startup` da API, no `__init__` do servicer gRPC e no início
  do `main()` do worker) — nunca a cada requisição.
- **`app/fila.py`** — abstrai o Redis: fila de tarefas pendentes (lista
  `tarefas`), fila de descarte (`tarefas:dead_letter`) e o armazenamento de
  resultados por id (chaves `resultado:<id>`).
- **`app/api_rest.py`** — interface REST (FastAPI). Rota síncrona
  (`/predict-sync`, usada em laboratório) e o fluxo assíncrono pedido no
  trabalho (`POST /predict` + `GET /resultado/{id}`).
- **`app/servidor_grpc.py`** — interface gRPC. `Prever` (um texto) e
  `PreverLote` (vários textos, uma única chamada de rede).
- **`app/worker.py`** — consome a fila, roda a inferência, grava o
  resultado e trata falhas (retentativa + dead-letter).
- **`app/log_requisicoes.py`** — logging estruturado usado por todos os
  serviços acima.

## Decisões de implementação (núcleo obrigatório)

1. **Submissão assíncrona** (`POST /predict`) — enfileira o texto via
   `fila.enfileirar` e devolve `202 Accepted` com `{"id": ...}` imediatamente,
   sem chamar o modelo.
2. **Consulta de resultado** (`GET /resultado/{id}`) — busca em
   `resultado:<id>`; devolve `404` se a chave não existir (id inválido ou
   já expirado).
3. **Worker grava o resultado** — ao terminar a inferência com sucesso,
   `fila.guardar_resultado(id, {...})` com `status: "pronto"`.
4. **gRPC `PreverLote`** — recebe `PedidoLote{repeated string textos}` e
   devolve `RespostaLote{repeated RespostaPrever resultados}`, chamando o
   modelo uma vez por texto dentro da mesma chamada RPC (uma única
   viagem de rede para o lote inteiro).
5. **Tratamento de erro / dead-letter** — `processar_tarefa` tenta até
   `MAX_TENTATIVAS = 3` vezes, com backoff exponencial (1s, 2s) entre
   tentativas. Se todas falharem: grava `status: "falha"` em
   `resultado:<id>` (para quem consultar pela API) **e** publica a tarefa
   original + erro na fila dedicada `tarefas:dead_letter`, separada da fila
   principal, para inspeção posterior sem bloquear novas tarefas.
6. **Log de requisições** — `log_requisicoes.registrar_requisicao(id,
   tamanho_entrada, tempo_resposta_ms, origem)` é chamado em todo ponto de
   entrada: `/predict-sync`, `/predict`, `/resultado/{id}`, `Prever`,
   `PreverLote` e no worker (sucesso e falha definitiva). `origem`
   identifica de qual serviço veio o log (`rest-sync`,
   `rest-async-submissao`, `rest-async-consulta`, `grpc-prever`,
   `grpc-preverlote`, `worker`, `worker-dead-letter`).

## Como executar do zero

Pré-requisitos: Python 3.11+, Docker (para o Redis).

```bash
# 1. Clone o repositório e entre na pasta
git clone https://github.com/ensosampaio/sd-2026-2-kit-c1a2.git
cd sd-2026-2-kit-c1a2

# 2. Crie e ative o ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Suba o Redis
docker compose up -d

# 5. Gere os stubs do gRPC (precisa rodar de novo se o .proto mudar)
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/inferencia.proto
```

Em três terminais separados (todos com o `.venv` ativado):

```bash
# Terminal 1 — API REST
uvicorn app.api_rest:app --reload --port 8000
# docs interativas em http://localhost:8000/docs

# Terminal 2 — worker (pode subir mais de um para dividir a carga)
python -m app.worker

# Terminal 3 — servidor gRPC
python -m app.servidor_grpc
```

## Como testar

```bash
# REST (síncrono e assíncrono)
python exemplos/cliente_rest.py "o atendimento foi otimo"

# gRPC (unário e em lote)
python exemplos/cliente_grpc.py "o atendimento foi otimo" "produto pessimo"
```

Ou manualmente pela API:

```bash
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d "{\"texto\": \"o atendimento foi otimo\"}"
curl http://localhost:8000/resultado/<id-devolvido-acima>
```

As duas interfaces chamam o mesmo `modelo.py`, então REST e gRPC devolvem o
mesmo `sentimento`/`confianca` para o mesmo texto.

## Resiliência

- **Retentativa com backoff**: falhas transitórias na inferência são
  reprocessadas até 3 vezes antes de desistir.
- **Dead-letter queue**: tarefas que esgotam as tentativas vão para
  `tarefas:dead_letter` (lista Redis separada) em vez de travar a fila
  principal ou serem perdidas silenciosamente.
- **Múltiplos workers**: como o consumo da fila é via `BLPOP`, subir mais
  de um `python -m app.worker` divide a carga automaticamente — nenhuma
  tarefa é processada duas vezes.

## Variáveis de ambiente

Ver `.env.example`. A única necessária é `REDIS_URL`
(padrão `redis://localhost:6379/0`).
