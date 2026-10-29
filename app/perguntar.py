"""Faz uma pergunta ao servico de geracao.

Uso:  python scripts/perguntar.py "o que diz o teorema CAP?"
"""
import json
import os
import sys

import requests

URL_GERACAO = os.getenv("URL_GERACAO", "http://localhost:8003")


def main() -> int:
    pergunta = " ".join(sys.argv[1:]) or "o que diz o teorema CAP?"
    r = requests.post(f"{URL_GERACAO}/perguntar", json={"pergunta": pergunta}, timeout=60)
    print(f"HTTP {r.status_code}")
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    return 0 if r.ok else 1


if __name__ == "__main__":
    sys.exit(main())
