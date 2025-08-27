import os
import json
from openai import OpenAI
from logger_config import logger

# Inicializar o cliente da OpenAI
client = OpenAI()

def analisar_email(corpo_email):
    """
    Usa o modelo da OpenAI para extrair dados estruturados de um e-mail.
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

    logger.info("A chamar a API da OpenAI para extrair dados...")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente especialista em logística e extração de dados."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )

        dados_extraidos = json.loads(response.choices[0].message.content)
        logger.info(f"Dados recebidos da OpenAI: {dados_extraidos}")
        
        # Garantir que os campos numéricos sejam do tipo correto
        if dados_extraidos.get("peso"):
            dados_extraidos["peso"] = int(dados_extraidos["peso"])
        if dados_extraidos.get("volume"):
            dados_extraidos["volume"] = int(dados_extraidos["volume"])

        return dados_extraidos

    except json.JSONDecodeError as e:
        # Captura o erro caso a OpenAI não retorne um JSON válido
        logger.error(f"Erro ao descodificar a resposta JSON da OpenAI: {e}")
        logger.error(f"Resposta recebida: {response.choices[0].message.content}")
        return None
    except Exception as e:
        # Captura outros erros (ex: falha de conexão, chave de API inválida)
        logger.error(f"Ocorreu um erro inesperado ao chamar a API da OpenAI: {e}", exc_info=True)
        return None
        logger.error(f"Erro ao comunicar com a API da OpenAI: {e}", exc_info=True)
        # Lançar a exceção para que o RQ possa lidar com a falha
        raise