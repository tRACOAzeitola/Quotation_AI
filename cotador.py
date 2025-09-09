import os
import json
import pandas as pd
from logger_config import logger
import requests


class Cotador:
    def __init__(self, tabela_path="tabela_precos.csv"):
        try:
            self.df = pd.read_csv(tabela_path)
            self._normalizar_colunas()
            logger.info(f"Tabela de preços '{tabela_path}' carregada com sucesso.")
        except FileNotFoundError:
            logger.error(f"Arquivo da tabela de preços '{tabela_path}' não encontrado.")
            raise
        except Exception as e:
            logger.error(f"Erro ao ler ou processar a tabela de preços: {e}", exc_info=True)
            raise

        # Geocoding será feito via HTTP direto ao Nominatim (sem dependência externa)
        # Carrega configuração de preços por km do ficheiro privado (gitignored)
        self._pricing_tiers = self._load_pricing_tiers()

    def _normalizar_colunas(self):
        self.df.columns = [col.strip().lower() for col in self.df.columns]
        if 'destino' in self.df.columns:
            self.df['destino'] = self.df['destino'].str.strip().str.lower()

    def encontrar_cotacao(self, destino, peso, volume, temperatura="ambiente"):
        destino_normalizado = destino.lower().strip()
        temperatura_normalizada = temperatura.lower().strip() if isinstance(temperatura, str) else "ambiente"
        
        logger.info(f"Buscando cotação para Destino: {destino_normalizado}, Peso: {peso}, Volume: {volume}, Temperatura: {temperatura_normalizada}")

        filtro = (
            (self.df["destino"] == destino_normalizado) &
            (self.df["peso_maximo"] >= peso) &
            (self.df["volume_maximo"] >= volume) &
            (self.df["temperatura"] == temperatura_normalizada)
        )

        resultados = self.df[filtro].sort_values(by=["preco"]) # Ordenar pelo preço para encontrar o mais barato

        if not resultados.empty:
            return resultados.iloc[0]

        # Fallback API se não encontrar na tabela
        logger.warning(
            f"Nenhuma cotação exata encontrada na tabela. A tentar fallback via API (Nominatim + OSRM) para destino='{destino_normalizado}'."
        )
        return self._cotar_por_api(destino_normalizado, peso, volume, temperatura_normalizada)

    def _cotar_por_api(self, destino: str, peso: float, volume: float, temperatura: str):
        try:
            origem = "Lisboa, Portugal"
            origem_loc = self._geocode(origem)
            destino_loc = self._geocode(destino)
            if not origem_loc or not destino_loc:
                logger.error(
                    f"Falha no geocoding (origem='{origem}', destino='{destino}')."
                )
                return None

            distance_km = self._osrm_distance_km(origem_loc, destino_loc)
            if distance_km is None:
                logger.error("Falha ao obter distância via OSRM.")
                return None

            tarifa_km, tipo_transporte = self._tarifa_por_peso_volume(peso, volume, temperatura)
            if tarifa_km is None:
                logger.warning(
                    f"Sem tarifa definida para peso={peso}kg e volume={volume}m3."
                )
                return None

            preco = round(distance_km * tarifa_km, 2)
            # Monta um "resultado"-like (estrutura similar a uma linha do DF)
            return {
                "destino": destino,
                "tipo_transporte": tipo_transporte,
                "preco": preco,
                "temperatura": temperatura,
                "fonte": "api"
            }
        except Exception as e:
            logger.error(f"Erro no fallback de cotação por API: {e}", exc_info=True)
            return None

    def _geocode(self, query: str):
        """Geocoding usando Nominatim via HTTP (sem API key)."""
        try:
            params = {
                "q": query,
                "format": "json",
                "addressdetails": 0,
                "countrycodes": "pt",
                "limit": 1,
            }
            headers = {"User-Agent": "cotacoes_ai_app/1.0 (contact: exemplo@exemplo.com)"}
            r = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
            if not data:
                return None
            item = data[0]
            lat = float(item.get("lat"))
            lon = float(item.get("lon"))
            return (lat, lon)
        except Exception as e:
            logger.warning(f"Falha no geocoding para '{query}': {e}")
            return None

    def _osrm_distance_km(self, origem_latlon, destino_latlon):
        try:
            o_lat, o_lon = origem_latlon
            d_lat, d_lon = destino_latlon
            url = (
                f"https://router.project-osrm.org/route/v1/driving/"
                f"{o_lon},{o_lat};{d_lon},{d_lat}?overview=false&alternatives=false&annotations=distance"
            )
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            routes = data.get("routes") or []
            if not routes:
                return None
            dist_m = routes[0].get("distance")
            if dist_m is None:
                return None
            return round(dist_m / 1000.0, 2)
        except Exception as e:
            logger.warning(f"Falha ao consultar OSRM: {e}")
            return None

    def _tarifa_por_peso_volume(self, peso: float, volume: float, temperatura: str):
        """Retorna (tarifa_por_km, tipo_transporte) conforme configuração privada.
        Esta informação é carregada de um ficheiro gitignored.
        """
        try:
            if not self._pricing_tiers:
                logger.warning("Configuração de preços por km não encontrada. Fallback API desativado.")
                return None, None
            for tier in self._pricing_tiers:
                peso_max = float(tier.get("peso_max", 0))
                vol_max = float(tier.get("volume_max", 0))
                tarifa = float(tier.get("tarifa_eur_km", 0))
                tipo = tier.get("tipo_transporte")
                temp_tier = tier.get("temperatura")
                if temp_tier is None and isinstance(tipo, str):
                    tl = tipo.lower()
                    if "frio" in tl:
                        temp_tier = "frio"
                    elif "ambiente" in tl:
                        temp_tier = "ambiente"
                # Se o tier especifica temperatura, só aplica se coincidir
                if temp_tier is not None and str(temp_tier).lower().strip() != str(temperatura).lower().strip():
                    continue
                if peso <= peso_max and volume <= vol_max:
                    return tarifa, tipo
            return None, None
        except Exception as e:
            logger.error(f"Erro ao avaliar faixas de preço: {e}")
            return None, None

    def _load_pricing_tiers(self):
        """Carrega faixas de preço por km de um ficheiro JSON privado.
        Ordem de procura:
        - Variável de ambiente PRICING_CONFIG_PATH (caminho para JSON)
        - 'pricing_config.json' na raiz do projeto
        Estrutura esperada: lista de objetos com chaves: peso_max, volume_max, tarifa_eur_km, tipo_transporte
        """
        try:
            cfg_path = os.getenv("PRICING_CONFIG_PATH", "pricing_config.json")
            if not os.path.exists(cfg_path):
                logger.warning(f"Ficheiro de configuração de preços não encontrado: {cfg_path}")
                return []
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                logger.warning("Configuração de preços inválida: esperado uma lista de tiers.")
                return []
            return data
        except Exception as e:
            logger.error(f"Erro ao carregar configuração de preços: {e}", exc_info=True)
            return []

