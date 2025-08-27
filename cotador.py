import pandas as pd
from logger_config import logger

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

    def _normalizar_colunas(self):
        self.df.columns = [col.strip().lower() for col in self.df.columns]
        if 'destino' in self.df.columns:
            self.df['destino'] = self.df['destino'].str.strip().str.lower()

    def encontrar_cotacao(self, destino, peso, volume):
        destino_normalizado = destino.lower().strip()
        logger.info(f"Buscando cotação para Destino: {destino_normalizado}, Peso: {peso}, Volume: {volume}")

        filtro = (
            (self.df["destino"] == destino_normalizado) &
            (self.df["peso_maximo"] >= peso) &
            (self.df["volume_maximo"] >= volume)
        )

        resultados = self.df[filtro].sort_values(by=["peso_maximo", "volume_maximo"])

        if resultados.empty:
            logger.warning(f"Nenhuma cotação encontrada para os critérios: Destino={destino_normalizado}, Peso={peso}, Volume={volume}")
            return None

        return resultados.iloc[0]

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

        resultado = cotador_global.encontrar_cotacao(
            destino=dados_extraidos["destino"],
            peso=dados_extraidos["peso"],
            volume=dados_extraidos["volume"]
        )

        if resultado is not None:
            cotacao_completa = {
                'destino': resultado['destino'].capitalize(),
                'tipo_transporte': resultado['tipo_transporte'],
                'peso': dados_extraidos['peso'],
                'volume': dados_extraidos['volume'],
                'preco_final': resultado['preco_final'],
                'prazo_entrega': resultado['prazo_entrega']
            }
            return cotacao_completa

    except KeyError as e:
        logger.error(f"Chave ausente nos dados extraídos ao preparar para cotação: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado ao calcular cotação: {e}", exc_info=True)
    
    return None