"""
Utilitario de log de requisicoes - usado por todos os servicos (REST, gRPC, worker).

TAREFA 6: registra, para cada requisicao, id, tamanho da entrada e tempo de resposta.
"""
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("requisicoes")


def registrar_requisicao(id_requisicao: str, tamanho_entrada: int,
                          tempo_resposta_ms: float, origem: str = ""):
    """Registra uma requisicao processada.

    id_requisicao: identificador unico da requisicao/tarefa.
    tamanho_entrada: tamanho do texto de entrada, em caracteres.
    tempo_resposta_ms: tempo de resposta, em milissegundos.
    origem: nome do servico que gerou o log (rest-sync, rest-async, grpc, worker).
    """
    logger.info(
        "id=%s origem=%s tamanho_entrada=%d tempo_resposta_ms=%.2f",
        id_requisicao, origem, tamanho_entrada, tempo_resposta_ms,
    )