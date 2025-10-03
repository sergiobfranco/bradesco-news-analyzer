"""
Utilitários para manipulação de arquivos e diretórios
"""

import os
import logging
from pathlib import Path
from typing import Optional

def create_directories():
    """
    Cria todos os diretórios necessários para o projeto
    """
    logger = logging.getLogger(__name__)
    base_path = Path(__file__).parent.parent.parent
    
    directories = [
        base_path / "dados" / "api",
        base_path / "dados" / "marca_setor", 
        base_path / "config",
        base_path / "logs",
        base_path / "downloads"
    ]
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Diretório criado/verificado: {directory}")
        except Exception as e:
            logger.error(f"Erro ao criar diretório {directory}: {str(e)}")
            raise

def setup_download_button(arquivo_path: str):
    """
    Configura um botão de download para o arquivo (simulação para ambiente Docker)
    Em um ambiente web real, isso seria implementado diferentemente
    """
    logger = logging.getLogger(__name__)
    
    # Copia arquivo para pasta de downloads
    base_path = Path(__file__).parent.parent.parent
    downloads_dir = base_path / "downloads"
    downloads_dir.mkdir(exist_ok=True)
    
    arquivo_origem = Path(arquivo_path)
    if arquivo_origem.exists():
        import shutil
        arquivo_destino = downloads_dir / arquivo_origem.name
        shutil.copy2(arquivo_origem, arquivo_destino)
        logger.info(f"Arquivo disponível para download em: {arquivo_destino}")
        
        # Exibe instruções para download
        print(f"\n{'='*60}")
        print("ARQUIVO PRONTO PARA DOWNLOAD")
        print(f"{'='*60}")
        print(f"Arquivo: {arquivo_origem.name}")
        print(f"Localização: {arquivo_destino}")
        print(f"{'='*60}\n")
        
        return str(arquivo_destino)
    else:
        logger.error(f"Arquivo não encontrado para download: {arquivo_path}")
        return None

def validate_file_exists(filepath: Path, description: str = "") -> bool:
    """
    Valida se um arquivo existe
    """
    logger = logging.getLogger(__name__)
    
    if filepath.exists():
        logger.info(f"Arquivo encontrado: {filepath} {description}")
        return True
    else:
        logger.error(f"Arquivo não encontrado: {filepath} {description}")
        return False

def get_file_size(filepath: Path) -> Optional[int]:
    """
    Retorna o tamanho do arquivo em bytes
    """
    try:
        return filepath.stat().st_size
    except:
        return None

def clean_temp_files(temp_dir: Path):
    """
    Limpa arquivos temporários
    """
    logger = logging.getLogger(__name__)
    
    try:
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)
            logger.info(f"Diretório temporário removido: {temp_dir}")
    except Exception as e:
        logger.warning(f"Erro ao remover diretório temporário: {str(e)}")