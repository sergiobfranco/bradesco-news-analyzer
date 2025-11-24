#!/usr/bin/env python3
"""
Brand Extractor - Detecção de Marcas para Análise de Exclusividade
Integrado com a arquitetura do projeto Bradesco News Analyzer

Execução:
  python src/brand_extractor.py          (diretamente)
  python -m src.brand_extractor          (como módulo)
  python main.py                         (integrado)

Autor: Claude + Sérgio Franco  
Data: Novembro 2025
"""

import pandas as pd
import json
import hashlib
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import re
import requests
import sys
import os

# Configurar imports de forma flexível
def setup_imports():
    """Configura imports para diferentes formas de execução"""
    
    # Adicionar diretório do projeto ao path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    try:
        # Tentar import normal (execução como módulo)
        from src.config_manager import ConfigManager
        from src.api_caller import APICaller
        return ConfigManager, APICaller
        
    except ImportError:
        try:
            # Tentar import direto (execução direta)
            current_dir = Path(__file__).parent
            
            # Carregar config_manager
            config_path = current_dir / "config_manager.py"
            if not config_path.exists():
                raise ImportError(f"Arquivo não encontrado: {config_path}")
                
            import importlib.util
            spec = importlib.util.spec_from_file_location("config_manager", config_path)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            ConfigManager = config_module.ConfigManager
            
            # Carregar api_caller  
            api_path = current_dir / "api_caller.py"
            if not api_path.exists():
                raise ImportError(f"Arquivo não encontrado: {api_path}")
                
            spec = importlib.util.spec_from_file_location("api_caller", api_path)
            api_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(api_module)
            APICaller = api_module.APICaller
            
            return ConfigManager, APICaller
            
        except Exception as e:
            print(f"❌ Erro ao carregar dependências: {e}")
            print("\n💡 Soluções:")
            print("1. Execute do diretório raiz: cd bradesco-news-analyzer && python src/brand_extractor.py")
            print("2. Ou como módulo: python -m src.brand_extractor")
            print("3. Verifique se arquivos src/config_manager.py e src/api_caller.py existem")
            sys.exit(1)

# Carregar dependências
ConfigManager, APICaller = setup_imports()

