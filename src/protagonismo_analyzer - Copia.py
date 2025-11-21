"""
Módulo responsável pela análise de protagonismo usando DeepSeek API
Adaptado do código original removendo filtros específicos do iFood
VERSÃO ATUALIZADA: Inclui contagem de ocorrências das marcas e verificação de porta-vozes
VERSÃO CORRIGIDA: Bug de classificação de marca em termos compostos corrigido
"""

import pandas as pd
import requests
import time
import re
import logging
import unicodedata
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from src.config_manager import ConfigManager

class ProtagonismoAnalyzer:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self.headers = config_manager.get_api_headers()
        # Carrega porta-vozes: dicionário {normalizado: original} e lista de normalizados
        # ATUALIZADO: Usado para Bradesco, Ágora, Bradesco Asset e BBI
        self.porta_vozes_map, self.porta_vozes = self._load_porta_vozes()
    
    def _normalize_text(self, text: str) -> str:
        """
        Remove acentos e normaliza texto para comparação
        
        Args:
            text: Texto a ser normalizado
            
        Returns:
            Texto sem acentos e em minúsculas
        """
        # Remove acentos usando NFD (Normalization Form Canonical Decomposition)
        nfd = unicodedata.normalize('NFD', text)
        text_sem_acento = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
        return text_sem_acento.lower()
    
    def _clean_channel_field(self, canais_text: str) -> str:
        """
        Limpa o campo Canais removendo colchetes, áspas e caracteres especiais
        que podem atrapalhar a detecção de marcas
        
        Args:
            canais_text: Texto original do campo Canais
            
        Returns:
            Texto limpo sem colchetes, áspas e espaços extras
        
        Exemplo:
            Input: "['', '', 'Ágora'], Bradesco, Santander"
            Output: "Ágora, Bradesco, Santander"
        """
        if not canais_text:
            return ""
        
        # Remove colchetes, áspas simples e duplas
        texto_limpo = canais_text.replace('[', '').replace(']', '')
        texto_limpo = texto_limpo.replace("'", '').replace('"', '')
        
        # Remove espaços duplicados e vírgulas múltiplas
        texto_limpo = re.sub(r'\s+', ' ', texto_limpo)
        texto_limpo = re.sub(r',\s*,+', ',', texto_limpo)
        
        # Remove vírgulas no início/fim e espaços
        texto_limpo = texto_limpo.strip().strip(',').strip()
        
        return texto_limpo
    
    def _load_porta_vozes(self) -> tuple[Dict[str, str], List[str]]:
        """
        Carrega lista de porta-vozes do arquivo mais recente
        ATUALIZADO: Usado para Bradesco, Ágora, Bradesco Asset e BBI
        
        Returns:
            Tupla contendo:
            - Dicionário {nome_normalizado: nome_original} para manter capitalização
            - Lista de nomes normalizados para busca rápida
        """
        try:
            config_path = Path("config")
            
            # Busca todos os arquivos que começam com porta_vozes_
            arquivos_porta_vozes = list(config_path.glob("porta_vozes_*.xlsx"))
            
            if not arquivos_porta_vozes:
                self.logger.warning("Nenhum arquivo de porta-vozes encontrado na pasta config")
                return {}, []
            
            # Ordena por nome (timestamp no nome) e pega o mais recente
            arquivo_mais_recente = sorted(arquivos_porta_vozes, reverse=True)[0]
            
            self.logger.info(f"Carregando porta-vozes do arquivo: {arquivo_mais_recente.name}")
            
            # Lê arquivo sem header (apenas uma coluna)
            df_porta_vozes = pd.read_excel(arquivo_mais_recente, header=None)
            
            # Extrai nomes: cria dicionário e lista
            porta_vozes_map = {}  # {normalizado: original}
            porta_vozes_list = []  # [normalizado1, normalizado2, ...]
            
            for nome in df_porta_vozes[0].dropna():
                nome_original = str(nome).strip()
                nome_normalizado = self._normalize_text(nome_original)
                
                if nome_normalizado:
                    porta_vozes_map[nome_normalizado] = nome_original
                    porta_vozes_list.append(nome_normalizado)
            
            self.logger.info(f"Carregados {len(porta_vozes_list)} porta-vozes (Bradesco e Ágora)")
            self.logger.debug(f"Primeiros 5 porta-vozes: {list(porta_vozes_map.values())[:5]}...")
            
            return porta_vozes_map, porta_vozes_list
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar arquivo de porta-vozes: {str(e)}")
            return {}, []
    
    def _check_porta_voz_mentioned(self, titulo: str, conteudo: str) -> List[str]:
        """
        Verifica se algum porta-voz (Bradesco ou Ágora) é mencionado no texto
        
        Args:
            titulo: Título da notícia
            conteudo: Conteúdo da notícia
            
        Returns:
            Lista de nomes de porta-vozes encontrados com capitalização ORIGINAL (vazia se nenhum encontrado)
        """
        if not self.porta_vozes:
            return []
        
        # Combina título e conteúdo e normaliza
        texto_completo = f"{titulo} {conteudo}"
        texto_normalizado = self._normalize_text(texto_completo)
        
        # Lista para armazenar porta-vozes encontrados (com capitalização original)
        porta_vozes_encontrados = []
        
        # Busca cada porta-voz no texto
        for porta_voz_normalizado in self.porta_vozes:
            # Usa word boundary para evitar matches parciais
            pattern = r'\b' + re.escape(porta_voz_normalizado) + r'\b'
            if re.search(pattern, texto_normalizado):
                # Adiciona o nome ORIGINAL (com capitalização) à lista
                nome_original = self.porta_vozes_map.get(porta_voz_normalizado, porta_voz_normalizado)
                porta_vozes_encontrados.append(nome_original)
        
        return porta_vozes_encontrados
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CORREÇÃO: NOVOS MÉTODOS PARA RESOLVER BUG DE MARCAS COMPOSTAS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_marcas_compostas_para_marca_base(self, marca_base: str) -> List[str]:
        """
        Retorna lista de marcas compostas que contêm a marca base
        
        Exemplos:
            marca_base="Bradesco" → ["Bradesco Asset", "Bradesco BBI"]
            marca_base="Itaú" → ["Itaú Unibanco"]
        
        Args:
            marca_base: Marca base (ex: "Bradesco")
        
        Returns:
            list: Lista de marcas compostas
        """
        todas_marcas = self.config.w_marcas
        marcas_compostas = []
        marca_base_lower = marca_base.lower()
        
        for marca in todas_marcas:
            marca_lower = marca.lower()
            # Se a marca contém a base mas não é igual (é composta)
            if marca_base_lower in marca_lower and marca_lower != marca_base_lower:
                marcas_compostas.append(marca)
        
        return marcas_compostas
    
    def _verificar_marca_isolada_no_titulo(self, marca: str, titulo: str, 
                                           marcas_compostas: List[str]) -> bool:
        """
        Verifica se a marca aparece ISOLADA no título (não como parte de termo composto)
        
        Exemplos:
            marca="Bradesco", titulo="Bradesco Asset adia..." → False
            marca="Bradesco", titulo="Bradesco anuncia..." → True
        
        Args:
            marca: Nome da marca (ex: "Bradesco")
            titulo: Título da notícia
            marcas_compostas: Lista de marcas compostas que contêm a marca base
        
        Returns:
            bool: True se a marca aparece isolada, False se faz parte de termo composto
        """
        titulo_lower = titulo.lower()
        marca_lower = marca.lower()
        
        # Primeiro verifica se a marca existe no título
        if marca_lower not in titulo_lower:
            return False
        
        # Verificar se alguma das marcas compostas está presente
        for marca_composta in marcas_compostas:
            if marca_composta.lower() in titulo_lower:
                self.logger.info(
                    f"Marca '{marca}' encontrada no título, mas faz parte de '{marca_composta}' - "
                    f"não será classificada automaticamente como Dedicada"
                )
                return False
        
        # Se chegou aqui, a marca aparece isolada
        # Verificar usando word boundary para ter certeza
        pattern = r'\b' + re.escape(marca_lower) + r'\b'
        if re.search(pattern, titulo_lower):
            self.logger.info(
                f"Marca '{marca}' encontrada ISOLADA no título - "
                f"Classificação automática: Dedicada"
            )
            return True
        
        return False
    
    def _count_marca_occurrences_fixed(self, marca: str, titulo: str, conteudo: str, 
                                       marcas_compostas: List[str]) -> int:
        """
        Conta quantas vezes a marca aparece ISOLADA no texto (não como parte de termo composto)
        
        Estratégia:
            1. Substitui todas marcas compostas por placeholders
            2. Conta apenas a marca isolada
            
        Exemplos:
            texto="Bradesco Asset e Bradesco anunciam..."
            marca="Bradesco", marcas_compostas=["Bradesco Asset"]
            → Retorna 1 (apenas o "Bradesco" isolado)
        
        Args:
            marca: Nome da marca (ex: "Bradesco")
            titulo: Título da notícia
            conteudo: Conteúdo da notícia
            marcas_compostas: Lista de marcas compostas que contêm a marca base
        
        Returns:
            int: Número de ocorrências ISOLADAS da marca
        """
        # Combinar título e conteúdo
        texto_completo = f"{titulo} {conteudo}"
        texto_lower = texto_completo.lower()
        marca_lower = marca.lower()
        
        # PRIMEIRO: Substituir temporariamente todas as ocorrências de marcas compostas
        # por um placeholder para não contá-las
        # IMPORTANTE: Usar placeholder único que não contém as palavras originais
        texto_modificado = texto_lower
        marcas_ordenadas = sorted(marcas_compostas, key=len, reverse=True)
        
        for i, marca_composta in enumerate(marcas_ordenadas):
            marca_composta_lower = marca_composta.lower()
            # Usar placeholder único baseado no índice
            placeholder = f'___MARCA_COMPOSTA_{i}___'
            texto_modificado = texto_modificado.replace(marca_composta_lower, placeholder)
        
        # SEGUNDO: Contar apenas a marca isolada no texto modificado
        pattern = r'\b' + re.escape(marca_lower) + r'\b'
        matches = re.findall(pattern, texto_modificado)
        
        contagem = len(matches)
        
        # Log para debug
        if contagem > 0:
            self.logger.debug(
                f"Marca '{marca}' encontrada {contagem} vez(es) ISOLADA no texto "
                f"(excluindo ocorrências em: {marcas_compostas})"
            )
        
        return contagem
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FIM DOS NOVOS MÉTODOS PARA CORREÇÃO
    # ═══════════════════════════════════════════════════════════════════════════
    
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
                
                # Aplica correção pós-processamento
                df_resultados = self._correct_missing_classifications_largo(df_resultados, final_df)
                
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
        
        REGRAS ESPECIAIS:
        - "Bradesco": conta apenas quando NÃO for seguido de "BBI" ou "Asset"
        - "BBI": conta "BBI" isolado + "Bradesco BBI" (sem contar o Bradesco)
        - "Bradesco Asset": conta apenas "Bradesco Asset" completo
        
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
        
        # === REGRAS ESPECIAIS POR MARCA ===
        
        # 1. BRADESCO: Conta apenas quando NÃO for seguido de "BBI" ou "Asset"
        if marca_lower == "bradesco":
            # Pattern: "bradesco" que NÃO seja seguido de "bbi" ou "asset"
            # Negative lookahead: (?!\s+(bbi|asset)\b)
            pattern = r'\bbradesco\b(?!\s+(bbi|asset)\b)'
            matches = re.findall(pattern, texto_completo, re.IGNORECASE)
            return len(matches)
        
        # 2. BBI: Aceita "BBI" isolado OU "Bradesco BBI"
        elif marca_lower == "bbi":
            # Conta duas variações:
            # a) "Bradesco BBI" (completo)
            pattern_bradesco_bbi = r'\bbradesco\s+bbi\b'
            matches_bradesco_bbi = re.findall(pattern_bradesco_bbi, texto_completo, re.IGNORECASE)
            
            # b) "BBI" isolado (sem Bradesco antes)
            # Negative lookbehind: (?<!bradesco\s)
            pattern_bbi_isolado = r'(?<!bradesco\s)\bbbi\b'
            matches_bbi_isolado = re.findall(pattern_bbi_isolado, texto_completo, re.IGNORECASE)
            
            total = len(matches_bradesco_bbi) + len(matches_bbi_isolado)
            return total
        
        # 3. BRADESCO ASSET: Aceita apenas "Bradesco Asset" completo
        elif marca_lower == "bradesco asset":
            # Pattern: "bradesco asset" (completo)
            pattern = r'\bbradesco\s+asset\b'
            matches = re.findall(pattern, texto_completo, re.IGNORECASE)
            return len(matches)
        
        # 4. OUTRAS MARCAS: Contagem normal com word boundary
        else:
            pattern = r'\b' + re.escape(marca_lower) + r'\b'
            matches = re.findall(pattern, texto_completo, re.IGNORECASE)
            return len(matches)
    
    def _process_noticias_formato_largo(self, final_df: pd.DataFrame, df_protagonismo: pd.DataFrame) -> pd.DataFrame:
        """
        Processa cada notícia para análise de protagonismo e contagem de ocorrências
        ATUALIZADO: Retorna DataFrame no formato largo (uma linha por notícia, colunas separadas por marca)
        CORRIGIDO: Bug de classificação de marca em termos compostos
        """
        required_columns = ['Id', 'Titulo', 'Conteudo', 'Canais']
        
        if not all(col in final_df.columns for col in required_columns):
            self.logger.error(f"Colunas necessárias não encontradas: {required_columns}")
            return pd.DataFrame()
        
        # Criar DataFrame resultado com as colunas base
        resultado_df = final_df[['Id', 'UrlVisualizacao', 'UrlOriginal', 'Titulo']].copy()
        
        # Adicionar colunas para cada marca (protagonismo + contagem + porta-voz)
        for marca in self.config.w_marcas:
            resultado_df[f'Nivel de Protagonismo {marca}'] = None
            resultado_df[f'Ocorrencias {marca}'] = 0
            
            # ATUALIZADO: Porta-vozes para Bradesco, Ágora, Bradesco Asset e BBI
            if marca in ['Bradesco', 'Ágora', 'Bradesco Asset', 'BBI']:
                resultado_df[f'Porta-Voz {marca}'] = None
        
        self.logger.info("Avaliando nível de protagonismo para cada notícia e marca...")
        
        # Contador para estatísticas
        total_noticias = len(final_df)
        noticias_processadas = 0
        noticias_filtradas = 0
        classificacoes_automaticas = 0
        upgrades_por_porta_voz = 0
        chamadas_deepseek = 0
        
        for index, row in final_df.iterrows():
            noticia_id = row['Id']
            titulo_noticia = str(row['Titulo']).strip()
            conteudo_noticia = str(row['Conteudo']).strip()
            canais_noticia = str(row['Canais']).strip()
            
            # NOVO: Limpa o campo Canais
            canais_noticia = self._clean_channel_field(canais_noticia)
            
            # Combina título e conteúdo
            texto_completo_noticia = f"Título: {titulo_noticia}\n\nConteúdo: {conteudo_noticia}"
            
            if not texto_completo_noticia.strip():
                self.logger.warning(f"Pulando notícia ID {noticia_id}: Título e Conteúdo vazios")
                continue
            
            # FILTRO: Verifica se pelo menos uma das marcas está presente no campo Canais
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
                self.logger.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - "
                                f"Avaliando notícia ID {noticia_id} para a marca: {marca}")
                
                # Inicializar variáveis no início de CADA iteração
                nivel_detectado = None
                classificacao_automatica = False
                
                # ═══ CORREÇÃO 1: Obter marcas compostas relacionadas ═══
                marcas_compostas = self._get_marcas_compostas_para_marca_base(marca)
                
                # ═══ Contagem de ocorrências (usa método com negative lookahead) ═══
                contagem = self._count_marca_occurrences(
                    marca, titulo_noticia, conteudo_noticia
                )
                
                # === PRÉ-PROCESSAMENTO BASEADO EM CONTAGEM DE OCORRÊNCIAS ===
                
                # CRÍTICO: Não pula quando contagem é 0 - deixa ir para DeepSeek
                # O DeepSeek pode detectar a marca mesmo quando nossa contagem não encontra
                
                # Regra 1: 5+ ocorrências = Dedicada
                if contagem >= 5:
                    nivel_detectado = 'Nível 1'  # Dedicada
                    classificacao_automatica = True
                    self.logger.info(f"Marca '{marca}' com {contagem} ocorrências - Classificação automática: Dedicada")
                    classificacoes_automaticas += 1
                
                # Regra 2: 3-4 ocorrências = Conteúdo
                elif contagem >= 3:
                    nivel_detectado = 'Nível 2'  # Conteúdo
                    classificacao_automatica = True
                    self.logger.info(f"Marca '{marca}' com {contagem} ocorrências - Classificação automática: Conteúdo")
                    classificacoes_automaticas += 1
                
                # Regra 3: 1-2 ocorrências = Citação (mas verifica porta-voz para marcas específicas)
                elif contagem >= 1:
                    nivel_detectado = 'Nível 3'  # Citação
                    classificacao_automatica = True
                    
                    # Verificação de porta-vozes para Bradesco, Ágora, Bradesco Asset e BBI
                    if marca in ['Bradesco', 'Ágora', 'Bradesco Asset', 'BBI']:
                        porta_vozes_encontrados = self._check_porta_voz_mentioned(titulo_noticia, conteudo_noticia)
                        
                        if porta_vozes_encontrados:
                            nivel_detectado = 'Nível 2'  # Upgrade para Conteúdo
                            upgrades_por_porta_voz += 1
                            self.logger.info(f"Marca '{marca}' com {contagem} ocorrências + porta-vozes: {', '.join(porta_vozes_encontrados)} - Upgrade para Conteúdo")
                            
                            # Salvar porta-vozes no DataFrame (igual ao que já existe no método DeepSeek)
                            mask = resultado_df['Id'] == noticia_id
                            porta_vozes_str = ', '.join(porta_vozes_encontrados)
                            resultado_df.loc[mask, f'Porta-Voz {marca}'] = porta_vozes_str
                        else:
                            self.logger.info(f"Marca '{marca}' com {contagem} ocorrências - Classificação automática: Citação")
                    else:
                        self.logger.info(f"Marca '{marca}' com {contagem} ocorrências - Classificação automática: Citação")
                    
                    classificacoes_automaticas += 1
                
                # ═══ CORREÇÃO 2: Verificar se marca aparece ISOLADA no título (sobrescreve contagem) ═══
                marca_isolada_no_titulo = self._verificar_marca_isolada_no_titulo(
                    marca, titulo_noticia, marcas_compostas
                )
                
                if marca_isolada_no_titulo:
                    # Marca isolada no título sempre é Dedicada (sobrescreve classificação por contagem)
                    nivel_detectado = 'Nível 1'  # Dedicada
                    classificacao_automatica = True
                    self.logger.info(f"Marca '{marca}' encontrada ISOLADA no título - Dedicada (sobrescreve contagem)")
                    if contagem < 5:  # Só conta se não foi contado antes
                        classificacoes_automaticas += 1
                
                # Se não houve classificação automática, envia para DeepSeek
                if not classificacao_automatica:
                    # Verifica regras específicas de conteúdo
                    content_check = self.config.check_specific_content_requirements(
                        canais_noticia, texto_completo_noticia
                    )
                    
                    if content_check['should_be_minimum_citation'] and marca == 'Bradesco':
                        specific_terms_info = content_check['found_specific_terms']
                        self.logger.info(
                            f"Termos específicos encontrados para Bradesco: "
                            f"{[t['content_term'] for t in specific_terms_info]}"
                        )
                    
                    # Faz análise completa com DeepSeek
                    nivel_detectado = self._analyze_single_news_marca(
                        texto_completo_noticia, marca, df_protagonismo, noticia_id, 
                        canais_noticia, content_check
                    )
                    chamadas_deepseek += 1
                    # Pausa para evitar sobrecarregar a API
                    time.sleep(1)
                
                # Salvar resultados no DataFrame formato largo
                mask = resultado_df['Id'] == noticia_id
                resultado_df.loc[mask, f'Nivel de Protagonismo {marca}'] = nivel_detectado
                resultado_df.loc[mask, f'Ocorrencias {marca}'] = contagem
                
                self.logger.info(
                    f"Notícia ID {noticia_id}, Marca {marca}: "
                    f"Nível='{nivel_detectado}', Ocorrências={contagem}"
                )
        
        # Log de estatísticas finais
        self.logger.info(f"Estatísticas do processamento:")
        self.logger.info(f"- Total de notícias na base: {total_noticias}")
        self.logger.info(f"- Notícias processadas (com marcas no canal): {noticias_processadas}")
        self.logger.info(f"- Notícias filtradas (sem marcas no canal): {noticias_filtradas}")
        self.logger.info(f"- Classificações automáticas (por contagem/título): {classificacoes_automaticas}")
        self.logger.info(f"- Upgrades por porta-voz (Citação→Conteúdo): {upgrades_por_porta_voz}")
        self.logger.info(f"- Chamadas enviadas ao DeepSeek: {chamadas_deepseek}")
        
        if noticias_processadas > 0:
            economia_percentual = (classificacoes_automaticas / noticias_processadas) * 100
            self.logger.info(f"- Economia de chamadas API: {economia_percentual:.1f}%")
        
        return resultado_df
    
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
            self.logger.error(f"Erro inesperado ao processar notícia ID {noticia_id}, marca {marca}: {str(e)}")
            return 'Erro de Processamento'
    
    
    def _correct_missing_classifications_largo(self, df_resultados: pd.DataFrame, final_df: pd.DataFrame) -> pd.DataFrame:
        """
        Corrige classificações faltantes ou incorretas baseado na contagem de ocorrências
        ATUALIZADO: Funciona com formato largo e inclui verificação de porta-vozes
        CORRIGIDO: Usa verificação de marca isolada no título
        """
        self.logger.info("Iniciando correção pós-processamento baseada na contagem de ocorrências...")
        
        correcoes_realizadas = 0
        
        # Cache de textos das notícias para evitar buscas repetidas
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
                titulo = noticias_dict[noticia_id]['titulo']
                conteudo = noticias_dict[noticia_id]['conteudo']
                
                for marca in self.config.w_marcas:
                    nivel_col = f'Nivel de Protagonismo {marca}'
                    ocorrencias_col = f'Ocorrencias {marca}'
                    
                    nivel_atual = row.get(nivel_col)
                    contagem = row.get(ocorrencias_col, 0)
                    
                    # Se não há classificação ou é "Nenhum Nível Encontrado"
                    if pd.isna(nivel_atual) or nivel_atual == 'Nenhum Nível Encontrado':
                        # ═══ CORREÇÃO: Usar contagem corrigida ═══
                        marcas_compostas = self._get_marcas_compostas_para_marca_base(marca)
                        contagem = self._count_marca_occurrences_fixed(marca, titulo, conteudo, marcas_compostas)
                        
                        # Se encontrou ocorrências, reclassifica baseado na quantidade
                        if contagem > 0:
                            # Determina o nível baseado na quantidade de ocorrências
                            if contagem >= 5:
                                nivel_corrigido = 'Nível 1'  # Dedicada
                                nome_nivel = 'Dedicada'
                            elif contagem >= 3:  # 3-4 ocorrências
                                nivel_corrigido = 'Nível 2'  # Conteúdo
                                nome_nivel = 'Conteúdo'
                            else:  # 1-2 ocorrências
                                nivel_corrigido = 'Nível 3'  # Citação
                                nome_nivel = 'Citação'
                                
                                # NOVO: Verificar porta-vozes para upgrade (Bradesco, Ágora, Bradesco Asset, BBI)
                                if marca in ['Bradesco', 'Ágora', 'Bradesco Asset', 'BBI']:
                                    porta_vozes_encontrados = self._check_porta_voz_mentioned(titulo, conteudo)
                                    
                                    if porta_vozes_encontrados:
                                        nivel_corrigido = 'Nível 2'  # Upgrade para Conteúdo
                                        nome_nivel = f'Conteúdo (upgrade por porta-voz: {", ".join(porta_vozes_encontrados)})'
                                        
                                        # Preenche coluna de porta-voz se existir
                                        portavoz_col = f'Porta-Voz {marca}'
                                        if portavoz_col in df_resultados.columns:
                                            porta_vozes_str = ', '.join(porta_vozes_encontrados)
                                            df_resultados.loc[index, portavoz_col] = porta_vozes_str
                            
                            # ═══ CORREÇÃO: Verificar se marca está ISOLADA no título ═══
                            marca_isolada = self._verificar_marca_isolada_no_titulo(marca, titulo, marcas_compostas)
                            if marca_isolada:
                                nivel_corrigido = 'Nível 1'
                                nome_nivel = 'Dedicada (marca isolada no título)'
                            
                            self.logger.info(f"Corrigindo classificação - Notícia ID {noticia_id}, Marca {marca}: "
                                           f"'{nivel_atual}' → '{nome_nivel}' ({contagem} ocorrências)")
                            
                            df_resultados.loc[index, nivel_col] = nivel_corrigido
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
        Remove colunas de porta-vozes do Itaú e Santander antes de salvar
        """
        try:
            # NOVO: Remove colunas de Porta-Voz do Itaú e Santander (se existirem)
            colunas_para_remover = []
            for marca in ['Itaú', 'Santander']:
                col_portavoz = f'Porta-Voz {marca}'
                if col_portavoz in df_resultados.columns:
                    colunas_para_remover.append(col_portavoz)
            
            if colunas_para_remover:
                df_resultados = df_resultados.drop(columns=colunas_para_remover)
                self.logger.info(f"Colunas de porta-vozes removidas: {colunas_para_remover}")
            
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
                
                # ATUALIZADO: Porta-vozes são obrigatórias para Bradesco, Ágora, Bradesco Asset e BBI
                if marca in ['Bradesco', 'Ágora', 'Bradesco Asset', 'BBI']:
                    colunas_obrigatorias.append(f'Porta-Voz {marca}')
            
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