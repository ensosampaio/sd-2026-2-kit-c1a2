"""Indexa os .txt da pasta documentos/ pelo servico de ingestao.

Uso:  python scripts/indexar_documentos.py
O POST /indexar apenas enfileira; o script espera o worker terminar de
processar (consultando GET /indice) para mostrar o resultado final.
"""
import os
import sys
import time
from pathlib import Path

import requests

URL_INGESTAO = os.getenv("URL_INGESTAO", "http://localhost:8001")
PASTA = Path(__file__).resolve().parent.parent / "documentos"


def main() -> int:
    docs = [
        {"texto": arq.read_text(encoding="utf-8").strip(), "origem": arq.name}
        for arq in sorted(PASTA.glob("*.txt"))
    ]
    if not docs:
        print(f"Nenhum .txt em {PASTA}")
        return 1

    r = requests.post(f"{URL_INGESTAO}/indexar", json=docs, timeout=10)
    r.raise_for_status()
    print("Enfileirado:", r.json())

    origens = {d["origem"] for d in docs}
    for _ in range(30):
        itens = requests.get(f"{URL_INGESTAO}/indice", timeout=10).json()["itens"]
        if origens <= {i["origem"] for i in itens}:
            print(f"Worker processou. Indice com {len(itens)} documento(s).")
            return 0
        time.sleep(1)
    print("Tempo esgotado: o worker esta rodando? (python -m servicos.ingestao.worker)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
