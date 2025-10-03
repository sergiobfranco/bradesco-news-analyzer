"""
Módulo com funções utilitárias.
"""

import os
import logging
from pathlib import Path
from typing import Union

def setup_logging():
    """Configura o sistema de logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def create_directories():
    """Cria os diretórios necessários para o projeto."""
    directories = [
        'config',
        'dados',
        'dados/api',
        'dados/marca_setor',
        'logs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def generate_download_button(file_path: Union[str, Path]):
    """
    Gera um botão de download para o arquivo especificado.
    Esta função pode ser expandida para diferentes ambientes (web, desktop, etc.)
    
    Args:
        file_path: Caminho para o arquivo a ser disponibilizado para download
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logging.error(f"Arquivo não encontrado: {file_path}")
        return
    
    # Para ambiente local/docker, apenas exibe informações sobre o arquivo
    print("\n" + "="*50)
    print("ARQUIVO GERADO COM SUCESSO!")
    print("="*50)
    print(f"Arquivo: {file_path.name}")
    print(f"Caminho completo: {file_path.absolute()}")
    print(f"Tamanho: {file_path.stat().st_size} bytes")
    print("\nO arquivo está disponível no caminho indicado acima.")
    
    # Em um ambiente web (Flask/Django), você poderia implementar:
    # - Endpoint para download
    # - Link de download
    # - Redirecionamento automático
    
    # Em um ambiente desktop, você poderia implementar:
    # - Abrir explorador de arquivos
    # - Copiar para área de transferência
    # - Enviar por email

def validate_environment():
    """Valida se o ambiente está configurado corretamente."""
    required_env_vars = ['DEEPSEEK_API_KEY']
    missing_vars = []
    
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("ATENÇÃO: Variáveis de ambiente faltando:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nConfigure as variáveis de ambiente ou use arquivo de configuração.")
        return False
    
    return True

def check_config_files():
    """Verifica se os arquivos de configuração necessários existem."""
    config_files = [
        'config/api_marca_configs.json',
        'config/nivel_protagonismo_claude_bradesco.xlsx'
    ]
    
    missing_files = []
    for file_path in config_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("ATENÇÃO: Arquivos de configuração faltando:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    return True