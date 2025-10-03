"""
Módulo responsável pela análise de protagonismo usando DeepSeek API
Adaptado do código original removendo filtros específicos do iFood
VERSÃO ATUALIZADA: Inclui contagem de ocorrências das marcas
"""

import pandas as pd
import requests
import time
import re
import logging
from datetime import datetime
from typing import List, Dict
from src.config_manager import ConfigManager

class ProtagonismoAnalyzer:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self.headers = config_manager.get_api_headers()
    
    def analyze_protagonismo(self, final_df: pd.DataFrame) -> pd.DataFrame:
        """
        Analisa o nível de protagonismo para cada notícia e marca
        ATUALIZADO: Inclui contagem de ocorrências no formato largo
        """
        try:
            # Carrega a tabela de protagonismo
            df_protagonismo = self._load_protagonismo_table()
            
            if df_protagonismo.empty:
                self.logger.error("Tabela de protagonismo não pôde ser carregada")
                return pd.DataFrame()
            
            # Processa notícias no formato largo com contagem de ocorrências
            df_resultados = self._process_noticias_formato_largo(final_df, df_protagonismo)
            
            if not df_resultados.empty:
                self.logger.info(f"Análise concluída: {len(df_resultados)} notícias processadas")
                
                # Aplica substituições dos níveis
                df_resultados = self._apply_nivel_substitutions_largo(df_resultados)
                
                # Salva resultados
                self._save_results_largo(df_resultados)
            
            return df_resultados
            
        except Exception as e:
            self.logger.error(f"Erro durante análise de protagonismo: {str(e)}")
            raise
    
    def _load_protagonismo_table(self) -> pd.DataFrame:
        """
        Carrega a tabela de níveis de protagonismo
        """
        try:
            df_protagonismo = pd.read_excel(self.config.arq_protagonismo)
            self.logger.info(f"Tabela de protagonismo carregada: {self.config.arq_protagonismo}")
            
            if 'Nivel' not in df_protagonismo.columns or 'Conceito' not in df_protagonismo.columns:
                self.logger.error("Tabela de protagonismo não contém as colunas necessárias ('Nivel', 'Conceito')")
                return pd.DataFrame()
            
            return df_protagonismo
            
        except FileNotFoundError:
            self.logger.error(f"Arquivo de protagonismo não encontrado: {self.config.arq_protagonismo}")
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Erro ao carregar tabela de protagonismo: {str(e)}")
            return pd.DataFrame()
    
    def _count_marca_occurrences(self, marca: str, titulo: str, conteudo: str) -> int:
        """
        Conta quantas vezes a marca aparece no texto (título + conteúdo)
        
        Args:
            marca: Nome da marca a ser contada
            titulo: Título da notícia
            conteudo: Conteúdo da notícia
        
        Returns:
            int: Número de ocorrências encontradas
        """
        # Combinar título e conteúdo
        texto_completo = f"{titulo} {conteudo}".lower()
        marca_lower = marca.lower()
        
        # Usar regex com word boundary para evitar contagens incorretas
        # Ex: "Bradesco" não deve contar em "Bradescoprev"
        pattern = r'\b' + re.escape(marca_lower) + r'\b'
        matches = re.findall(pattern, texto_completo)
        
        return len(matches)
    
    def _process_noticias_formato_largo(self, final_df: pd.DataFrame, df_protagonismo: pd.DataFrame) -> pd.DataFrame:
        """
        Processa cada notícia para análise de protagonismo e contagem de ocorrências
        ATUALIZADO: Retorna DataFrame no formato largo com colunas de ocorrências
        """
        required_columns = ['Id', 'Titulo', 'Conteudo', 'Canais']
        
        if not all(col in final_df.columns for col in required_columns):
            self.logger.error(f"Colunas necessárias não encontradas: {required_columns}")
            return pd.DataFrame()
        
        # Verificar se as colunas base existem no DataFrame de entrada
        colunas_base_necessarias = ['Id', 'UrlVisualizacao', 'UrlOriginal', 'Titulo']
        colunas_disponiveis = [col for col in colunas_base_necessarias if col in final_df.columns]
        colunas_faltantes = [col for col in colunas_base_necessarias if col not in final_df.columns]
        
        if colunas_faltantes:
            self.logger.warning(f"Colunas base faltantes no DataFrame de entrada: {colunas_faltantes}")
            # Adicionar colunas faltantes com valores padrão
            for col in colunas_faltantes:
                final_df[col] = ""
            self.logger.info(f"Colunas faltantes adicionadas com valores vazios: {colunas_faltantes}")
        
        # Criar DataFrame resultado com TODAS as colunas base
        resultado_df = final_df[colunas_base_necessarias].copy()
        
        # Adicionar colunas para cada marca ANTES do processamento
        for marca in self.config.w_marcas:
            resultado_df[f'Nivel de Protagonismo {marca}'] = None
            resultado_df[f'Ocorrencias {marca}'] = None  # Inicializa como None para indicar "não processado"
        
        self.logger.info(f"DataFrame resultado criado com {len(resultado_df)} registros")
        self.logger.info(f"Colunas criadas para as marcas: {self.config.w_marcas}")
        self.logger.info("Avaliando nível de protagonismo para cada notícia e marca...")
        
        # Contador para estatísticas
        total_noticias = len(final_df)
        noticias_processadas = 0
        noticias_filtradas = 0
        classificacoes_automaticas = 0
        chamadas_deepseek = 0
        
        for index, row in final_df.iterrows():
            noticia_id = row['Id']
            titulo_noticia = str(row['Titulo']).strip()
            conteudo_noticia = str(row['Conteudo']).strip()
            canais_noticia = str(row['Canais']).strip()
            
            # Combina título e conteúdo
            texto_completo_noticia = f"Título: {titulo_noticia}\n\nConteúdo: {conteudo_noticia}"
            
            if not texto_completo_noticia.strip():
                self.logger.warning(f"Pulando notícia ID {noticia_id}: Título e Conteúdo vazios")
                continue
            
            # Verifica se pelo menos uma das marcas está presente no campo Canais
            marcas_no_canal = []
            for marca in self.config.w_marcas:
                if re.search(r'\b' + re.escape(marca.lower()) + r'\b', canais_noticia.lower()):
                    marcas_no_canal.append(marca)
            
            # Se nenhuma marca foi encontrada no campo Canais, pula a notícia
            if not marcas_no_canal:
                noticias_filtradas += 1
                self.logger.debug(f"Notícia ID {noticia_id} filtrada - nenhuma marca encontrada no campo Canais: {canais_noticia}")
                continue
            
            noticias_processadas += 1
            self.logger.info(f"Processando notícia ID {noticia_id} - Marcas encontradas no canal: {marcas_no_canal}")
            
            # Processa apenas as marcas encontradas no campo Canais
            for marca in marcas_no_canal:
                self.logger.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Avaliando notícia ID {noticia_id} para a marca: {marca}")
                
                # Verifica se a marca aparece no título
                if re.search(r'\b' + re.escape(marca.lower()) + r'\b', titulo_noticia.lower()):
                    self.logger.info(f"Marca '{marca}' encontrada no título - Classificação automática: Dedicada")
                    nivel_detectado = 'Nível 1'  # Dedicada
                    classificacoes_automaticas += 1
                else:
                    # Verifica regras específicas de conteúdo
                    content_check = self.config.check_specific_content_requirements(canais_noticia, texto_completo_noticia)
                    
                    if content_check['should_be_minimum_citation'] and marca == 'Bradesco':
                        specific_terms_info = content_check['found_specific_terms']
                        self.logger.info(f"Termos específicos encontrados para Bradesco: {[t['content_term'] for t in specific_terms_info]}")
                    
                    # Faz análise completa com DeepSeek
                    nivel_detectado = self._analyze_single_news_marca(
                        texto_completo_noticia, marca, df_protagonismo, noticia_id, 
                        canais_noticia, content_check
                    )
                    chamadas_deepseek += 1
                    # Pausa para evitar sobrecarregar a API
                    time.sleep(1)
                
                # === NOVO: PÓS-PROCESSAMENTO PARA CONTAGEM DE OCORRÊNCIAS ===
                contagem_ocorrencias = 0
                if nivel_detectado not in ['Nenhum Nível Encontrado', 'Erro na API', 'Erro de Processamento']:
                    # Só conta ocorrências se houve classificação válida de protagonismo
                    contagem_ocorrencias = self._count_marca_occurrences(marca, titulo_noticia, conteudo_noticia)
                    self.logger.info(f"Marca {marca} - Contagem de ocorrências: {contagem_ocorrencias}")
                
                # Atualizar DataFrame resultado no formato largo
                mask = resultado_df['Id'] == noticia_id
                resultado_df.loc[mask, f'Nivel de Protagonismo {marca}'] = nivel_detectado
                
                # NOVO: Só preenche a contagem se houve classificação válida
                if nivel_detectado not in ['Nenhum Nível Encontrado', 'Erro na API', 'Erro de Processamento']:
                    resultado_df.loc[mask, f'Ocorrencias {marca}'] = contagem_ocorrencias
                
                self.logger.info(f"Notícia ID {noticia_id}, Marca {marca}: "
                               f"Nível='{nivel_detectado}', Ocorrências={contagem_ocorrencias if contagem_ocorrencias > 0 else 'N/A'}")
        
        # Log de estatísticas finais
        self.logger.info(f"Estatísticas do processamento:")
        self.logger.info(f"- Total de notícias na base: {total_noticias}")
        self.logger.info(f"- Notícias processadas (com marcas no canal): {noticias_processadas}")
        self.logger.info(f"- Notícias filtradas (sem marcas no canal): {noticias_filtradas}")
        self.logger.info(f"- Classificações automáticas (marca no título): {classificacoes_automaticas}")
        self.logger.info(f"- Chamadas enviadas ao DeepSeek: {chamadas_deepseek}")
        
        # Correção pós-processamento no formato largo
        resultado_df = self._correct_missing_classifications_largo(resultado_df, final_df)
        
        # Log final das estatísticas de ocorrências
        self._log_ocorrencias_statistics(resultado_df)
        
        return resultado_df
    
    def _log_ocorrencias_statistics(self, df_resultados: pd.DataFrame):
        """
        Registra estatísticas das contagens de ocorrências
        """
        self.logger.info("=== ESTATÍSTICAS DE OCORRÊNCIAS ===")
        
        for marca in self.config.w_marcas:
            nivel_col = f'Nivel de Protagonismo {marca}'
            ocorrencias_col = f'Ocorrencias {marca}'
            
            if nivel_col in df_resultados.columns and ocorrencias_col in df_resultados.columns:
                # Conta quantas notícias têm classificação para esta marca
                com_classificacao = df_resultados[nivel_col].notna().sum()
                
                # Conta quantas têm contagem de ocorrências preenchida
                com_contagem = df_resultados[ocorrencias_col].notna().sum()
                
                if com_contagem > 0:
                    # Calcula estatísticas das ocorrências
                    ocorrencias_validas = df_resultados[ocorrencias_col].dropna()
                    total_ocorrencias = ocorrencias_validas.sum()
                    media_ocorrencias = ocorrencias_validas.mean()
                    min_ocorrencias = ocorrencias_validas.min()
                    max_ocorrencias = ocorrencias_validas.max()
                    
                    self.logger.info(f"{marca}:")
                    self.logger.info(f"  - Notícias com classificação: {com_classificacao}")
                    self.logger.info(f"  - Notícias com contagem: {com_contagem}")
                    self.logger.info(f"  - Total de ocorrências: {int(total_ocorrencias)}")
                    self.logger.info(f"  - Média de ocorrências: {media_ocorrencias:.2f}")
                    self.logger.info(f"  - Min/Max ocorrências: {int(min_ocorrencias)}/{int(max_ocorrencias)}")
                else:
                    self.logger.info(f"{marca}: Nenhuma notícia com contagem de ocorrências")
    
    def _analyze_single_news_marca(self, texto_noticia: str, marca: str, 
                                  df_protagonismo: pd.DataFrame, noticia_id: int,
                                  canais_noticia: str = "", content_check: dict = None) -> str:
        """
        Analisa uma única notícia para uma marca específica
        """
        # Constrói informações sobre verificações específicas
        specific_requirements = ""
        if content_check and content_check.get('should_be_minimum_citation') and marca == 'Bradesco':
            found_terms = [t['content_term'] for t in content_check['found_specific_terms']]
            specific_requirements = f"""
        
        VERIFICAÇÃO ESPECÍFICA PARA BRADESCO:
        Os seguintes termos específicos foram encontrados no conteúdo: {', '.join(found_terms)}
        Devido a essa verificação específica, esta notícia deve ser classificada no MÍNIMO como "Nível 3" (Citação).
        """
        
        # Prepara o prompt para o DeepSeek
        prompt_texto = f"""
        Analise o seguinte texto de notícia e determine o nível de protagonismo da marca "{marca}".

        NÍVEIS DE PROTAGONISMO:

        **Nível 1 - Dedicada:**
        - A marca é o foco principal da matéria
        - Destacada no título, subtítulo ou lead
        - Exemplo: "Bradesco revoluciona o mercado financeiro com nova tecnologia"

        **Nível 2 - Conteúdo:**
        - Menção significativa da marca, mas sem ser o foco ou referência primária
        - A marca tem papel relevante mas não é o protagonista principal da notícia
        
        a) **Comparação equilibrada com concorrentes:**
        - A marca é mencionada em matérias com o mesmo peso dos concorrentes, como ponto de comparação
        - Exemplo: "O Santander saiu na frente no dia 30 de abril, com um resultado dentro do esperado. Agora, os holofotes se voltam para Bradesco e Itaú."

        **Nível 3 - Citação:**
        Este nível abrange três situações distintas:
        
        a) **Comparação com concorrentes (marca secundária):**
        - A marca é mencionada em matérias focadas no concorrente, como ponto de comparação
        - A marca tem papel secundário na narrativa
        - Exemplo: Matéria focada no Itaú menciona o Bradesco para comparar estratégias
        
        b) **Referência setorial:**
        - A marca ou seus porta-vozes são citados como referência no setor ou sobre tema específico
        - Através de declarações ou dados fornecidos pela empresa
        - Exemplo: "Segundo o Bradesco, o número de empréstimos em São Paulo cresceu 20% no último ano"
        
        c) **Menção tangencial:**
        - Menção onde a presença da marca não é crucial para a matéria
        - Exemplo: "Empresas inovadoras como iFood, Nubank, Bradesco, e outras..."

        REGRA IMPORTANTE: Se a marca "{marca}" for mencionada de QUALQUER FORMA no texto, ela deve ser classificada no MÍNIMO como "Nível 3" (Citação).
        {specific_requirements}
        APENAS responda "Nenhum Nível Encontrado" se a marca "{marca}" NÃO aparecer de forma alguma no texto.

        Analise o texto abaixo e responda SOMENTE com: "Nível 1", "Nível 2", "Nível 3" ou "Nenhum Nível Encontrado".

        Texto da Notícia:
        {texto_noticia}
        """

        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system", 
                        "content": "Você é um analista especializado em classificar o nível de protagonismo de marcas em notícias. Use os critérios fornecidos de forma rigorosa mas inclusiva - qualquer menção da marca deve ser pelo menos Nível 3 (Citação). Considere verificações específicas quando informadas."
                    },
                    {"role": "user", "content": prompt_texto}
                ],
                "temperature": 0.1
            }
            
            response = requests.post(self.config.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            nivel_detectado = response.json()['choices'][0]['message']['content'].strip()
            nivel_detectado_limpo = nivel_detectado.replace(":", "").strip()
            
            return nivel_detectado_limpo
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro na requisição para notícia ID {noticia_id}, marca {marca}: {str(e)}")
            return 'Erro na API'
        except Exception as e:
            self.logger.error(f"Erro no processamento da resposta para notícia ID {noticia_id}, marca {marca}: {str(e)}")
            return 'Erro de Processamento'
    
    def _correct_missing_classifications_largo(self, df_resultados: pd.DataFrame, final_df: pd.DataFrame) -> pd.DataFrame:
        """
        Corrige classificações 'Nenhum Nível Encontrado' quando a marca é mencionada no texto
        ATUALIZADO: Funciona com formato largo e inclui contagem de ocorrências
        """
        self.logger.info("Iniciando correção pós-processamento para classificações 'Nenhum Nível Encontrado'...")
        
        correcoes_realizadas = 0
        
        # Cria um dicionário para acesso rápido aos textos das notícias
        noticias_dict = {}
        for _, row in final_df.iterrows():
            noticia_id = row['Id']
            titulo = str(row.get('Titulo', '')).strip()
            conteudo = str(row.get('Conteudo', '')).strip()
            noticias_dict[noticia_id] = {'titulo': titulo, 'conteudo': conteudo}
        
        # Processa cada linha do DataFrame resultado
        for index, row in df_resultados.iterrows():
            noticia_id = row['Id']
            
            if noticia_id in noticias_dict:
                for marca in self.config.w_marcas:
                    nivel_col = f'Nivel de Protagonismo {marca}'
                    ocorrencias_col = f'Ocorrencias {marca}'
                    
                    nivel_atual = row[nivel_col]
                    
                    # Se não há classificação ou é "Nenhum Nível Encontrado"
                    if pd.isna(nivel_atual) or nivel_atual == 'Nenhum Nível Encontrado':
                        # Recalcula a contagem para ter certeza
                        titulo = noticias_dict[noticia_id]['titulo']
                        conteudo = noticias_dict[noticia_id]['conteudo']
                        contagem = self._count_marca_occurrences(marca, titulo, conteudo)
                        
                        # Se encontrou ocorrências, reclassifica como "Nível 3" e preenche contagem
                        if contagem > 0:
                            self.logger.info(f"Corrigindo classificação - Notícia ID {noticia_id}, Marca {marca}: "
                                           f"'{nivel_atual}' → 'Nível 3' (encontradas {contagem} ocorrências)")
                            
                            df_resultados.loc[index, nivel_col] = 'Nível 3'
                            df_resultados.loc[index, ocorrencias_col] = contagem
                            correcoes_realizadas += 1
                        else:
                            self.logger.debug(f"Mantendo classificação - Notícia ID {noticia_id}, Marca {marca}: "
                                            f"marca não encontrada no texto")
            else:
                self.logger.warning(f"Texto não encontrado para notícia ID {noticia_id}")
        
        self.logger.info(f"Correção pós-processamento concluída: {correcoes_realizadas} classificações corrigidas")
        
        return df_resultados
    
    def _apply_nivel_substitutions_largo(self, df_resultados: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica as substituições dos níveis conforme especificado
        ATUALIZADO: Funciona com formato largo
        """
        self.logger.info("Aplicando substituições dos nomes dos níveis...")
        
        # Mapeamento baseado no arquivo Bradesco
        substituicoes = {
            "Nível 1": "Dedicada",
            "Nível 2": "Conteúdo", 
            "Nível 3": "Citação"
        }
        
        # Aplica substituições em todas as colunas de nível
        for marca in self.config.w_marcas:
            nivel_col = f'Nivel de Protagonismo {marca}'
            if nivel_col in df_resultados.columns:
                df_resultados[nivel_col] = df_resultados[nivel_col].apply(
                    lambda x: substituicoes.get(x, x) if pd.notna(x) else x
                )
        
        self.logger.info("Substituições concluídas")
        return df_resultados
    
    def _save_results_largo(self, df_resultados: pd.DataFrame):
        """
        Salva os resultados da análise de protagonismo no formato largo
        ATUALIZADO: Inclui colunas de ocorrências
        """
        try:
            # Verificação antes de salvar
            self.logger.info("=== PREPARANDO PARA SALVAR ===")
            self.logger.info(f"DataFrame a ser salvo: {len(df_resultados)} registros")
            self.logger.info(f"Colunas a serem salvas: {list(df_resultados.columns)}")
            
            # Verificar se as colunas obrigatórias estão presentes
            colunas_obrigatorias = ['Id', 'UrlVisualizacao', 'UrlOriginal', 'Titulo']
            for marca in self.config.w_marcas:
                colunas_obrigatorias.extend([
                    f'Nivel de Protagonismo {marca}',
                    f'Ocorrencias {marca}'
                ])
            
            colunas_faltantes = [col for col in colunas_obrigatorias if col not in df_resultados.columns]
            if colunas_faltantes:
                self.logger.error(f"ERRO: Tentando salvar sem colunas obrigatórias: {colunas_faltantes}")
                raise ValueError(f"Colunas obrigatórias faltantes: {colunas_faltantes}")
            
            # Gera timestamp para o nome do arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Define o caminho com timestamp
            base_path = str(self.config.arq_protagonismo_result).replace('.xlsx', f'_{timestamp}.xlsx')
            
            # Salva arquivo com timestamp
            df_resultados.to_excel(base_path, index=False)
            self.logger.info(f"✅ Resultados de protagonismo salvos: {base_path}")
            
            # Também salva arquivo padrão para compatibilidade com outras etapas
            df_resultados.to_excel(self.config.arq_protagonismo_result, index=False)
            self.logger.info(f"✅ Arquivo padrão salvo: {self.config.arq_protagonismo_result}")
            
            # Log final da estrutura salva
            self.logger.info("=== ARQUIVO SALVO COM SUCESSO ===")
            self.logger.info(f"Estrutura final: {list(df_resultados.columns)}")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar resultados: {str(e)}")
            raise
    
    # === MÉTODOS ANTIGOS MANTIDOS PARA COMPATIBILIDADE ===
    def _process_noticias(self, final_df: pd.DataFrame, df_protagonismo: pd.DataFrame) -> List[Dict]:
        """
        MÉTODO ORIGINAL MANTIDO PARA COMPATIBILIDADE
        Redireciona para o novo método de formato largo
        """
        self.logger.warning("Método _process_noticias antigo foi chamado. Redirecionando para formato largo.")
        df_largo = self._process_noticias_formato_largo(final_df, df_protagonismo)
        
        # Converte de volta para o formato lista para compatibilidade
        resultados = []
        for _, row in df_largo.iterrows():
            for marca in self.config.w_marcas:
                nivel_col = f'Nivel de Protagonismo {marca}'
                nivel = row[nivel_col]
                if pd.notna(nivel):
                    resultados.append({
                        'Id': row['Id'],
                        'Marca': marca,
                        'Nivel': nivel
                    })
        
        return resultados
    
    def _apply_nivel_substitutions(self, df_resultados: pd.DataFrame) -> pd.DataFrame:
        """
        MÉTODO ORIGINAL MANTIDO PARA COMPATIBILIDADE
        """
        return self._apply_nivel_substitutions_largo(df_resultados)
    
    def _correct_missing_classifications(self, df_resultados: pd.DataFrame, final_df: pd.DataFrame) -> pd.DataFrame:
        """
        MÉTODO ORIGINAL MANTIDO PARA COMPATIBILIDADE
        """
        return self._correct_missing_classifications_largo(df_resultados, final_df)
    
    def _save_results(self, df_resultados: pd.DataFrame):
        """
        MÉTODO ORIGINAL MANTIDO PARA COMPATIBILIDADE
        """
        return self._save_results_largo(df_resultados)