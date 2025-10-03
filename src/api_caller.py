"""
Módulo responsável por fazer as chamadas da API de Marcas
Adaptado do código original para arquitetura modular
"""

import requests
import pandas as pd
import time
import logging
from typing import Optional
from src.config_manager import ConfigManager

class APICaller:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
    
    def fetch_data(self) -> pd.DataFrame:
        """
        Faz as chamadas para a API e retorna um DataFrame consolidado
        """
        try:
            # Carrega as configurações da API
            api_configs = self.config.load_api_configs()
            self.logger.info(f"Carregadas {len(api_configs)} configurações da API")
            
            # Lista para armazenar todos os DataFrames
            all_dfs = []
            
            # Itera sobre as configurações da API
            for config in api_configs:
                url = config["url"]
                data = config["data"]
                
                df_result = self._call_api_with_retry(url, data)
                if df_result is not None:
                    all_dfs.append(df_result)
            
            if not all_dfs:
                self.logger.error("Nenhum DataFrame foi recuperado das chamadas da API")
                return pd.DataFrame()
            
            # Concatena todos os DataFrames em um único DataFrame
            final_df = pd.concat(all_dfs, ignore_index=True)
            self.logger.info(f"Concatenados {len(all_dfs)} DataFrames em final_df com {len(final_df)} registros")
            
            # Salva os arquivos
            self._save_dataframes(final_df)
            
            return final_df
            
        except Exception as e:
            self.logger.error(f"Erro durante a chamada da API: {str(e)}")
            raise
    
    def _call_api_with_retry(self, url: str, data: dict, max_retries: int = 1) -> Optional[pd.DataFrame]:
        """
        Faz uma chamada da API com retry em caso de erro 500
        """
        retry_count = 0
        
        while retry_count <= max_retries:
            self.logger.info(f"Tentativa {retry_count + 1} para {url}...")
            
            try:
                response = requests.post(url, json=data)
                self.logger.info(f'Status da resposta: {response.status_code}')
                
                if response.status_code == 200:
                    # Converte a resposta em JSON e DataFrame
                    news_data = response.json()
                    df_api = pd.json_normalize(news_data)
                    self.logger.info(f"DataFrame criado com {len(df_api)} registros")
                    return df_api
                    
                elif response.status_code == 500 and retry_count < max_retries:
                    self.logger.warning(f"Erro 500 recebido para {url}. Tentando novamente em 5 segundos...")
                    time.sleep(5)
                    retry_count += 1
                    continue
                    
                else:
                    self.logger.error(f"Erro na requisição para {url}: {response.status_code}")
                    break
                    
            except requests.RequestException as e:
                self.logger.error(f"Erro de requisição para {url}: {str(e)}")
                break
        
        return None
    
    def _save_dataframes(self, final_df: pd.DataFrame):
        """
        Salva os DataFrames nos arquivos especificados
        """
        try:
            # Normaliza o campo Canais antes de salvar
            if 'Canais' in final_df.columns:
                self.logger.info("Normalizando campo Canais com mapeamentos de marcas...")
                final_df['Canais'] = final_df['Canais'].apply(self.config.normalize_channel_field)
                self.logger.info("Normalização do campo Canais concluída")
            
            # Salva o DataFrame completo
            final_df.to_excel(self.config.arq_api_original, index=False)
            self.logger.info(f"Arquivo salvo: {self.config.arq_api_original} - {final_df.shape[0]} registros")
            
            # Cria versão reduzida com colunas específicas
            required_cols_small = ['Id', 'Titulo', 'Conteudo', 'IdVeiculo', 'Canais']
            existing_cols_small = [col for col in required_cols_small if col in final_df.columns]
            
            if len(existing_cols_small) == len(required_cols_small):
                final_df_small = final_df[existing_cols_small].copy()
            else:
                missing_cols = list(set(required_cols_small) - set(existing_cols_small))
                self.logger.warning(f"Colunas não encontradas: {missing_cols}")
                final_df_small = pd.DataFrame(columns=required_cols_small)
            
            final_df_small.to_excel(self.config.arq_api, index=False)
            self.logger.info(f"Arquivo salvo: {self.config.arq_api} - {final_df_small.shape[0]} registros")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar arquivos: {str(e)}")
            raise