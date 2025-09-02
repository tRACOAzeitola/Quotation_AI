
import os
import sys
from unittest.mock import patch, MagicMock
import json
import pandas as pd
from logger_config import logger # Move logger import to the top

# Adicionar o diretório raiz do projeto ao PATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

# Definir variáveis de ambiente para o modo de teste
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES" # Para macOS
os.environ["APP_TEST_MODE"] = "true" # Não será usado nos módulos, mas para logs

# Mock da função obter_emails do email_reader
def mock_obter_emails():
    logger.info("Simulando obter_emails() - Retornando e-mail de teste.")
    return [
        {
            "remetente": "cliente_simulado@example.com",
            "assunto": "Pedido de Cotação - Simulado",
            "corpo": "Preciso de transporte urgente de 8 toneladas para Albufeira, com dimensões de 3m x 3m x 5m e carga frigorífica."
        }
    ]

# Mock da função enviar_email_cotacao do email_sender (chamada via tasks)
def mock_enviar_email_cotacao(destinatario, assunto_original, cotacao):
    logger.info(f"Simulando enviar_email_cotacao() para {destinatario}")
    logger.info(f"Assunto: Re: {assunto_original}")
    logger.info(f"Cotação (dados): {cotacao}")

    # Lógica para construir o HTML (copiada de email_sender.py)
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

if __name__ == "__main__":
    # Mocks para o Redis e RQ (para evitar conexão real e enfileiramento)
    with patch('main.Redis'), \
         patch('main.Queue') as MockQueueClass, \
         patch('main.q') as mock_main_q:

        mock_job = MagicMock()
        mock_job.id = "simulated_job_id_123"
        MockQueueClass.return_value.enqueue.return_value = mock_job
        mock_main_q.enqueue.return_value = mock_job

        # Mocks para as funções de email
        with patch('main.obter_emails', side_effect=mock_obter_emails), \
             patch('tasks.enviar_email_cotacao', side_effect=mock_enviar_email_cotacao):

            # Importar e executar main.py APÓS os mocks serem aplicados
            from main import main, q, redis_conn, failed_queue # Reimportar se necessário
            logger.info("--- INICIANDO FLUXO DE TESTE INTEGRADO ---")
            main() # Executar a função principal
            logger.info("--- FIM DO FLUXO DE TESTE INTEGRADO ---")

            # Opcional: Adicionar asserções para verificar se as chamadas ocorreram
            # mock_obter_emails.assert_called_once()
            # mock_main_q.enqueue.assert_called_once()
            # mock_enviar_email_cotacao.assert_called_once()