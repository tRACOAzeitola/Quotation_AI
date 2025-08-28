import os
import json
import ollama
from logger_config import logger


def analisar_email(corpo_email):
    """
    Usa o modelo Llama3 via Ollama para extrair dados estruturados de um e-mail.
    """
    prompt = f"""Extraia as seguintes informações do corpo do e-mail abaixo:
    - destino (cidade ou localidade)
    - peso (em kg)
    - volume (em m3)
    - tipo_transporte (normal ou frio)
    - temperatura (se aplicável, caso contrário "ambiente")

    Se alguma informação não estiver presente, retorne `null` para o campo correspondente.
    Retorne a resposta APENAS em formato JSON.

    E-mail:
    ---
    {corpo_email}
    ---
    """

    logger.info("A chamar a API do Ollama com Llama3 para extrair dados...")
    try:
        response = ollama.chat(
            model='llama3',
            messages=[
                {"role": "system", "content": "Você é um assistente especialista em logística e extração de dados. Retorne a resposta APENAS em formato JSON."},
                {"role": "user", "content": prompt}
            ],
            format='json'
        )
        
        # O conteúdo da mensagem já vem como um string JSON
        dados_extraidos = json.loads(response['message']['content'])
        logger.info(f"Dados recebidos do Ollama: {dados_extraidos}")
        
        # Garantir que os campos numéricos sejam do tipo correto
        if dados_extraidos.get("peso"):
            dados_extraidos["peso"] = int(dados_extraidos["peso"])
        if dados_extraidos.get("volume"):
            dados_extraidos["volume"] = int(dados_extraidos["volume"])

        return dados_extraidos

    except json.JSONDecodeError as e:
        logger.error(f"Erro ao descodificar a resposta JSON do Ollama: {e}")
        logger.error(f"Resposta recebida: {response['message']['content']}")
        return None
    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado ao chamar a API do Ollama: {e}", exc_info=True)
        # Lançar a exceção para que o RQ possa lidar com a falha
        raise e