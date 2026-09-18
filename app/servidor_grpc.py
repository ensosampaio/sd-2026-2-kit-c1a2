"""
Interface gRPC do servico de inferencia.

PRE-REQUISITO: gerar os stubs antes de rodar (veja scripts/gerar_stubs).

O QUE JA ESTA PRONTO: o metodo Prever e o metodo PreverLote (TAREFA 4).

Rodar:  python -m app.servidor_grpc
"""
import time
import uuid
from concurrent import futures

import grpc

from app.log_requisicoes import registrar_requisicao
from app.modelo import carregar_modelo

try:
    import inferencia_pb2
    import inferencia_pb2_grpc
except ImportError:  # pragma: no cover
    raise SystemExit(
        "Stubs nao encontrados. Rode antes:\n"
        "  python -m grpc_tools.protoc -I proto --python_out=. "
        "--grpc_python_out=. proto/inferencia.proto"
    )


class ServicoInferencia(inferencia_pb2_grpc.InferenciaServicer):

    def __init__(self):
        print("[grpc] carregando modelo...")
        self.modelo = carregar_modelo()
        print("[grpc] modelo pronto")

    def Prever(self, request, context):
        inicio = time.time()
        r = self.modelo.prever(request.texto)
        registrar_requisicao(
            str(uuid.uuid4()), len(request.texto),
            round((time.time() - inicio) * 1000, 2),
            origem="grpc-prever",
        )
        return inferencia_pb2.RespostaPrever(
            texto=r["texto"], sentimento=r["sentimento"], confianca=r["confianca"]
        )

    def PreverLote(self, request, context):
        inicio = time.time()
        resultados = []
        tamanho_total = 0
        for texto in request.textos:
            r = self.modelo.prever(texto)
            tamanho_total += len(texto)
            resultados.append(
                inferencia_pb2.RespostaPrever(
                    texto=r["texto"],
                    sentimento=r["sentimento"],
                    confianca=r["confianca"],
                )
            )
        registrar_requisicao(
            str(uuid.uuid4()), tamanho_total,
            round((time.time() - inicio) * 1000, 2),
            origem="grpc-preverlote",
        )
        return inferencia_pb2.RespostaLote(resultados=resultados)


def servir(porta: int = 50051):
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inferencia_pb2_grpc.add_InferenciaServicer_to_server(
        ServicoInferencia(), servidor)
    servidor.add_insecure_port(f"[::]:{porta}")
    servidor.start()
    print(f"[grpc] escutando na porta {porta}")
    servidor.wait_for_termination()


if __name__ == "__main__":
    servir()
