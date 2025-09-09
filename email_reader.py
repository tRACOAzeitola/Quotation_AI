import imaplib
import email
from email.header import decode_header
import os
from logger_config import logger

PALAVRAS_CHAVE = ["pedido", "orçamento", "cotação", "preço", "urgente"]

def limpar_texto(texto):
    return "".join(c if c.isalnum() else " " for c in texto).lower()

def obter_emails():
    # Se o modo de teste estiver ativo, retorna um e-mail simulado
    if os.getenv("APP_TEST_MODE") == "true":
        logger.info("APP_TEST_MODE está ativo. Retornando e-mail de teste simulado.")
        return [
            {
                "remetente": "cliente_teste@example.com",
                "assunto": "Cotação ",
                "corpo": """
Vols: Fruta
Peso (kgs): 800
M3: 5
Entrega: Meimoa
"""
            }
        ]

    emails_relevantes = []
    mail = None

    EMAIL_USUARIO = os.getenv("EMAIL_USUARIO")
    EMAIL_SENHA = os.getenv("EMAIL_SENHA")
    EMAIL_SERVIDOR = os.getenv("EMAIL_SERVIDOR")
    EMAIL_PASTA = os.getenv("EMAIL_PASTA", "inbox")

    try:
        logger.info(f"Conectando ao servidor IMAP: {EMAIL_SERVIDOR}")
        mail = imaplib.IMAP4_SSL(EMAIL_SERVIDOR)
        mail.login(EMAIL_USUARIO, EMAIL_SENHA)
        mail.select(EMAIL_PASTA)
        logger.info(f"Conexão bem-sucedida. Selecionada a pasta '{EMAIL_PASTA}'.")

        status, mensagens = mail.search(None, "(UNSEEN)") # Procura apenas e-mails não lidos
        if status != 'OK':
            logger.error("Falha ao buscar e-mails.")
            return []

        ids = mensagens[0].split()
        if not ids:
            logger.info("Nenhum e-mail não lido encontrado.")
            return []

        logger.info(f"Encontrados {len(ids)} e-mails não lidos. Processando...")

        for num in ids:
            status, dados = mail.fetch(num, "(RFC822)")
            if status != 'OK':
                logger.warning(f"Falha ao buscar o e-mail com ID {num.decode()}.")
                continue

            for resposta in dados:
                if isinstance(resposta, tuple):
                    msg = email.message_from_bytes(resposta[1])
                    assunto, codificacao = decode_header(msg["Subject"])[0]
                    if isinstance(assunto, bytes):
                        assunto = assunto.decode(codificacao or "utf-8")
                    remetente = msg.get("From")

                    corpo = ""
                    if msg.is_multipart():
                        for parte in msg.walk():
                            if parte.get_content_type() == "text/plain":
                                corpo = parte.get_payload(decode=True).decode(errors='ignore')
                                break
                    else:
                        corpo = msg.get_payload(decode=True).decode(errors='ignore')

                    texto_completo = limpar_texto(assunto + " " + corpo)
                    if any(palavra in texto_completo for palavra in PALAVRAS_CHAVE):
                        logger.info(f"E-mail de '{remetente}' sobre '{assunto}' marcado como relevante.")
                        emails_relevantes.append({
                            "remetente": remetente,
                            "assunto": assunto,
                            "corpo": corpo
                        })
                        # Marcar e-mail como lido para não processar novamente
                        mail.store(num, '+FLAGS', '\\Seen')

        return emails_relevantes

    except imaplib.IMAP4.error as e:
        logger.error(f"Erro de IMAP: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Erro inesperado ao ler os e-mails: {e}", exc_info=True)
        return []
    finally:
        if mail:
            logger.info("Fechando a conexão com o servidor IMAP.")
            mail.logout()