# --- Otimização: Instância Única do Cotador ---
# Criamos uma instância global para que a tabela de preços seja lida do disco apenas uma vez.
try:
    cotador_global = Cotador()
except Exception:
    cotador_global = None
    logger.critical("Falha crítica ao inicializar o Cotador. O sistema não poderá processar cotações.")

def calcular_cotacao(dados_extraidos):
    """
    Ponto de entrada para o cálculo de cotação. Utiliza a instância global do Cotador.
    """
    if cotador_global is None:
        logger.error("O Cotador não está disponível. Impossível calcular cotação.")
        return None

    try:
        # Validação de dados de entrada
        required_keys = ["destino", "peso", "volume"]
        if not all(key in dados_extraidos and dados_extraidos[key] is not None for key in required_keys):
            logger.warning(f"Dados insuficientes para cotação. Recebido: {dados_extraidos}")
            return None

        # Usar 'ambiente' como padrão se a temperatura não for extraída
        temperatura = dados_extraidos.get("temperatura", "ambiente")

        resultado = cotador_global.encontrar_cotacao(
            destino=dados_extraidos["destino"],
            peso=dados_extraidos["peso"],
            volume=dados_extraidos["volume"],
            temperatura=temperatura
        )

        if resultado is not None:
            # Pode vir como Series (da tabela) ou dict (fallback API)
            if isinstance(resultado, dict):
                destino_out = resultado.get('destino', dados_extraidos['destino']).capitalize()
                tipo_transporte_out = resultado.get('tipo_transporte')
                preco_out = resultado.get('preco')
                temperatura_out = resultado.get('temperatura', temperatura)
            else:
                destino_out = resultado['destino'].capitalize()
                tipo_transporte_out = resultado['tipo_transporte']
                preco_out = resultado['preco']
                temperatura_out = resultado['temperatura']

            cotacao_completa = {
                'destino': destino_out,
                'tipo_transporte': tipo_transporte_out,
                'peso': dados_extraidos['peso'],
                'volume': dados_extraidos['volume'],
                'preco_final': preco_out,
                'temperatura': temperatura_out,
            }
            return cotacao_completa

    except KeyError as e:
        logger.error(f"Chave ausente nos dados extraídos ao preparar para cotação: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado ao calcular cotação: {e}", exc_info=True)
    
    return None