class BrandExtractor:
    """Extrator de marcas integrado com a arquitetura do projeto"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        Inicializa o extrator usando o ConfigManager existente
        
        Args:
            config_manager: Instância do ConfigManager do projeto
        """
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self.headers = config_manager.get_api_headers()  # CORRIGIDO: Mesmo que protagonismo_analyzer
        
        # Configurar diretórios para brand extractor
        self._setup_directories()
        
        # Marcas do grupo Bradesco (para análise de exclusividade)
        self.bradesco_group_brands = [
            "Bradesco",
            "Bradesco BBI", 
            "Bradesco Asset",
            "Ágora"
        ]
        
        # Cache para evitar reprocessar
        self.processed_cache = set()
        self.load_processed_cache()
        
        # Estatísticas
        self.stats = {
            "total_articles": 0,
            "processed_articles": 0,
            "skipped_cache": 0,
            "api_calls": 0,
            "unique_brands": 0,
            "exclusive_articles": 0
        }

    def _setup_directories(self):
        """Configura diretórios específicos do brand extractor"""
        # Usar estrutura existente do projeto
        self.output_dir = self.config.pasta_marca_setor / "brand_analysis"
        self.output_dir.mkdir(exist_ok=True)
        
        # Cache no diretório de dados
        self.cache_dir = self.config.pasta_api / ".cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Diretórios configurados:")
        self.logger.info(f"  Saída: {self.output_dir}")
        self.logger.info(f"  Cache: {self.cache_dir}")

    def load_processed_cache(self):
        """Carrega cache de artigos já processados"""
        cache_file = self.cache_dir / "brand_extraction_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.processed_cache = set(cache_data.get('processed_hashes', []))
                    self.logger.info(f"Cache carregado: {len(self.processed_cache)} artigos já processados")
            except Exception as e:
                self.logger.warning(f"Erro ao carregar cache: {e}")

    def save_processed_cache(self):
        """Salva cache de artigos processados"""
        cache_file = self.cache_dir / "brand_extraction_cache.json"
        try:
            cache_data = {
                'processed_hashes': list(self.processed_cache),
                'last_update': datetime.now().isoformat(),
                'total_processed': len(self.processed_cache)
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Erro ao salvar cache: {e}")

    def get_content_hash(self, title: str, content: str) -> str:
        """Gera hash único para o conteúdo do artigo"""
        combined = f"{title}\n{content}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()

    def extract_brands_with_deepseek(self, title: str, content: str) -> List[str]:
        """
        Extrai marcas usando DeepSeek API com configurações do projeto
        CORRIGIDO: Usa mesmo formato do protagonismo_analyzer.py
        
        Args:
            title: Título da notícia
            content: Conteúdo da notícia
            
        Returns:
            Lista de marcas detectadas
        """
        text = f"Título: {title}\n\nConteúdo: {content}"
        
        prompt = f"""
Analise o texto a seguir e identifique TODAS as marcas/empresas mencionadas.

INSTRUÇÕES IMPORTANTES:
1. Identifique marcas de TODOS os setores (bancos, tecnologia, varejo, automotivo, etc.)
2. Inclua tanto marcas principais quanto subsidiárias/divisões
3. NÃO inclua: nomes de pessoas, cidades, países, órgãos governamentais
4. NÃO inclua: termos genéricos como "governo", "mercado", "setor"
5. Mantenha grafias exatas como aparecem no texto
6. ATENÇÃO ESPECIAL para marcas do grupo Bradesco: Bradesco, Bradesco BBI, Bradesco Asset, Ágora

FORMATO DE RESPOSTA:
Responda APENAS com uma lista JSON de strings, sem explicações:
["Marca1", "Marca2", "Marca3"]

Se não encontrar marcas, responda: []

TEXTO:
{text}
"""

        try:
            # CORRIGIDO: Usar EXATAMENTE o mesmo formato do protagonismo_analyzer.py
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system", 
                        "content": "Você é um analista especializado em identificar marcas/empresas mencionadas em textos. Identifique TODAS as marcas, exceto órgãos governamentais e termos genéricos."
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1
            }
            
            response = requests.post(self.config.api_url, headers=self.headers, json=payload)
            response.raise_for_status()  # CORRIGIDO: Mesmo tratamento de erro
            
            result = response.json()
            brands_text = result['choices'][0]['message']['content'].strip()
            
            # Parse JSON response
            try:
                brands = json.loads(brands_text)
                if isinstance(brands, list):
                    self.stats["api_calls"] += 1
                    self.logger.debug(f"DeepSeek retornou: {brands}")
                    return brands
            except json.JSONDecodeError:
                self.logger.warning(f"Resposta não é JSON válido: {brands_text}")
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro na requisição DeepSeek: {str(e)}")
        except Exception as e:
            self.logger.error(f"Erro inesperado ao chamar DeepSeek: {str(e)}")
            
        return []

    def apply_automatic_filters(self, brands: List[str]) -> List[str]:
        """
        Aplica filtros automáticos para reduzir ruído
        
        Args:
            brands: Lista de marcas brutas
            
        Returns:
            Lista de marcas filtradas
        """
        filtered_brands = []
        
        for brand in brands:
            if not brand or not isinstance(brand, str):
                continue
                
            brand = brand.strip()
            
            # Filtro: tamanho mínimo
            if len(brand) < 3:
                continue
                
            # Filtro: só números
            if brand.isdigit():
                continue
                
            # Filtro: URLs ou emails
            if '@' in brand or 'http' in brand.lower() or '.com' in brand.lower():
                continue
                
            # Filtro: termos muito genéricos
            generic_terms = {
                'brasil', 'brazil', 'sp', 'rj', 'mg', 'são paulo', 'rio de janeiro',
                'governo', 'estado', 'união', 'federal', 'municipal', 'nacional',
                'mercado', 'setor', 'empresa', 'companhia', 'grupo', 'holding',
                'ltda', 'sa', 's.a.', 'inc', 'corp', 'corporation', 'banco central',
                'tesouro nacional', 'ministério', 'receita federal'
            }
            
            if brand.lower() in generic_terms:
                continue
                
            # Filtro: apenas caracteres especiais
            if not re.search(r'[a-zA-Z]', brand):
                continue
                
            filtered_brands.append(brand)
            
        return filtered_brands

    def check_exclusivity(self, brands: List[str], article_id: str, title: str) -> Optional[str]:
        """
        Verifica se alguma marca do grupo Bradesco aparece de forma exclusiva
        
        Args:
            brands: Lista de todas as marcas detectadas no artigo
            article_id: ID do artigo
            title: Título do artigo
            
        Returns:
            Nome da marca exclusiva ou None
        """
        # Normalizar marcas detectadas (case insensitive)
        brands_normalized = [b.lower() for b in brands]
        
        # Verificar cada marca do grupo Bradesco
        bradesco_brands_found = []
        for bradesco_brand in self.bradesco_group_brands:
            if bradesco_brand.lower() in brands_normalized:
                bradesco_brands_found.append(bradesco_brand)
        
        # Verificar exclusividade: APENAS UMA marca do grupo E NENHUMA outra marca
        if len(bradesco_brands_found) == 1 and len(brands) == 1:
            exclusive_brand = bradesco_brands_found[0]
            self.logger.info(f"EXCLUSIVA DETECTADA - Artigo {article_id}: '{exclusive_brand}' | Título: {title[:50]}...")
            self.stats["exclusive_articles"] += 1
            return exclusive_brand
            
        return None

    def load_data_from_api(self) -> pd.DataFrame:
        """
        Carrega dados usando o APICaller existente ou arquivo local
        
        Returns:
            DataFrame com dados das notícias
        """
        self.logger.info("Tentando carregar dados...")
        
        try:
            # Primeira tentativa: usar APICaller
            self.logger.info("Tentando APICaller...")
            api_caller = APICaller(self.config)
            df = api_caller.fetch_data()
            
            if not df.empty:
                self.logger.info(f"APICaller: {len(df)} artigos carregados")
                return df
            else:
                self.logger.warning("APICaller retornou DataFrame vazio")
                
        except Exception as e:
            self.logger.warning(f"Erro no APICaller: {e}")
        
        # Segunda tentativa: arquivo local
        try:
            self.logger.info("Tentando carregar arquivo local...")
            if self.config.arq_api_original.exists():
                df = pd.read_excel(self.config.arq_api_original)
                self.logger.info(f"Arquivo local: {len(df)} artigos carregados")
                return df
            else:
                self.logger.warning(f"Arquivo local não encontrado: {self.config.arq_api_original}")
                
        except Exception as e:
            self.logger.error(f"Erro ao carregar arquivo local: {e}")
        
        # Terceira tentativa: arquivo alternativo
        try:
            alternative_file = self.config.pasta_api / "Favoritos_Marcas.xlsx"
            if alternative_file.exists():
                self.logger.info(f"Tentando arquivo alternativo: {alternative_file}")
                df = pd.read_excel(alternative_file)
                self.logger.info(f"Arquivo alternativo: {len(df)} artigos carregados")
                return df
                
        except Exception as e:
            self.logger.error(f"Erro no arquivo alternativo: {e}")
        
        raise ValueError("Não foi possível carregar dados de nenhuma fonte")

    def process_articles(self, df: pd.DataFrame, month_year: str) -> Dict:
        """
        Processa artigos do DataFrame
        
        Args:
            df: DataFrame com artigos
            month_year: String no formato 'YYYY_MM'
            
        Returns:
            Dicionário com resultados da extração
        """
        self.logger.info(f"Iniciando extração de marcas para {month_year}")
        self.logger.info(f"Total de artigos: {len(df)}")
        
        self.stats["total_articles"] = len(df)
        
        # Estrutura de dados para resultados
        results = {
            "month_year": month_year,
            "extraction_date": datetime.now().isoformat(),
            "total_articles": len(df),
            "processed_articles": 0,
            "exclusive_articles": [],
            "all_brands_frequency": {},
            "unique_brands": [],
            "statistics": {}
        }
        
        all_brands_set = set()
        
        for index, row in df.iterrows():
            try:
                article_id = str(row['Id'])
                title = str(row.get('Titulo', '')).strip()
                content = str(row.get('Conteudo', '')).strip()
                
                if not title and not content:
                    continue
                
                # Verificar cache
                content_hash = self.get_content_hash(title, content)
                if content_hash in self.processed_cache:
                    self.stats["skipped_cache"] += 1
                    continue
                
                # Extrair marcas com DeepSeek
                self.logger.info(f"Processando artigo {article_id}: {title[:50]}...")
                brands = self.extract_brands_with_deepseek(title, content)
                
                if brands:
                    # Aplicar filtros
                    filtered_brands = self.apply_automatic_filters(brands)
                    
                    if filtered_brands:
                        # Verificar exclusividade
                        exclusive_brand = self.check_exclusivity(filtered_brands, article_id, title)
                        
                        if exclusive_brand:
                            results["exclusive_articles"].append({
                                "article_id": article_id,
                                "title": title,
                                "exclusive_brand": exclusive_brand,
                                "all_brands": filtered_brands,
                                "content_preview": content[:200] + "..." if len(content) > 200 else content
                            })
                        
                        # Atualizar frequência de marcas
                        for brand in filtered_brands:
                            all_brands_set.add(brand)
                            if brand in results["all_brands_frequency"]:
                                results["all_brands_frequency"][brand] += 1
                            else:
                                results["all_brands_frequency"][brand] = 1
                
                # Adicionar ao cache
                self.processed_cache.add(content_hash)
                self.stats["processed_articles"] += 1
                
                # Pausa para não sobrecarregar API
                time.sleep(0.5)
                
                # Log de progresso
                if (index + 1) % 10 == 0:
                    self.logger.info(f"Progresso: {index + 1}/{len(df)} artigos")
                    
            except Exception as e:
                self.logger.error(f"Erro ao processar artigo {article_id}: {e}")
                continue
        
        # Finalizar resultados
        results["processed_articles"] = self.stats["processed_articles"]
        results["unique_brands"] = sorted(list(all_brands_set))
        results["statistics"] = self.stats.copy()
        
        self.stats["unique_brands"] = len(all_brands_set)
        
        return results

    def save_results(self, results: Dict, month_year: str):
        """
        Salva resultados em arquivos JSON na estrutura do projeto
        
        Args:
            results: Dicionário com resultados
            month_year: String no formato 'YYYY_MM'
        """
        try:
            # Arquivo principal de resultados
            output_file = self.output_dir / f"brands_month_{month_year}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Resultados salvos em: {output_file}")
            
            # Arquivo resumido apenas com artigos exclusivos
            exclusive_file = self.output_dir / f"exclusive_articles_{month_year}.json"
            exclusive_data = {
                "month_year": month_year,
                "extraction_date": results["extraction_date"],
                "total_exclusive_articles": len(results["exclusive_articles"]),
                "exclusive_articles": results["exclusive_articles"]
            }
            
            with open(exclusive_file, 'w', encoding='utf-8') as f:
                json.dump(exclusive_data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Artigos exclusivos salvos em: {exclusive_file}")
            
            # Arquivo de frequência de marcas para curadoria
            brands_file = self.output_dir / f"brands_frequency_{month_year}.json"
            frequency_data = {
                "month_year": month_year,
                "extraction_date": results["extraction_date"],
                "total_unique_brands": len(results["unique_brands"]),
                "brands_frequency": results["all_brands_frequency"],
                "sorted_by_frequency": sorted(
                    results["all_brands_frequency"].items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )
            }
            
            with open(brands_file, 'w', encoding='utf-8') as f:
                json.dump(frequency_data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Frequência de marcas salva em: {brands_file}")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar resultados: {e}")

    def run_extraction(self, month_year: Optional[str] = None):
        """
        Executa extração completa integrada com o projeto
        
        Args:
            month_year: String no formato 'YYYY_MM' (opcional, usa mês atual)
        """
        try:
            # Usar mês atual se não especificado
            if not month_year:
                month_year = datetime.now().strftime("%Y_%m")
            
            self.logger.info(f"Iniciando extração de marcas - período: {month_year}")
            
            # Carregar dados
            df = self.load_data_from_api()
            
            # Validar colunas necessárias
            required_columns = ['Id', 'Titulo', 'Conteudo']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Colunas obrigatórias ausentes: {missing_columns}")
            
            # Processar artigos
            results = self.process_articles(df, month_year)
            
            # Salvar resultados
            self.save_results(results, month_year)
            self.save_processed_cache()
            
            # Log final
            self.logger.info("=" * 60)
            self.logger.info("EXTRAÇÃO DE MARCAS CONCLUÍDA")
            self.logger.info("=" * 60)
            self.logger.info(f"Período: {month_year}")
            self.logger.info(f"Total de artigos: {self.stats['total_articles']}")
            self.logger.info(f"Processados: {self.stats['processed_articles']}")
            self.logger.info(f"Pulados (cache): {self.stats['skipped_cache']}")
            self.logger.info(f"Chamadas API DeepSeek: {self.stats['api_calls']}")
            self.logger.info(f"Marcas únicas encontradas: {self.stats['unique_brands']}")
            self.logger.info(f"Artigos exclusivos detectados: {self.stats['exclusive_articles']}")
            self.logger.info(f"Arquivos gerados em: {self.output_dir}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Erro durante extração: {e}")
            raise

def main():
    """Função para execução standalone do brand_extractor"""
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    print("🚀 BRAND EXTRACTOR - Detecção de Marcas Exclusivas")
    print("=" * 55)
    print()
    
    try:
        # Usar ConfigManager do projeto
        logger.info("Carregando ConfigManager...")
        config_manager = ConfigManager()
        logger.info("ConfigManager carregado com sucesso")
        
        # Criar extrator
        logger.info("Criando BrandExtractor...")
        extractor = BrandExtractor(config_manager)
        
        # Executar extração
        month_year = datetime.now().strftime("%Y_%m")
        print(f"📅 Executando extração para: {month_year}")
        print(f"💾 Resultados serão salvos em: {extractor.output_dir}")
        print()
        
        results = extractor.run_extraction(month_year)
        
        print()
        print("✅ Extração concluída com sucesso!")
        print()
        print("📄 Arquivos gerados:")
        print(f"   - brands_month_{month_year}.json")
        print(f"   - exclusive_articles_{month_year}.json") 
        print(f"   - brands_frequency_{month_year}.json")
        print()
        print("📊 Estatísticas:")
        print(f"   - Total de artigos: {results['total_articles']}")
        print(f"   - Artigos processados: {results['processed_articles']}")
        print(f"   - Artigos exclusivos: {len(results['exclusive_articles'])}")
        print(f"   - Marcas únicas: {len(results['unique_brands'])}")
        print()
        print("🎯 Próximos passos:")
        print("   1. Analise exclusive_articles para validar detecções")
        print("   2. Faça curadoria de brands_frequency")
        print("   3. Crie brands_master_list.json curado")
        print("   4. Integre com protagonismo_analyzer.py")
        
    except Exception as e:
        logger.error(f"Erro durante execução: {e}")
        print(f"❌ Erro: {e}")
        print("\n💡 Possíveis soluções:")
        print("1. Verifique se está no diretório correto (bradesco-news-analyzer)")
        print("2. Verifique se arquivo .env com DEEPSEEK_API_KEY existe")
        print("3. Verifique se arquivos src/config_manager.py e src/api_caller.py existem")

if __name__ == "__main__":
    main()