"""
Interface REST do servico de inferencia.

O QUE JA ESTA PRONTO:
  - carregamento do modelo UMA vez, na subida (nao a cada requisicao)
  - rota sincrona /predict-sync, usada no laboratorio da Aula 6

O QUE VOCE PRECISA FAZER (TAREFAS.md, itens 1 e 2):
  - POST /predict  -> colocar na fila e devolver o id
  - GET  /resultado/{id} -> devolver o resultado quando estiver pronto

Rodar:  uvicorn app.api_rest:app --reload --port 8000
Docs:   http://localhost:8000/docs
"""
import time
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.modelo import carregar_modelo
from app.log_requisicoes import registrar_requisicao
from app import fila

app = FastAPI(title="Servico de Inferencia - C1.A2", version="0.1.0")

modelo = None


class Entrada(BaseModel):
    texto: str


@app.on_event("startup")
def _subir():
    """Carrega o modelo UMA vez. Este e o ponto-chave da Aula 6."""
    global modelo
    inicio = time.time()
    modelo = carregar_modelo()
    print(f"[startup] modelo carregado em {time.time() - inicio:.3f}s")


@app.get("/saude")
def saude():
    return {"status": "ok", "modelo_carregado": modelo is not None}


@app.post("/predict-sync")
def predict_sync(entrada: Entrada):
    """Inferencia SINCRONA: o cliente espera a resposta. Lab da Aula 6."""
    if not entrada.texto.strip():
        raise HTTPException(status_code=400, detail="texto vazio")
    inicio = time.time()
    resultado = modelo.prever(entrada.texto)
    resultado["tempo_ms"] = round((time.time() - inicio) * 1000, 2)
    registrar_requisicao(
        str(uuid.uuid4()), len(entrada.texto), resultado["tempo_ms"],
        origem="rest-sync",
    )
    return resultado



@app.post("/predict", status_code=202)
def predict(entrada: Entrada):
    inicio = time.time()
    tarefa_id = fila.enfileirar(entrada.texto)
    registrar_requisicao(
        tarefa_id, len(entrada.texto),
        round((time.time() - inicio) * 1000, 2),
        origem="rest-async-submissao",
    )
    return ({"id": tarefa_id })



@app.get("/resultado/{tarefa_id}")
def resultado(tarefa_id: str):
    """Deve devolver o resultado; 404 se o id nao existir."""
    inicio = time.time()
    res = fila.buscar_resultado(tarefa_id)
    registrar_requisicao(
        tarefa_id, 0, round((time.time() - inicio) * 1000, 2),
        origem="rest-async-consulta",
    )
    if res is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return res