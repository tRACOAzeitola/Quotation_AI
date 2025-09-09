import os
import json
import ollama
from logger_config import logger
import pandas as pd # Importar pandas aqui para ler a tabela de preços
import re # Adicionar import para regex
# RAG: tentativa de import; fallback se indisponível
try:
    from rag_store import retrieve_similar
except Exception:
    retrieve_similar = None

# Carregar a tabela de preços para obter os destinos válidos
try:
    df_precos = pd.read_csv("tabela_precos.csv")
    destinos_validos = list(df_precos['destino'].str.strip().str.lower().unique())
    logger.info(f"Destinos válidos carregados: {destinos_validos}")
except Exception as e:
    logger.error(f"Erro ao carregar destinos válidos da tabela_precos.csv: {e}", exc_info=True)
    destinos_validos = [] # Fallback para lista vazia em caso de erro

# Palavras-chave que implicam cadeia de frio, mesmo sem mencionar "frio" explicitamente
COLD_KEYWORDS = {
    "fruta", "frutas", "congelado", "congelados", "refrigerado", "refrigerados",
    "gelado", "gelados", "laticinio", "laticínios", "laticinios", "lacticínios",
    "leite", "queijo", "iogurte", "carne", "peixe", "marisco", "mariscos",
    "pescado", "charcutaria", "farma", "farmaceutico", "farmacêutico",
    "medicamento", "medicamentos", "vacina", "vacinas",
}

def _build_rag_context(corpo_email: str) -> str:
    """Obtém exemplos similares do RAG e formata um contexto textual.
    Se RAG não estiver disponível, retorna string vazia.
    """
    try:
        if retrieve_similar is None:
            return ""
        similares = retrieve_similar(corpo_email, top_k=3)
        if not similares:
            return ""
        linhas = []
        for i, s in enumerate(similares, 1):
            meta = s.get("metadata", {}) or {}
            destino = meta.get("destino")
            peso = meta.get("peso")
            volume = meta.get("volume")
            temperatura = meta.get("temperatura")
            resumo = (s.get("text") or "").replace("\n", " ")[:200]
            linhas.append(f"Ex{i}: destino={destino}, peso={peso}, volume={volume}, temperatura={temperatura} | texto='{resumo}'")
        return "\n".join(linhas)
    except Exception as e:
        logger.warning(f"Falha ao obter contexto RAG: {e}")
        return ""

def normalizar_peso(peso_str):
    """Converte peso textual para kg"""
    if not isinstance(peso_str, str):
        return None
    peso_str = peso_str.lower().replace(",", ".").strip()
    
    # Tenta analisar como um número simples, assumindo kg se nenhuma unidade for especificada
    try:
        numeric_peso = float(peso_str)
        return round(numeric_peso, 2)
    except ValueError:
        pass # Não é apenas um número, continua com a análise regex

    match = re.search(r"([\d\.]+)\s*(kg|kilos|ton|toneladas|t)", peso_str)
    if not match:
        logger.warning(f"Formato de peso '{peso_str}' não reconhecido.")
        return None

    valor, unidade = float(match.group(1)), match.group(2)
    if unidade.startswith(("kg", "kilos")):
        return round(valor, 2)
    elif unidade.startswith(("ton", "t")):
        return round(valor * 1000, 2)
    return None

