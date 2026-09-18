"""
Auxiliares de fila (Redis) - PRONTO, use como esta.

A fila guarda tarefas pendentes e os resultados prontos.
Conceito da Aula 8: quem pede nao espera; um worker processa depois.
"""
import json
import os
import uuid

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
FILA_TAREFAS = "tarefas"
FILA_DEAD_LETTER = "tarefas:dead_letter"
PREFIXO_RESULTADO = "resultado:"

_cliente = None


def cliente():
    global _cliente
    if _cliente is None:
        _cliente = redis.from_url(REDIS_URL, decode_responses=True)
    return _cliente


def enfileirar(texto: str) -> str:
    """Coloca uma tarefa na fila e devolve o id para consulta posterior."""
    tarefa_id = str(uuid.uuid4())
    cliente().rpush(FILA_TAREFAS, json.dumps({"id": tarefa_id, "texto": texto}))
    cliente().set(PREFIXO_RESULTADO + tarefa_id,
                  json.dumps({"status": "na_fila"}))
    return tarefa_id


def proxima_tarefa(timeout: int = 5):
    """Bloqueia ate chegar tarefa (ou timeout). Usado pelo worker."""
    item = cliente().blpop(FILA_TAREFAS, timeout=timeout)
    if item is None:
        return None
    return json.loads(item[1])


def guardar_resultado(tarefa_id: str, resultado: dict) -> None:
    cliente().set(PREFIXO_RESULTADO + tarefa_id, json.dumps(resultado))


def buscar_resultado(tarefa_id: str):
    bruto = cliente().get(PREFIXO_RESULTADO + tarefa_id)
    return json.loads(bruto) if bruto else None


def enviar_para_dead_letter(tarefa: dict, erro: str, tentativas: int) -> None:
    """Grava a tarefa que esgotou as tentativas numa fila de descarte
    dedicada (lista Redis separada da fila principal), para inspecao
    posterior. Nao remove o status "falha" salvo por guardar_resultado.
    """
    cliente().rpush(
        FILA_DEAD_LETTER,
        json.dumps({**tarefa, "erro": erro, "tentativas": tentativas}),
    )


def tamanho_dead_letter() -> int:
    return cliente().llen(FILA_DEAD_LETTER)
