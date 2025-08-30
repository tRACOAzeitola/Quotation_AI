
import unittest
from unittest.mock import patch, MagicMock
import os

# Adiciona o diretório raiz do projeto ao PATH para que possamos importar os módulos
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import main # Alterado de volta
from tasks import processar_email_task
from email_sender import enviar_email_cotacao

class TestCotacaoAI(unittest.TestCase):

    def setUp(self):
        # Configura as variáveis de ambiente necessárias para o .env, mas com valores fictícios
        os.environ["EMAIL_USUARIO"] = "test@example.com"
        os.environ["EMAIL_SENHA"] = "password"
        os.environ["EMAIL_SERVIDOR"] = "imap.test.com"
        os.environ["SMTP_SERVIDOR"] = "smtp.test.com"
        os.environ["SMTP_PORTA"] = "587"

    @patch('main.obter_emails')
    @patch('tasks.enviar_email_cotacao') # Patch no local onde é USADO em tasks.py
    @patch('redis.Redis') # Mock da classe Redis
    @patch('rq.Queue') # Mock da classe Queue
    @patch('main.q') # Mock da variável global q em main.py
    @patch('tasks.get_current_job')
    @patch('tasks.analisar_email') # Re-adicionar este mock
    @patch('tasks.calcular_cotacao') # Re-adicionar este mock
    def test_main_flow_with_mocked_emails(self, mock_calcular_cotacao, mock_analisar_email, mock_get_current_job, mock_main_q, MockQueueClass, mock_Redis, mock_enviar_email_cotacao, mock_obter_emails):
        # Configurar o mock para obter_emails para retornar uma lista de e-mails de teste
        mock_obter_emails.return_value = [
            {
                "remetente": "cliente@example.com",
                "assunto": "Pedido de Cotação - Transporte Urgente",
                "corpo": "Prezados, solicito uma cotação para transporte de carga."
            }
        ]

        # Mock para a fila (para evitar conexão real com Redis e execução de workers)
        # Precisamos que o enqueue retorne um objeto MagicMock que tenha um atributo 'id'
        mock_job = MagicMock()
        mock_job.id = "mock_job_id_123"

        # Configurar o mock para a instância de Queue em main.py
        mock_main_q.enqueue.return_value = mock_job

        # Configurar o mock para get_current_job
        mock_get_current_job.return_value = mock_job

        # Configurar o mock para analisar_email com um valor que a tabela de preços pode processar
        mock_analisar_email.return_value = {
            "destino": "Porto",
            "peso": "100",
            "volume": "40", # Volume ajustado para um valor válido na tabela
            "tipo_transporte": "", # A IA pode ou não preencher isso, mas o cotador lida com a ausência
            "temperatura": "frio"
        }

        # Configurar o mock para calcular_cotacao com um resultado esperado da tabela
        mock_calcular_cotacao.return_value = {
            "destino": "Porto",
            "tipo_transporte": "Camiao Grande", # Baseado na tabela para Porto, 100kg, 40m3, frio
            "peso": "100",
            "volume": "40",
            "preco_final": 850.00, # Preço correspondente na tabela
            "temperatura": "frio"
        }

        # Chamar a função principal
        main()

        # Verificar se obter_emails foi chamado
        mock_obter_emails.assert_called_once()

        # Verificar se a tarefa de processar_email_task foi enfileirada através da variável global 'q'
        mock_main_q.enqueue.assert_called_once()

        # Chamar processar_email_task diretamente para testar sua lógica
        processar_email_task(mock_obter_emails.return_value[0])

        # Verificar se analisar_email foi chamado e com o corpo do email
        mock_analisar_email.assert_called_once_with(mock_obter_emails.return_value[0]["corpo"])

        # Verificar se calcular_cotacao foi chamado e com os dados extraídos
        mock_calcular_cotacao.assert_called_once_with(mock_analisar_email.return_value)

        # Verificar se enviar_email_cotacao foi chamado com os argumentos esperados
        mock_enviar_email_cotacao.assert_called_once()
        args, kwargs = mock_enviar_email_cotacao.call_args
        
        self.assertEqual(kwargs['destinatario'], "cliente@example.com") # Destinatário
        self.assertEqual(kwargs['assunto_original'], "Pedido de Cotação - Transporte Urgente") # Assunto de resposta
        # Verificar os campos específicos da cotação mockada
        self.assertEqual(kwargs['cotacao']['destino'], "Porto")
        self.assertEqual(kwargs['cotacao']['tipo_transporte'], "Camiao Grande")
        self.assertEqual(kwargs['cotacao']['peso'], "100")
        self.assertEqual(kwargs['cotacao']['volume'], "40")
        self.assertEqual(kwargs['cotacao']['preco_final'], 850.00)
        self.assertEqual(kwargs['cotacao']['temperatura'], "frio")

        print("E-mail de cotação mockado enviado com sucesso!")

if __name__ == '__main__':
    unittest.main()