#!/usr/bin/env python3
"""
Sistema de Análise de Notícias - Programa Principal
Orquestra as chamadas para os módulos de processamento
"""

import os
import sys
from pathlib import Path
import logging
from datetime import datetime

# Adicionar o diretório atual ao path para importações
sys.path.append(str(Path(__file__).parent))

# Importar módulos do projeto
from src.config_manager import ConfigManager
from src.api_caller import APICaller
from src.protagonismo_analyzer import ProtagonismoAnalyzer
from src.data_consolidator import DataConsolidator
from src.batch_processor import BatchProcessor
from src.utils.file_utils import create_directories, setup_download_button

def setup_logging():
    """Configura o sistema de logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def main():
    """Função principal do sistema"""
    logger = setup_logging()
    logger.info("Iniciando Sistema de Análise de Notícias")
    
    try:
        # Criar diretórios necessários
        create_directories()
        
        # Carregar configurações
        config_manager = ConfigManager()
        logger.info("Configurações carregadas com sucesso")
        
        # Etapa 1: Chamar API e carregar dados
        logger.info("Iniciando chamada da API...")
        api_caller = APICaller(config_manager)
        final_df = api_caller.fetch_data()
        
        if final_df.empty:
            logger.error("Nenhum dado foi retornado pela API")
            return
        
        logger.info(f"API retornou {len(final_df)} registros")
        
        # Etapa 2: Análise de protagonismo
        logger.info("Iniciando análise de protagonismo...")
        protagonismo_analyzer = ProtagonismoAnalyzer(config_manager)
        df_resultados = protagonismo_analyzer.analyze_protagonismo(final_df)
        
        if df_resultados.empty:
            logger.error("Análise de protagonismo não retornou resultados")
            return
        
        logger.info(f"Análise de protagonismo gerou {len(df_resultados)} resultados")
        
        # Etapa 3: Consolidação dos dados
        logger.info("Iniciando consolidação dos dados...")
        consolidator = DataConsolidator(config_manager)
        final_df_consolidado = consolidator.consolidate_data(final_df, df_resultados)
        
        logger.info(f"Consolidação gerou {len(final_df_consolidado)} registros")
        
        # Etapa 4: Processamento em lote
        logger.info("Iniciando processamento em lote...")
        batch_processor = BatchProcessor(config_manager)
        arquivo_final = batch_processor.process_batch(final_df_consolidado, final_df)
        
        if arquivo_final:
            logger.info(f"Processamento concluído. Arquivo gerado: {arquivo_final}")
            
            # Habilitar download do arquivo
            setup_download_button(arquivo_final)
            
        logger.info("Sistema executado com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante a execução: {str(e)}")
        raise

if __name__ == "__main__":
    main()