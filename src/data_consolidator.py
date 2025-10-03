"""
Módulo responsável pela consolidação dos dados de protagonismo
VERSÃO ATUALIZADA: Compatível com formato largo incluindo colunas de ocorrências
"""

import pandas as pd
import logging
from typing import List, Dict
from src.config_manager import ConfigManager

class DataConsolidator:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
    
    def consolidate_data(self, final_df: pd.DataFrame, df_resultados: pd.DataFrame) -> pd.DataFrame:
        """
        Consolida os dados de notícias com os resultados de protagonismo
        ATUALIZADO: Funciona com formato largo incluindo colunas de ocorrências
        """
        try:
            self.logger.info("Iniciando consolidação de dados...")
            self.logger.info(f"DataFrame de notícias: {len(final_df)} registros")
            self.logger.info(f"DataFrame de resultados: {len(df_resultados)} registros")
            
            # Verifica se é formato largo ou antigo
            if self._is_formato_largo(df_resultados):
                self.logger.info("Detectado formato largo - processando adequadamente")
                final_df_consolidado = self._consolidate_formato_largo(final_df, df_resultados)
            else:
                self.logger.info("Detectado formato antigo - convertendo para formato largo")
                final_df_consolidado = self._consolidate_formato_antigo(final_df, df_resultados)
            
            # Aplica filtros finais
            self.logger.info("Aplicando filtros finais...")
            final_df_consolidado = self._apply_final_filters(final_df_consolidado)
            
            # Salva o resultado consolidado
            self._save_consolidated_data(final_df_consolidado)
            
            self.logger.info(f"Consolidação concluída: {len(final_df_consolidado)} registros finais")
            return final_df_consolidado
            
        except Exception as e:
            self.logger.error(f"Erro durante consolidação: {str(e)}")
            raise
    
    def _is_formato_largo(self, df_resultados: pd.DataFrame) -> bool:
        """
        Verifica se o DataFrame está no formato largo (colunas separadas por marca)
        ATUALIZADO: Considera também colunas de ocorrências
        """
        # Verifica se existem colunas no padrão "Nivel de Protagonismo {Marca}"
        colunas_protagonismo = [col for col in df_resultados.columns 
                               if col.startswith('Nivel de Protagonismo')]
        
        # Verifica se existem colunas de ocorrências
        colunas_ocorrencias = [col for col in df_resultados.columns 
                              if col.startswith('Ocorrencias')]
        
        # É formato largo se tem pelo menos uma coluna de protagonismo
        is_largo = len(colunas_protagonismo) > 0
        
        self.logger.info(f"Colunas de protagonismo encontradas: {colunas_protagonismo}")
        self.logger.info(f"Colunas de ocorrências encontradas: {colunas_ocorrencias}")
        
        return is_largo
    
    def _consolidate_formato_largo(self, final_df: pd.DataFrame, df_resultados: pd.DataFrame) -> pd.DataFrame:
        """
        Consolida dados quando o resultado está no formato largo
        ATUALIZADO: Processa colunas de ocorrências
        """
        self.logger.info("Processando consolidação no formato largo...")
        
        # O df_resultados já está no formato correto - apenas fazemos merge se necessário
        # Verifica se as colunas básicas estão presentes
        colunas_basicas = ['Id', 'UrlVisualizacao', 'UrlOriginal', 'Titulo']
        colunas_faltantes = [col for col in colunas_basicas if col not in df_resultados.columns]
        
        if colunas_faltantes:
            self.logger.warning(f"Colunas básicas faltantes no resultado: {colunas_faltantes}")
            # Faz merge para adicionar colunas faltantes do final_df
            df_resultados = df_resultados.merge(
                final_df[['Id'] + [col for col in colunas_faltantes if col in final_df.columns]], 
                on='Id', 
                how='left',
                suffixes=('', '_from_original')
            )
        
        # Remove registros onde todas as marcas têm classificação nula
        marcas = self.config.w_marcas
        colunas_nivel = [f'Nivel de Protagonismo {marca}' for marca in marcas]
        
        # Identifica registros que têm pelo menos uma marca com classificação válida
        registros_validos = []
        for index, row in df_resultados.iterrows():
            tem_classificacao_valida = False
            for coluna_nivel in colunas_nivel:
                if coluna_nivel in df_resultados.columns:
                    valor = row[coluna_nivel]
                    if pd.notna(valor) and valor not in ['Nenhum Nível Encontrado', 'Erro na API', 'Erro de Processamento']:
                        tem_classificacao_valida = True
                        break
            
            if tem_classificacao_valida:
                registros_validos.append(index)
        
        # Filtra apenas registros válidos
        df_resultados_filtrado = df_resultados.loc[registros_validos].copy()
        
        self.logger.info(f"Registros com classificação válida: {len(df_resultados_filtrado)} de {len(df_resultados)}")
        
        # Log das estatísticas por marca
        self._log_consolidation_statistics_largo(df_resultados_filtrado, marcas)
        
        return df_resultados_filtrado
    
    def _log_consolidation_statistics_largo(self, df_resultados: pd.DataFrame, marcas: List[str]):
        """
        Registra estatísticas da consolidação para formato largo
        NOVO: Inclui estatísticas das colunas de ocorrências
        """
        self.logger.info("=== ESTATÍSTICAS DA CONSOLIDAÇÃO ===")
        
        for marca in marcas:
            nivel_col = f'Nivel de Protagonismo {marca}'
            ocorrencias_col = f'Ocorrencias {marca}'
            
            if nivel_col in df_resultados.columns:
                # Conta classificações por nível
                classificacoes_validas = df_resultados[nivel_col].dropna()
                classificacoes_validas = classificacoes_validas[
                    ~classificacoes_validas.isin(['Nenhum Nível Encontrado', 'Erro na API', 'Erro de Processamento'])
                ]
                
                if len(classificacoes_validas) > 0:
                    # Conta por nível
                    contagem_niveis = classificacoes_validas.value_counts()
                    
                    self.logger.info(f"{marca}:")
                    self.logger.info(f"  - Total de notícias classificadas: {len(classificacoes_validas)}")
                    
                    for nivel, quantidade in contagem_niveis.items():
                        self.logger.info(f"  - {nivel}: {quantidade} notícias")
                    
                    # Estatísticas de ocorrências se a coluna existir
                    if ocorrencias_col in df_resultados.columns:
                        ocorrencias_validas = df_resultados[ocorrencias_col].dropna()
                        if len(ocorrencias_validas) > 0:
                            total_ocorrencias = ocorrencias_validas.sum()
                            media_ocorrencias = ocorrencias_validas.mean()
                            self.logger.info(f"  - Total de ocorrências: {int(total_ocorrencias)}")
                            self.logger.info(f"  - Média de ocorrências: {media_ocorrencias:.2f}")
                        else:
                            self.logger.info(f"  - Nenhuma ocorrência registrada")
                else:
                    self.logger.info(f"{marca}: Nenhuma classificação válida")
    
    def _consolidate_formato_antigo(self, final_df: pd.DataFrame, df_resultados: pd.DataFrame) -> pd.DataFrame:
        """
        Consolida dados quando o resultado está no formato antigo (lista)
        MANTIDO PARA COMPATIBILIDADE: Converte para formato largo
        """
        self.logger.info("Convertendo formato antigo para formato largo...")
        
        # Converte formato antigo para largo
        df_largo = self._convert_antigo_para_largo(df_resultados, final_df)
        
        # Processa como formato largo
        return self._consolidate_formato_largo(final_df, df_largo)
    
    def _convert_antigo_para_largo(self, df_resultados: pd.DataFrame, final_df: pd.DataFrame) -> pd.DataFrame:
        """
        Converte formato antigo (lista com Id, Marca, Nivel) para formato largo
        ATUALIZADO: Inicializa colunas de ocorrências (mas não preenche - seria necessário reprocessamento)
        """
        self.logger.info("Convertendo dados do formato antigo para formato largo...")
        
        # Cria DataFrame base com informações das notícias
        colunas_base = ['Id', 'UrlVisualizacao', 'UrlOriginal', 'Titulo']
        resultado_df = final_df[colunas_base].copy()
        
        # Adiciona colunas para cada marca
        for marca in self.config.w_marcas:
            resultado_df[f'Nivel de Protagonismo {marca}'] = None
            resultado_df[f'Ocorrencias {marca}'] = None  # Não preenchido no formato antigo
        
        # Preenche os dados de protagonismo
        for _, row in df_resultados.iterrows():
            noticia_id = row['Id']
            marca = row['Marca']
            nivel = row['Nivel']
            
            mask = resultado_df['Id'] == noticia_id
            col_nivel = f'Nivel de Protagonismo {marca}'
            
            if col_nivel in resultado_df.columns:
                resultado_df.loc[mask, col_nivel] = nivel
        
        self.logger.warning("ATENÇÃO: Colunas de ocorrências não foram preenchidas na conversão do formato antigo.")
        self.logger.warning("Para ter contagem de ocorrências, é necessário reprocessar com o novo protagonismo_analyzer.py")
        
        return resultado_df
    
    def _apply_final_filters(self, final_df_consolidado: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica filtros finais antes da gravação
        ATUALIZADO: Funciona com formato largo
        """
        self.logger.info("Aplicando filtragem antes da gravação...")
        self.logger.info(f"Registros antes da filtragem: {len(final_df_consolidado)}")
        
        # Para formato largo, verifica se existe pelo menos uma classificação válida por linha
        marcas = self.config.w_marcas
        indices_para_manter = []
        
        for index, row in final_df_consolidado.iterrows():
            tem_classificacao_valida = False
            
            for marca in marcas:
                nivel_col = f'Nivel de Protagonismo {marca}'
                if nivel_col in final_df_consolidado.columns:
                    valor = row[nivel_col]
                    if pd.notna(valor) and valor not in ['Nenhum Nível Encontrado', 'Erro na API', 'Erro de Processamento', 'NÃO', '']:
                        tem_classificacao_valida = True
                        break
            
            if tem_classificacao_valida:
                indices_para_manter.append(index)
        
        # Filtra o DataFrame
        final_df_consolidado_filtrado = final_df_consolidado.loc[indices_para_manter].copy()
        
        self.logger.info(f"Registros após filtragem: {len(final_df_consolidado_filtrado)}")
        
        return final_df_consolidado_filtrado
    
    def _save_consolidated_data(self, final_df_consolidado: pd.DataFrame):
        """
        Salva os dados consolidados
        CORRIGIDO: Usa self.config.arq_consolidado em vez de get_output_path()
        """
        try:
            # Log antes de salvar
            self.logger.info("=== SALVANDO DADOS CONSOLIDADOS ===")
            self.logger.info(f"Registros a salvar: {len(final_df_consolidado)}")
            self.logger.info(f"Colunas: {list(final_df_consolidado.columns)}")
            
            # Salva usando o caminho correto do ConfigManager
            final_df_consolidado.to_excel(self.config.arq_consolidado, index=False)
            self.logger.info(f"Dados consolidados salvos: {self.config.arq_consolidado}")
            
            # Cria também uma cópia na pasta downloads para facilitar acesso
            try:
                import shutil
                from pathlib import Path
                
                downloads_dir = Path("downloads")
                downloads_dir.mkdir(exist_ok=True)
                
                arquivo_consolidado = Path(self.config.arq_consolidado)
                if arquivo_consolidado.exists():
                    arquivo_download = downloads_dir / arquivo_consolidado.name
                    shutil.copy2(arquivo_consolidado, arquivo_download)
                    self.logger.info(f"Cópia para download criada: {arquivo_download}")
                    
            except Exception as e:
                self.logger.warning(f"Não foi possível criar cópia para download: {str(e)}")
            
            # Log de verificação das colunas de ocorrências
            colunas_ocorrencias = [col for col in final_df_consolidado.columns if 'Ocorrencias' in col]
            if colunas_ocorrencias:
                self.logger.info(f"Colunas de ocorrências salvas: {colunas_ocorrencias}")
                
                # Verifica se há dados nas colunas de ocorrências
                for col in colunas_ocorrencias:
                    dados_nao_nulos = final_df_consolidado[col].notna().sum()
                    if dados_nao_nulos > 0:
                        total_ocorrencias = final_df_consolidado[col].sum()
                        self.logger.info(f"  - {col}: {dados_nao_nulos} registros preenchidos, total: {int(total_ocorrencias)}")
                    else:
                        self.logger.warning(f"  - {col}: Nenhum dado preenchido")
            else:
                self.logger.warning("Nenhuma coluna de ocorrências encontrada no arquivo final")
                
        except Exception as e:
            self.logger.error(f"Erro ao salvar dados consolidados: {str(e)}")
            raise