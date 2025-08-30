import os
import json
import ollama
from logger_config import logger
import pandas as pd # Importar pandas aqui para ler a tabela de preços

# Carregar a tabela de preços para obter os destinos válidos
try:
    df_precos = pd.read_csv("tabela_precos.csv")
    destinos_validos = list(df_precos['destino'].str.strip().str.lower().unique())
    logger.info(f"Destinos válidos carregados: {destinos_validos}")
except Exception as e:
    logger.error(f"Erro ao carregar destinos válidos da tabela_precos.csv: {e}", exc_info=True)
    destinos_validos = [] # Fallback para lista vazia em caso de erro

def analisar_email(corpo_email):
    """
    Usa o modelo Llama3 via Ollama para extrair dados estruturados de um e-mail.
    """
    prompt = f"""""Instruções para extração de dados de e-mail:

Objetivo: Extrair informações de transporte de carga de um e-mail e formatá-las em JSON.
Prioridade: Garantir que o campo 'destino' seja sempre um dos valores na lista {destinos_validos}.

1.  **Destino**:
    -   Encontre a cidade ou localidade mencionada no e-mail.
    -   O destino **DEVE** ser um dos seguintes: {destinos_validos}.
    -   Se o destino do e-mail não estiver na lista, escolha o destino da lista que seja geograficamente mais próximo ou logicamente mais adequado.
    -   Converta o destino para letras minúsculas.

2.  **Peso**:
    -   Identifique o peso total da carga.
    -   A unidade padrão é quilogramas (kg). Se o peso for em 'toneladas', converta para kg (1 tonelada = 1000 kg).
    -   Converta o valor para um número inteiro.

3.  **Volume**:
    -   Calcule o volume total da carga.
    -   A unidade padrão é metros cúbicos (m3).
    -   Se houver dimensões (por exemplo, `3m x 3m x 5m`), multiplique-as para obter o volume em m3.
    -   Se o volume estiver em 'litros', converta para m3 (1000 litros = 1 m3).
    -   Converta o valor para um número inteiro.

4.  **Tipo de Transporte**:
    -   Procure por termos que descrevam o veículo, como 'Pequeno', 'Médio', 'Camiao' ou 'Camiao Grande'.
    -   Se não for especificado, o valor é `null`.

5.  **Temperatura**:
    -   Verifique se há menção explícita de `frio` ou `frigorífico`.
    -   Se sim, o valor é `frio`. Caso contrário, o valor é `ambiente`.

6.  **Saída Final**:
    -   Retorne a resposta **APENAS** em formato JSON, sem qualquer texto adicional ou explicação.
    -   Use a seguinte estrutura de chaves: `"destino": "...", "peso": "...", "volume": "...", "tipo_transporte": "...", "temperatura": "..."`.
    -   Se uma informação não for encontrada, o valor correspondente é `null`.

--- DEMONSTRATION EXAMPLE ---
E-mail: "Preciso de transporte urgente de 8 toneladas para Albufeira, com dimensões de 3m x 3m x 5m e carga frigorífica."
JSON Esperado:
"destino": "faro", "peso": 8000, "volume": 45, "tipo_transporte": null, "temperatura": "frio"
HTML Esperado:
```html
<p>O preço para este serviço de transporte é:</p>
<table>
  <tr><td>Preço</td><td>450 €</td></tr>
</table>
<p>Obrigado, SpeedConect.</p>
--- FIM DO EXEMPLO ---

E-mail a ser processado:
---
{corpo_email}
---"
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