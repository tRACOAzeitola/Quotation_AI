import dotenv
dotenv.load_dotenv()
from redis import Redis
from rq import Queue, Retry
from email_reader import obter_emails
from tasks import processar_email_task, on_failure
from logger_config import logger

# Carregar variáveis do .env
dotenv.load_dotenv()

# Conectar ao Redis e configurar a fila principal
redis_conn = Redis()
q = Queue(connection=redis_conn, default_timeout=3600)

# Configurar a fila de falhas
failed_queue = Queue("failed", connection=redis_conn)

def main():
    """
    Lê e-mails e enfileira tarefas para serem processadas pelos workers.
    """
    logger.info("--- INICIANDO VERIFICAÇÃO DE E-MAILS ---")
    
    try:
        emails = obter_emails()

        if not emails:
            logger.info("Nenhum e-mail novo para processar.")
            return

        logger.info(f"{len(emails)} e-mails novos encontrados. Enfileirando tarefas...")

        for email in emails:
            # Enfileira a tarefa com política de retentativa e manipulador de falha
            job = q.enqueue(
                processar_email_task, 
                email,
                on_failure=on_failure,
                retry=Retry(max=3, interval=[10, 30, 60]) # Tenta 3 vezes em intervalos de 10s, 30s, 60s
            )
            logger.info(f"Tarefa {job.id} enfileirada para o e-mail de {email['remetente']}")

        logger.info(f"{len(emails)} tarefas foram adicionadas à fila com sucesso.")

    except Exception as e:
        logger.error(f"Ocorreu um erro grave no processo principal: {e}", exc_info=True)

    finally:
        logger.info("--- Fim do ciclo de verificação de e-mails ---")

if __name__ == "__main__":
    main()