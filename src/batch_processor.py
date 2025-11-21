"""
Módulo responsável pelo processamento em lote dos dados consolidados
VERSÃO 2: Compatível com formato largo incluindo colunas de ocorrências e porta-vozes
"""

import pandas as pd
import logging
from datetime import datetime
from typing import Optional, List
from src.config_manager import ConfigManager

class BatchProcessor:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
    
    def process_batch(self, final_df_consolidado: pd.DataFrame, final_df: pd.DataFrame):
        """
        Processa os dados consolidados em lote
        VERSÃO 2: Funciona com formato largo incluindo colunas de ocorrências e porta-vozes
        """
        try:
            self.logger.info("Iniciando processamento em lote...")
            
            # Carrega DataFrame de lote baseado no consolidado
            df_lote = self._load_batch_data(final_df_consolidado)
            
            if df_lote.empty:
                self.logger.warning("Nenhum dado para processamento em lote")
                return
            
            self.logger.info(f"Quantidade inicial do arquivo de lote: {len(df_lote)}")
            
            # Processa consolidação por grupos
            df_lote_final = self._process_group_consolidation_largo(df_lote)
            
            if df_lote_final.empty:
                self.logger.error("Processamento de consolidação resultou em DataFrame vazio")
                return
            
            # Cria arquivo final limpo
            arquivo_final = self._create_final_clean_file_largo(df_lote_final, final_df)
            
            if arquivo_final:
                # Configura notificação de download
                arquivo_download = self._setup_download_notification(arquivo_final)
                
                if arquivo_download:
                    self.logger.info(f"Processamento em lote concluído com sucesso: {arquivo_final}")
                    self.logger.info(f"Arquivo disponível para download: {arquivo_download}")
                else:
                    self.logger.info(f"Processamento em lote concluído: {arquivo_final}")
            else:
                self.logger.error("Falha na criação do arquivo final")
                
        except Exception as e:
            self.logger.error(f"Erro durante processamento em lote: {str(e)}")
            raise
    
    def _load_batch_data(self, final_df_consolidado: pd.DataFrame) -> pd.DataFrame:
        """
        Carrega dados para processamento em lote baseado no DataFrame consolidado
        """
        # Usa diretamente o DataFrame consolidado
        df_lote = final_df_consolidado.copy()
        
        # Salva arquivo intermediário para diagnóstico
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_intermediario = f"{self.config.pasta_marca_setor}/Tabela_atualizacao_em_lote_{timestamp}.xlsx"
        
        try:
            df_lote.to_excel(arquivo_intermediario, index=False)
            self.logger.info(f"Arquivo intermediário salvo: {arquivo_intermediario}")
        except Exception as e:
            self.logger.warning(f"Não foi possível salvar arquivo intermediário: {str(e)}")
        
        return df_lote
    
    def _process_group_consolidation_largo(self, df_lote: pd.DataFrame) -> pd.DataFrame:
        """
        Processa consolidação por grupos no formato largo
        VERSÃO 2: Trabalha com colunas de protagonismo, porta-vozes e ocorrências por marca
        """
        self.logger.info("Processando consolidação em formato largo...")
        
        # Identifica colunas de protagonismo, porta-vozes e ocorrências
        colunas_protagonismo = [col for col in df_lote.columns if col.startswith('Nivel de Protagonismo')]
        colunas_portavoz = [col for col in df_lote.columns if col.startswith('Porta-Voz')]
        colunas_ocorrencias = [col for col in df_lote.columns if col.startswith('Ocorrencias')]
        
        self.logger.info(f"Colunas de protagonismo encontradas: {colunas_protagonismo}")
        self.logger.info(f"Colunas de porta-vozes encontradas: {colunas_portavoz}")
        self.logger.info(f"Colunas de ocorrências encontradas: {colunas_ocorrencias}")
        
        if not colunas_protagonismo:
            self.logger.error("Nenhuma coluna de protagonismo encontrada no formato esperado")
            return pd.DataFrame()
        
        # Para formato largo, não precisamos fazer agrupamento - já está consolidado
        # Apenas remove registros onde todas as marcas têm classificação nula
        registros_validos = []
        
        for index, row in df_lote.iterrows():
            tem_classificacao_valida = False
            
            for col_protagonismo in colunas_protagonismo:
                valor = row[col_protagonismo]
                if pd.notna(valor) and valor not in ['Nenhum Nível Encontrado', 'Erro na API', 'Erro de Processamento']:
                    tem_classificacao_valida = True
                    break
            
            if tem_classificacao_valida:
                registros_validos.append(index)
        
        df_lote_final = df_lote.loc[registros_validos].copy()
        
        self.logger.info(f"Registros válidos após consolidação: {len(df_lote_final)} de {len(df_lote)}")
        
        # Log das estatísticas por marca
        self._log_batch_statistics_largo(df_lote_final, colunas_protagonismo, colunas_portavoz, colunas_ocorrencias)
        
        return df_lote_final
    
    def _log_batch_statistics_largo(self, df_lote: pd.DataFrame, colunas_protagonismo: List[str], colunas_portavoz: List[str], colunas_ocorrencias: List[str]):
        """
        Registra estatísticas do processamento em lote para formato largo
        VERSÃO 2: Inclui estatísticas de porta-vozes
        """
        self.logger.info("=== ESTATÍSTICAS DO BATCH PROCESSING ===")
        
        for col_protagonismo in colunas_protagonismo:
            # Extrai nome da marca da coluna
            marca = col_protagonismo.replace('Nivel de Protagonismo ', '')
            col_portavoz = f'Porta-Voz {marca}'
            col_ocorrencias = f'Ocorrencias {marca}'
            
            # Conta classificações válidas
            classificacoes_validas = df_lote[col_protagonismo].dropna()
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
                
                # NOVO: Estatísticas de porta-vozes se a coluna existir
                if col_portavoz in df_lote.columns:
                    portavozes_validos = df_lote[col_portavoz].dropna()
                    if len(portavozes_validos) > 0:
                        self.logger.info(f"  - Notícias com porta-voz identificado: {len(portavozes_validos)}")
                    else:
                        self.logger.info(f"  - Nenhum porta-voz identificado")
                
                # Estatísticas de ocorrências se a coluna existir
                if col_ocorrencias in df_lote.columns:
                    ocorrencias_validas = df_lote[col_ocorrencias].dropna()
                    if len(ocorrencias_validas) > 0:
                        total_ocorrencias = ocorrencias_validas.sum()
                        media_ocorrencias = ocorrencias_validas.mean()
                        self.logger.info(f"  - Total de ocorrências: {int(total_ocorrencias)}")
                        self.logger.info(f"  - Média de ocorrências: {media_ocorrencias:.2f}")
            else:
                self.logger.info(f"{marca}: Nenhuma classificação válida")
    
    def _create_final_clean_file_largo(self, df_lote_final: pd.DataFrame, final_df: pd.DataFrame) -> Optional[str]:
        """
        Cria o arquivo final limpo para formato largo
        VERSÃO 2: Trabalha com colunas de protagonismo, porta-vozes e ocorrências
        """
        try:
            # Identifica todas as colunas disponíveis
            colunas_base = ['Id', 'UrlVisualizacao', 'UrlOriginal', 'Titulo']
            colunas_protagonismo = [col for col in df_lote_final.columns if col.startswith('Nivel de Protagonismo')]
            colunas_ocorrencias = [col for col in df_lote_final.columns if col.startswith('Ocorrencias')]
            
            # Monta lista de colunas para o arquivo final
            colunas_finais = []
            
            # Adiciona colunas base se existirem
            for col in colunas_base:
                if col in df_lote_final.columns:
                    colunas_finais.append(col)
            
            # Adiciona colunas de protagonismo e ocorrências intercaladas por marca
            marcas_processadas = set()
            for col_protagonismo in colunas_protagonismo:
                marca = col_protagonismo.replace('Nivel de Protagonismo ', '')
                if marca not in marcas_processadas:
                    colunas_finais.append(col_protagonismo)
                    
                    # NOVO: Adiciona coluna de porta-voz correspondente se existir
                    col_portavoz = f'Porta-Voz {marca}'
                    if col_portavoz in df_lote_final.columns:
                        colunas_finais.append(col_portavoz)
                    
                    # Adiciona coluna de ocorrências correspondente se existir
                    col_ocorrencias = f'Ocorrencias {marca}'
                    if col_ocorrencias in df_lote_final.columns:
                        colunas_finais.append(col_ocorrencias)
                    
                    marcas_processadas.add(marca)
            
            self.logger.info(f"Colunas disponíveis em df_lote_final: {list(df_lote_final.columns)}")
            self.logger.info(f"Colunas para arquivo final: {colunas_finais}")
            
            if not colunas_finais:
                self.logger.error("Nenhuma coluna válida encontrada para o arquivo final")
                return None
            
            # Verifica se colunas base estão faltando
            colunas_faltantes = [col for col in colunas_base if col not in df_lote_final.columns]
            if colunas_faltantes:
                self.logger.info(f"Adicionando colunas {', '.join(colunas_faltantes)}...")
                
                # Faz merge com final_df para adicionar colunas faltantes
                colunas_para_merge = ['Id'] + [col for col in colunas_faltantes if col in final_df.columns]
                
                if len(colunas_para_merge) > 1:  # Se tem Id + pelo menos uma coluna faltante
                    df_lote_final = df_lote_final.merge(
                        final_df[colunas_para_merge],
                        on='Id',
                        how='left',
                        suffixes=('', '_from_original')
                    )
                    
                    # Atualiza lista de colunas finais
                    colunas_finais = []
                    for col in colunas_base:
                        if col in df_lote_final.columns:
                            colunas_finais.append(col)
                    
                    # Re-adiciona colunas de protagonismo, porta-vozes e ocorrências
                    for col_protagonismo in colunas_protagonismo:
                        if col_protagonismo in df_lote_final.columns:
                            colunas_finais.append(col_protagonismo)
                            
                            marca = col_protagonismo.replace('Nivel de Protagonismo ', '')
                            
                            # NOVO: Adiciona porta-voz
                            col_portavoz = f'Porta-Voz {marca}'
                            if col_portavoz in df_lote_final.columns:
                                colunas_finais.append(col_portavoz)
                            
                            # Adiciona ocorrências
                            col_ocorrencias = f'Ocorrencias {marca}'
                            if col_ocorrencias in df_lote_final.columns:
                                colunas_finais.append(col_ocorrencias)
            
            # Cria DataFrame final com colunas ordenadas
            df_lote_final_limpo = df_lote_final[colunas_finais].copy()
            
            # Gera timestamp e salva arquivos
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Arquivo simples (Excel sem formatação)
            arquivo_simples = f"{self.config.pasta_marca_setor}/Tabela_atualizacao_em_lote_limpo_{timestamp}.xlsx"
            df_lote_final_limpo.to_excel(arquivo_simples, index=False)
            self.logger.info(f"Arquivo simples salvo: {arquivo_simples}")
            
            # Arquivo com hyperlinks (se UrlVisualizacao existe)
            if 'UrlVisualizacao' in df_lote_final_limpo.columns:
                arquivo_hyperlinks = f"{self.config.pasta_marca_setor}/Tabela_atualizacao_em_lote_limpo_hyperlinks_{timestamp}.xlsx"
                self._save_with_hyperlinks_largo(df_lote_final_limpo, arquivo_hyperlinks)
            
            return arquivo_simples
            
        except Exception as e:
            self.logger.error(f"Erro ao criar arquivo final: {str(e)}")
            return None
    
    def _setup_download_notification(self, arquivo_path: str):
        """
        Configura notificação de download e copia arquivo para pasta downloads
        """
        try:
            import shutil
            from pathlib import Path
            
            # Cria pasta downloads se não existir
            downloads_dir = Path("downloads")
            downloads_dir.mkdir(exist_ok=True)
            
            arquivo_origem = Path(arquivo_path)
            if arquivo_origem.exists():
                arquivo_destino = downloads_dir / arquivo_origem.name
                shutil.copy2(arquivo_origem, arquivo_destino)
                
                self.logger.info(f"Arquivo disponível para download em: {arquivo_destino}")
                
                # Exibe mensagem de download
                print(f"\n{'='*60}")
                print("📥 ARQUIVO PRONTO PARA DOWNLOAD")
                print(f"{'='*60}")
                print(f"Arquivo: {arquivo_origem.name}")
                print(f"Localização: {arquivo_destino.absolute()}")
                print(f"Tamanho: {arquivo_origem.stat().st_size:,} bytes")
                print(f"\nO arquivo foi copiado para a pasta 'downloads' e está")
                print(f"disponível para download no seu ambiente Docker.")
                print(f"{'='*60}\n")
                
                return str(arquivo_destino)
            else:
                self.logger.error(f"Arquivo não encontrado para download: {arquivo_path}")
                return None
                
        except Exception as e:
            self.logger.error(f"Erro ao configurar download: {str(e)}")
            return None
    
    def _save_with_hyperlinks_largo(self, df: pd.DataFrame, filename: str):
        """
        Salva DataFrame com hyperlinks na coluna UrlVisualizacao
        CORRIGIDO: Sintaxe correta do xlsxwriter
        """
        try:
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Sheet1', index=False)
                
                # Acessa workbook e worksheet corretamente
                workbook = writer.book
                worksheet = writer.sheets['Sheet1']
                
                # Cria formato para hyperlinks
                url_format = workbook.add_format({
                    'font_color': 'blue',
                    'underline': 1
                })
                
                # Encontra índice da coluna UrlVisualizacao
                if 'UrlVisualizacao' in df.columns:
                    url_col_idx = df.columns.get_loc('UrlVisualizacao')
                    
                    # Aplica hyperlinks
                    for row_idx, url in enumerate(df['UrlVisualizacao'], start=1):  # start=1 pula header
                        if pd.notna(url) and str(url).startswith('http'):
                            worksheet.write_url(row_idx, url_col_idx, str(url), url_format, 'Link')
                
                self.logger.info(f"Arquivo com hyperlinks salvo: {filename}")
                
        except Exception as e:
            self.logger.error(f"Erro ao salvar arquivo com hyperlinks: {str(e)}")
            # Fallback: salva como arquivo Excel simples
            df.to_excel(filename.replace('_hyperlinks', '_simples'), index=False)
    
    # === MÉTODOS ANTIGOS MANTIDOS PARA COMPATIBILIDADE ===
    def _process_group_consolidation(self, df_lote: pd.DataFrame) -> pd.DataFrame:
        """
        MÉTODO ORIGINAL MANTIDO PARA COMPATIBILIDADE
        Redireciona para o novo método de formato largo
        """
        self.logger.warning("Método _process_group_consolidation antigo foi chamado. Redirecionando para formato largo.")
        return self._process_group_consolidation_largo(df_lote)
    
    def _create_final_clean_file(self, df_lote_final: pd.DataFrame, final_df: pd.DataFrame) -> Optional[str]:
        """
        MÉTODO ORIGINAL MANTIDO PARA COMPATIBILIDADE
        Redireciona para o novo método de formato largo
        """
        self.logger.warning("Método _create_final_clean_file antigo foi chamado. Redirecionando para formato largo.")
        return self._create_final_clean_file_largo(df_lote_final, final_df)