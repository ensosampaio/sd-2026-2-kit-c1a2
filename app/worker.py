"""
Worker: consome a fila e executa a inferencia.

O QUE JA ESTA PRONTO: o laco principal, o carregamento do modelo, o
armazenamento do resultado (TAREFA 3) e a retentativa com dead-letter
(TAREFA 5).

Rodar:  python -m app.worker
Suba mais de um worker em terminais diferentes e veja a carga se dividir.
"""
import time

from app import fila
from app.modelo import carregar_modelo

MAX_TENTATIVAS = 3
BACKOFF_BASE_SEGUNDOS = 1.0


def processar_tarefa(modelo, tarefa):
    """Executa a inferencia com retentativa (backoff exponencial) e,
    se todas as tentativas falharem, registra a tarefa como falha
    definitiva (dead-letter) via fila.guardar_resultado.
    """
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        inicio = time.time()
        try:
            resultado = modelo.prever(tarefa["texto"])
            resultado["status"] = "pronto"
            resultado["tempo_ms"] = round((time.time() - inicio) * 1000, 2)

            fila.guardar_resultado(tarefa["id"], resultado)
            print(
                f"[worker] {tarefa['id']} concluida em "
                f"{resultado['tempo_ms']}ms (tentativa {tentativa}/{MAX_TENTATIVAS})"
            )
            return

        except Exception as erro:  # noqa: BLE001
            print(
                f"[worker] ERRO em {tarefa['id']} "
                f"(tentativa {tentativa}/{MAX_TENTATIVAS}): {erro}"
            )

            if tentativa < MAX_TENTATIVAS:
                espera = BACKOFF_BASE_SEGUNDOS * (2 ** (tentativa - 1))
                print(f"[worker] tentando novamente em {espera:.1f}s...")
                time.sleep(espera)
            else:
                # TAREFA 5: esgotou as tentativas -> dead-letter.
                # Aqui gravamos a tarefa como falha definitiva para que o
                # cliente consiga consultar o status. Se o modulo `fila`
                # tiver uma fila de descarte dedicada (ex.: um metodo como
                # `fila.enviar_para_dead_letter(...)`), troque a chamada
                # abaixo por ela.
                fila.guardar_resultado(
                    tarefa["id"],
                    {
                        "status": "falha",
                        "erro": str(erro),
                        "tentativas": tentativa,
                    },
                )
                print(
                    f"[worker] {tarefa['id']} enviada para dead-letter "
                    f"apos {tentativa} tentativas"
                )


def main():
    print("[worker] carregando modelo...")
    modelo = carregar_modelo()
    print("[worker] pronto. aguardando tarefas (Ctrl+C para sair)")

    while True:
        tarefa = fila.proxima_tarefa(timeout=5)
        if tarefa is None:
            continue

        print(f"[worker] processando {tarefa['id']}")
        processar_tarefa(modelo, tarefa)


if __name__ == "__main__":
    main()