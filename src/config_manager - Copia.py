"""
Gerenciador de Configurações
Centraliza todas as configurações e variáveis globais do sistema
"""

import os
import json
from pathlib import Path
from typing import Dict, List

class ConfigManager:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self._setup_paths()
        self._setup_variables()
        self._load_api_key()
        self._load_channel_mappings()
    
    def _setup_paths(self):
        """Define todos os caminhos de diretórios"""
        # Diretórios principais
        self.pasta_api = self.base_path / "dados" / "api"
        self.pasta_marca_setor = self.base_path / "dados" / "marca_setor"
        self.pasta_config = self.base_path / "config"
        self.pasta_logs = self.base_path / "logs"
        
        # Arquivos de configuração
        self.config_file = self.pasta_config / "api_marca_configs.json"
        self.arq_protagonismo = self.pasta_config / "nivel_protagonismo_claude_bradesco.xlsx"
        
        # Arquivos de dados da API
        self.favoritos_marca = "Favoritos_Marcas.xlsx"
        self.arq_api_original = self.pasta_api / self.favoritos_marca
        
        self.favoritos_small_marca = "Favoritos_Marcas_small.xlsx"
        self.arq_api = self.pasta_api / self.favoritos_small_marca
        
        # Arquivos de resultados
        self.protagonismo_result = "resultados_protagonismo.xlsx"
        self.arq_protagonismo_result = self.pasta_marca_setor / self.protagonismo_result
        
        self.consolidado = "Favoritos_Marca_Consolidado.xlsx"
        self.arq_consolidado = self.pasta_marca_setor / self.consolidado
        
        self.lote = "Favoritos_Marca_Consolidado.xlsx"
        self.arq_lote = self.pasta_marca_setor / self.lote
        
        self.lote_final = "Tabela_atualizacao_em_lote.xlsx"
        self.arq_lote_final = self.pasta_marca_setor / self.lote_final
        
        self.lote_final_limpo = "Tabela_atualizacao_em_lote_limpo.xlsx"
        self.arq_lote_final_limpo = self.pasta_marca_setor / self.lote_final_limpo
    
    def _setup_variables(self):
        """Define variáveis globais do sistema"""
        # Marcas a serem analisadas
        self.w_marcas = ['Bradesco', 'Itaú', 'Santander']
        
        # Configurações da API DeepSeek
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
        # Colunas de interesse para o arquivo final
        self.colunas_interesse = [
            'Id',
            'Bradesco_nivel_protagonismo',
            'Itaú_nivel_protagonismo',
            'Santander_nivel_protagonismo'
        ]
        
        # Mapeamento para renomear colunas
        self.renomear_colunas = {
            'Bradesco_nivel_protagonismo': 'Nivel de Protagonismo Bradesco',
            'Itaú_nivel_protagonismo': 'Nivel de Protagonismo Itaú',
            'Santander_nivel_protagonismo': 'Nivel de Protagonismo Santander'
        }
    
    def _load_api_key(self):
        """Carrega a chave da API de forma segura"""
        # Prioridade: variável de ambiente > arquivo .env > input do usuário
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        
        if not self.api_key:
            env_file = self.base_path / '.env'
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith('DEEPSEEK_API_KEY='):
                            self.api_key = line.split('=', 1)[1].strip()
                            break
        
        if not self.api_key:
            raise ValueError(
                "Chave da API DeepSeek não encontrada. "
                "Defina a variável de ambiente DEEPSEEK_API_KEY ou "
                "crie um arquivo .env com DEEPSEEK_API_KEY=sua_chave"
            )
    
    def _load_channel_mappings(self):
        """Carrega configurações de mapeamento de canais"""
        try:
            from src.config.channel_mappings import (
                get_all_mappings, 
                normalize_channel_field, 
                get_brand_terms,
                get_specific_content_terms,
                check_specific_content_requirements
            )
            self.channel_mappings = get_all_mappings()
            self.normalize_channel_field = normalize_channel_field
            self.get_brand_terms = get_brand_terms
            self.get_specific_content_terms = get_specific_content_terms
            self.check_specific_content_requirements = check_specific_content_requirements
        except ImportError:
            # Fallback se não conseguir importar
            self.channel_mappings = {marca: [marca] for marca in self.w_marcas}
            self.normalize_channel_field = lambda x: str(x)
            self.get_brand_terms = lambda marca: [marca]
            self.get_specific_content_terms = lambda: {}
            self.check_specific_content_requirements = lambda x, y: {'found_specific_terms': [], 'should_be_minimum_citation': False}
    
    def get_api_headers(self) -> Dict[str, str]:
        """Retorna os headers para a API"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def load_api_configs(self) -> List[Dict]:
        """Carrega as configurações da API do arquivo JSON"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {self.config_file}")
        
        with open(self.config_file, "r", encoding='utf-8') as f:
            return json.load(f)
    
    def get_paths_dict(self) -> Dict[str, Path]:
        """Retorna um dicionário com todos os caminhos"""
        return {
            'pasta_api': self.pasta_api,
            'pasta_marca_setor': self.pasta_marca_setor,
            'pasta_config': self.pasta_config,
            'arq_api_original': self.arq_api_original,
            'arq_api': self.arq_api,
            'arq_protagonismo': self.arq_protagonismo,
            'arq_protagonismo_result': self.arq_protagonismo_result,
            'arq_consolidado': self.arq_consolidado,
            'arq_lote': self.arq_lote,
            'arq_lote_final': self.arq_lote_final,
            'arq_lote_final_limpo': self.arq_lote_final_limpo
        }