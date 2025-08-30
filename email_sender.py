import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logger_config import logger

def enviar_email_cotacao(destinatario, assunto_original, cotacao):
    """
    Formata e envia um e-mail de resposta com a cotação.
    Lança uma exceção em caso de falha.
    """
    # Se o modo de teste estiver ativo, apenas registra o e-mail em vez de enviá-lo
    if os.getenv("APP_TEST_MODE") == "true":
        logger.info(f"APP_TEST_MODE está ativo. Simulando envio de e-mail para {destinatario}")
        logger.info(f"Assunto: Re: {assunto_original}")
        logger.info(f"Cotação simulada: {cotacao}")

        # Adicionar a lógica de construção do HTML para o modo de teste
        destino = cotacao.get('destino', 'N/A')
        peso = cotacao.get('peso', 'N/A')
        volume = cotacao.get('volume', 'N/A')
        tipo_transporte = cotacao.get('tipo_transporte', 'N/A')
        preco_final = cotacao.get('preco_final', 0)
        temperatura = cotacao.get('temperatura', 'ambiente').capitalize()

        corpo_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
            .container {{ padding: 25px; border: 1px solid #ddd; border-radius: 10px; max-width: 600px; margin: 40px auto; background-color: #ffffff; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            .header {{ font-size: 26px; color: #0056b3; margin-bottom: 20px; border-bottom: 2px solid #0056b3; padding-bottom: 10px; }}
            .details {{ margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee; }}
            .footer {{ margin-top: 25px; font-size: 12px; color: #777; }}
            strong {{ color: #0056b3; }}
            .price {{ font-size: 20px; font-weight: bold; color: #28a745; }}
        </style>
    </head>
    <body>
        <div class="container">
            <p class="header">Proposta de Cotação - SpeedConect</p>
            <p>Olá,</p>
            <p>Agradecemos o seu contacto. É com prazer que apresentamos a nossa proposta para o transporte solicitado:</p>
            <div class="details">
                <p><strong>Destino:</strong> {destino}</p>
                <p><strong>Tipo de Transporte:</strong> {tipo_transporte}</p>
                <p><strong>Peso:</strong> {peso} kg</p>
                <p><strong>Volume:</strong> {volume} m³</p>
                <p><strong>Condição de Transporte:</strong> {temperatura}</p>
                <hr>
                <p class="price">Valor Final: {preco_final:.2f} €</p>
            </div>
            <p>Esta proposta é válida por 15 dias. Para qualquer esclarecimento ou para confirmar o serviço, estamos à sua inteira disposição.</p>
            <p>Com os melhores cumprimentos,</p>
            <p><strong>A Equipa SpeedConect</strong></p>
            <p class="footer">Este é um e-mail automático. Por favor, não responda diretamente.</p>
        </div>
    </body>
    </html>
    """
        logger.info(f"HTML gerado (simulado):\n---\n{corpo_html}\n---")
        return True

    EMAIL_USUARIO = os.getenv("EMAIL_USUARIO")
    EMAIL_SENHA = os.getenv("EMAIL_SENHA")
    SMTP_SERVIDOR = os.getenv("SMTP_SERVIDOR", "smtp.gmail.com")
    SMTP_PORTA = int(os.getenv("SMTP_PORTA", 587))

    assunto_resposta = f"Re: {assunto_original}"
    # Extrair dados da cotação com valores padrão
    destino = cotacao.get('destino', 'N/A')
    peso = cotacao.get('peso', 'N/A')
    volume = cotacao.get('volume', 'N/A')
    tipo_transporte = cotacao.get('tipo_transporte', 'N/A')
    preco_final = cotacao.get('preco_final', 0)
    temperatura = cotacao.get('temperatura', 'ambiente').capitalize()

    corpo_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
            .container {{ padding: 25px; border: 1px solid #ddd; border-radius: 10px; max-width: 600px; margin: 40px auto; background-color: #ffffff; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            .header {{ font-size: 26px; color: #0056b3; margin-bottom: 20px; border-bottom: 2px solid #0056b3; padding-bottom: 10px; }}
            .details {{ margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee; }}
            .footer {{ margin-top: 25px; font-size: 12px; color: #777; }}
            strong {{ color: #0056b3; }}
            .price {{ font-size: 20px; font-weight: bold; color: #28a745; }}
        </style>
    </head>
    <body>
        <div class="container">
            <p class="header">Proposta de Cotação - SpeedConect</p>
            <p>Olá,</p>
            <p>Agradecemos o seu contacto. É com prazer que apresentamos a nossa proposta para o transporte solicitado:</p>
            <div class="details">
                <p><strong>Destino:</strong> {destino}</p>
                <p><strong>Tipo de Transporte:</strong> {tipo_transporte}</p>
                <p><strong>Peso:</strong> {peso} kg</p>
                <p><strong>Volume:</strong> {volume} m³</p>
                <p><strong>Condição de Transporte:</strong> {temperatura}</p>
                <hr>
                <p class="price">Valor Final: {preco_final:.2f} €</p>
            </div>
            <p>Esta proposta é válida por 15 dias. Para qualquer esclarecimento ou para confirmar o serviço, estamos à sua inteira disposição.</p>
            <p>Com os melhores cumprimentos,</p>
            <p><strong>A Equipa SpeedConect</strong></p>
            <p class="footer">Este é um e-mail automático. Por favor, não responda diretamente.</p>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = EMAIL_USUARIO
    msg['To'] = destinatario
    msg['Subject'] = assunto_resposta
    msg.attach(MIMEText(corpo_html, 'html'))

    logger.info(f"Tentando enviar e-mail para {destinatario}")
    try:
        with smtplib.SMTP(SMTP_SERVIDOR, SMTP_PORTA) as server:
            server.starttls()
            server.login(EMAIL_USUARIO, EMAIL_SENHA)
            server.send_message(msg)
        logger.info(f"E-mail enviado com sucesso para {destinatario}")
        return True
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail para {destinatario}. Erro: {e}", exc_info=True)
        return False

