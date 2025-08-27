import traceback
from rq import get_current_job

from logger_config import logger
from agent import analisar_email
from cotador import calcular_cotacao
from email_sender import enviar_email_cotacao

def on_failure(job, connection, type, value, traceback):
    """
    Manipulador de falhas customizado para o RQ.
    Registra a falha e move o job para a fila 'failed'.
    """
    logger.error(f"Falha na tarefa {job.id}. Motivo: {value}")
    logger.error(f"Email original: {job.args[0]}")
    logger.error(traceback)

def processar_email_task(email):
    """
    Tarefa que será executada por um worker da fila.
    Recebe um dicionário de e-mail, processa-o e envia a resposta.
    """
    job = get_current_job()
    logger.info(f"Iniciando tarefa {job.id} para o e-mail de: {email['remetente']}")

    try:
        assunto = email["assunto"]
        corpo = email["corpo"]
        remetente = email["remetente"]

        logger.info(f"[TAREFA {job.id}] 1. Analisando e-mail com IA...")
        dados_extraidos = analisar_email(corpo)

        if not dados_extraidos or not all(dados_extraidos.get(k) for k in ["destino", "peso", "volume"]):
            logger.warning(f"[TAREFA {job.id}] Não foi possível extrair todos os dados do e-mail. E-mail: {corpo[:150]}...")
            return # Termina a tarefa, pois não é uma falha, mas sim dados insuficientes

        logger.info(f"[TAREFA {job.id}] Dados extraídos com sucesso: {dados_extraidos}")

        logger.info(f"[TAREFA {job.id}] 2. Calculando cotação...")
        cotacao_encontrada = calcular_cotacao(dados_extraidos)

        if not cotacao_encontrada:
            logger.warning(f"[TAREFA {job.id}] Nenhuma cotação encontrada para os dados: {dados_extraidos}")
            return

        logger.info(f"[TAREFA {job.id}] Cotação encontrada: {cotacao_encontrada}")

        logger.info(f"[TAREFA {job.id}] 3. Enviando e-mail de resposta para {remetente}...")
        sucesso = enviar_email_cotacao(
            destinatario=remetente,
            assunto_original=assunto,
            cotacao=cotacao_encontrada
        )

        if sucesso:
            logger.info(f"[TAREFA {job.id}] E-mail enviado com sucesso para {remetente}")
        else:
            # Lança uma exceção para que a tarefa seja marcada como falha
            raise RuntimeError(f"Falha no envio do e-mail para {remetente}")

    except Exception as e:
        logger.error(f"[TAREFA {job.id}] Ocorreu um erro inesperado: {e}")
        # Re-lança a exceção para que o RQ a capture e chame o on_failure
        raise