def normalizar_volume(volume_str):
    """Converte volume textual para m³"""
    if not isinstance(volume_str, str):
        return None
    volume_str = volume_str.lower().replace(",", ".").strip()
    
    # Tenta analisar como um número simples, assumindo m3 se nenhuma unidade for especificada (ex: de "M3: 0.51")
    try:
        numeric_volume = float(volume_str)
        return round(numeric_volume, 2)
    except ValueError:
        pass # Não é apenas um número, continua com a análise regex

    # Caso já venha em m³ (ex: "0.51 m3", "45 m³", "0.42 m^3")
    match_m3 = re.search(r"([\d\.]+)\s*m\s*(?:\^?3|³)", volume_str)
    if match_m3:
        return round(float(match_m3.group(1)), 2)

    # Caso seja em dimensões (ex: "3x3x5 metros", "3m x 3m x 5m", "300cm x 300cm x 500cm", "120 x 80 x 122 cm")
    # Regex para capturar dimensões com ou sem unidades explícitas por cada valor, e unidade final
    # Ex: "120 x 80 x 122 cm" ou "3m x 3m x 5m"
    # Importante: o grupo da unidade final é único e opcional (?: ... )? para evitar grupos extras
    # Regra: unidade individual só é capturada se vier colada ao número (ex: "3m").
    # Com espaço (ex: "80 cm"), considera-se unidade final para todas as dimensões.
    dim_match = re.search(r"([\d\.]+)(m|cm)?\s*[xX*]\s*([\d\.]+)(m|cm)?\s*[xX*]\s*([\d\.]+)(m|cm)?(?:\s*(m|cm|metros|centimetros))?", volume_str)
    
    if dim_match:
        # Agora são exatamente 7 grupos: v1,u1,v2,u2,v3,u3,final_unit
        v1, u1, v2, u2, v3, u3, final_unit = dim_match.groups()

        logger.debug(f"DEBUG: dim_match.groups() -> {dim_match.groups()}") # NOVO LOG
        logger.debug(f"DEBUG: v1={v1}, u1={u1}, v2={v2}, u2={u2}, v3={v3}, u3={u3}, final_unit={final_unit}") # NOVO LOG

        # final_unit já vem limpo (m|cm|metros|centimetros) ou None -> normalizamos para base
        unit_map = {
            'm': 'm', 'metros': 'm',
            'cm': 'cm', 'centimetros': 'cm', 'centímetros': 'cm',
        }
        final_unit_norm = unit_map.get((final_unit or '').lower())
        logger.debug(f"DEBUG: final_unit -> {final_unit} | normalized={final_unit_norm}") # NOVO LOG

        valores_m = []
        try:
            # Usa a unidade final se disponível, senão assume a unidade padrão (m)
            # Ou tenta inferir das dimensões individuais se elas tiverem unidade
            effective_unit = (final_unit_norm or 'm')
            logger.debug(f"DEBUG: effective_unit -> {effective_unit}") # NOVO LOG

            for val_str, individual_unit in [(v1, u1), (v2, u2), (v3, u3)]:
                logger.debug(f"DEBUG: Processando dimensão: val_str={val_str}, individual_unit={individual_unit}") # NOVO LOG
                val = float(val_str)
                # Normaliza a unidade individual (se houver) e decide conversão
                unit_to_use = (individual_unit or effective_unit or 'm').lower()
                unit_to_use = unit_map.get(unit_to_use, unit_to_use)
                if unit_to_use == 'cm':
                    valores_m.append(val / 100)
                else:  # 'm' ou desconhecido (assumimos 'm')
                    valores_m.append(val)
            logger.debug(f"DEBUG: valores_m -> {valores_m}") # NOVO LOG

            return round(valores_m[0] * valores_m[1] * valores_m[2], 2)
        except ValueError:
            logger.warning(f"Erro ao converter dimensões numéricas para volume: '{volume_str}'")
            return None
    
    logger.warning(f"Formato de volume '{volume_str}' não reconhecido.")
    return None

