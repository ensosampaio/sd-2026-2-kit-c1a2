"""Cliente gRPC de exemplo. Gere os stubs e rode o servidor gRPC antes.

  python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/inferencia.proto
  python -m app.servidor_grpc
"""
import os
import sys

import grpc

# Os stubs (inferencia_pb2*.py) sao gerados na raiz do repositorio; garanta
# que ela esteja no sys.path mesmo rodando este script diretamente
# (python exemplos/cliente_grpc.py) de qualquer diretorio.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import inferencia_pb2
import inferencia_pb2_grpc

ENDERECO = "localhost:50051"


def prever(canal, texto):
    stub = inferencia_pb2_grpc.InferenciaStub(canal)
    resposta = stub.Prever(inferencia_pb2.PedidoPrever(texto=texto))
    print("prever:", resposta)


def prever_lote(canal, textos):
    stub = inferencia_pb2_grpc.InferenciaStub(canal)
    resposta = stub.PreverLote(inferencia_pb2.PedidoLote(textos=textos))
    for r in resposta.resultados:
        print("preverlote:", r)


if __name__ == "__main__":
    textos = sys.argv[1:] or [
        "o atendimento foi muito bom",
        "produto pessimo, nao recomendo",
    ]
    with grpc.insecure_channel(ENDERECO) as canal:
        prever(canal, textos[0])
        prever_lote(canal, textos)