def analisar_email(corpo_email):
    """
    Usa o modelo Llama3 via Ollama para extrair dados estruturados de um e-mail,
    e então normaliza esses dados com funções Python.
    """
    # RAG: contexto interno semelhante
    rag_context = _build_rag_context(corpo_email)

    prompt_llm = f"""Instruções para extração de dados de e-mail:

Contexto interno (exemplos semelhantes de e-mails/cotações):
{rag_context}

Objetivo: Extrair informações de transporte de carga de um e-mail e formatá-las em JSON.
Extraia os dados **exatamente como aparecem no texto**, sem tentar converter ou validar.

1.  **destino_texto**:
    -   Identifique a **cidade principal de entrega em Portugal ou Europa**. Priorize sempre uma cidade conhecida.
    -   Se o e-mail mencionar "Aeroporto de Lisboa", "Lisboa Aeroporto" ou similar para entrega, o destino deve ser **"Lisboa"**.
    -   Ignore códigos de aeroporto (LIS, HAV), referências internas (JTM, Portway) ou nomes de países que não sejam Portugal ou países europeus vizinhos (como CUBA, que deve ser ignorado).
    -   Extraia **apenas o nome da cidade** mais relevante para a cotação, mesmo que o email mencione um endereço completo, múltiplos pontos ou localidades de recolha (como "Pontinha").
    -   **Exemplos:**
        -   "Entrega: Aeroporto de Lisboa a/c JTM Destino - LIS / HAV - CUBA" -> "Lisboa"
        -   "Morada: Rua X, 123, Porto" -> "Porto"
        -   "Local entrega: 2951-503 Palmela" -> "Palmela"

2.  **peso_texto**:
    -   Identifique o peso total da carga, **exatamente como escrito**.
    -   Ex: "83 kgs", "1.5 toneladas", "400 kg"

3.  **volume_texto**:
    -   Calcule o volume total da carga, **exatamente como escrito**.
    -   Ex: "0,51", "0.51 m3", "3x3x5 metros", "45 m3" (se o contexto indicar metros cúbicos sem unidade explícita, apenas o número)

4.  **tipo_transporte**:
    -   Procure por termos que descrevam o veículo, como 'Pequeno', 'Médio', 'Camiao' ou 'Camiao Grande'.
    -   Se não for especificado, o valor é `null`.

5.  **temperatura**:
    -   Verifique se há menção explícita de `frio` ou `frigorífico`.
    -   Se sim, o valor é `frio`. Caso contrário, o valor é `ambiente`.

6.  **Saída Final**:
    -   Retorne a resposta **APENAS** em formato JSON, sem qualquer texto adicional ou explicação.
    -   Use a seguinte estrutura de chaves: `"destino_texto": "...", "peso_texto": "...", "volume_texto": "...", "tipo_transporte": "...", "temperatura": "..."`.
    -   Se uma informação não for encontrada, o valor correspondente é `null`.

--- DEMONSTRATION EXAMPLE ---
E-mail: "Preciso de transporte urgente de 8 toneladas para Albufeira, com dimensões de 3m x 3m x 5m e carga frigorífica."
JSON Esperado:
{{"destino_texto": "Albufeira", "peso_texto": "8 toneladas", "volume_texto": "3m x 3m x 5m", "tipo_transporte": null, "temperatura": "frio"}}
--- FIM DO EXEMPLO ---

--- NOVO EXEMPLO DE DEMONSTRAÇÃO ---
E-mail: "Bom dia Ricardo,\nPor favor, confirmem valor e disponibilidade para a recolha abaixo:\nMorada da Recolha:\nMesclachoice\nCasal do Troca\nEstrada da Paiã\n1675-076 Pontinha\nData de Recolha: 02/09 às 14h30\nCarga:\nQty: 1 plt\nDms: 112x47x80 cm\nWght: 190 kg\nEntrega:\nAeroporto de Lisboa a/c JTM\nDestino - LIS / HAV - CUBA\nEntregar na Portway\nObrigada"
JSON Esperado:
{{"destino_texto": "Lisboa", "peso_texto": "190 kg", "volume_texto": "112x47x80 cm", "tipo_transporte": null, "temperatura": "ambiente"}}
--- FIM DO NOVO EXEMPLO ---

--- EXEMPLO DE COTAÇÃO PARA AEROPORTO ---
E-mail: "Entrega: Aeroporto de Lisboa"
JSON Esperado:
{{"destino_texto": "Lisboa", "peso_texto": null, "volume_texto": null, "tipo_transporte": null, "temperatura": "ambiente"}}
--- FIM DO EXEMPLO DE COTAÇÃO PARA AEROPORTO ---

E-mail a ser processado:
---
{corpo_email}
---"""

    logger.info("A chamar a API do Ollama com Llama3 para extrair dados brutos...")
    try:
        response = ollama.chat(
            model='llama3',
            messages=[
                {"role": "system", "content": "Você é um assistente especialista em logística e extração de dados. Retorne a resposta APENAS em formato JSON."},
                {"role": "user", "content": prompt_llm} # Usar o novo prompt_llm
            ],
            format='json'
        )
        
        dados_brutos = json.loads(response['message']['content'])
        logger.info(f"Dados brutos recebidos do Ollama: {dados_brutos}")
        
        # --- Normalização em Python ---
        dados_normalizados = {}

        # 1. Normalizar Destino (sem fuzzy matching, sem sinônimos)
        destino_extraido = dados_brutos.get("destino_texto", "")
        if destino_extraido:
            destino_normalizado_lower = destino_extraido.lower().strip()
            # Regra explícita: aeroporto de Lisboa mapeia para Lisboa
            if (
                "aeroporto de lisboa" in destino_normalizado_lower
                or "lisboa aeroporto" in destino_normalizado_lower
            ):
                dados_normalizados["destino"] = "lisboa"
                logger.info(f"Destino '{destino_extraido}' mapeado para 'lisboa' via regra explícita.")
            else:
                # Mantém o destino exatamente como extraído (normalizado em lower)
                dados_normalizados["destino"] = destino_normalizado_lower
                logger.info(
                    "Destino mantido exatamente como extraído (sem fuzzy/sinônimos): '%s'",
                    dados_normalizados["destino"],
                )
        else:
            dados_normalizados["destino"] = None
            logger.warning("Destino não extraído pelo LLM.")


        # 2. Normalizar Peso
        peso_texto = dados_brutos.get("peso_texto")
        dados_normalizados["peso"] = normalizar_peso(peso_texto)
        if dados_normalizados["peso"] is None and peso_texto:
            logger.warning(f"Não foi possível normalizar o peso '{peso_texto}'.")

        # 3. Normalizar Volume
        volume_texto = dados_brutos.get("volume_texto")
        dados_normalizados["volume"] = normalizar_volume(volume_texto)
        if dados_normalizados["volume"] is None and volume_texto:
            logger.warning(f"Não foi possível normalizar o volume '{volume_texto}'.")
        
        # 4. Manter Tipo de Transporte e Temperatura do LLM (sem normalização Python adicional)
        dados_normalizados["tipo_transporte"] = dados_brutos.get("tipo_transporte")
        dados_normalizados["temperatura"] = dados_brutos.get("temperatura")

        # Heurística: se o e-mail mencionar produtos que exigem frio e a temperatura vier
        # ausente ou "ambiente", força para "frio".
        try:
            texto_lower = (corpo_email or "").lower()
            menciona_frio_implicito = any(k in texto_lower for k in COLD_KEYWORDS)
            temp_atual = (dados_normalizados.get("temperatura") or "").lower() or None
            if menciona_frio_implicito and (temp_atual is None or temp_atual == "ambiente"):
                dados_normalizados["temperatura"] = "frio"
                logger.info("Temperatura ajustada para 'frio' via heurística de produto (cadeia de frio).")
        except Exception:
            # Não interromper o fluxo por causa da heurística
            pass
        
        logger.info(f"Dados normalizados e validados: {dados_normalizados}")
        return dados_normalizados

    except json.JSONDecodeError as e:
        logger.error(f"Erro ao descodificar a resposta JSON do Ollama: {e}")
        logger.error(f"Resposta recebida: {response.get('message', {}).get('content', 'N/A')}")
        raise # Re-lança a exceção para que o RQ a capture e chame o on_failure
    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado ao processar o e-mail: {e}", exc_info=True)
        raise # Re-lança a exceção