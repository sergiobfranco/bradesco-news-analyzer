#!/usr/bin/env python3
"""
Interface Streamlit para Sistema de Análise de Notícias - Bradesco Centimetragem
Orquestra o processamento e permite download dos arquivos gerados
"""

import os
import sys
import streamlit as st
from pathlib import Path
import logging
from datetime import datetime
import pandas as pd
import time
from glob import glob
from PIL import Image
import pytz

# Adicionar o diretório atual ao path para importações
sys.path.append(str(Path(__file__).parent))

# Importar módulos do projeto
from src.config_manager import ConfigManager
from src.api_caller import APICaller
from src.protagonismo_analyzer import ProtagonismoAnalyzer
from src.data_consolidator import DataConsolidator
from src.batch_processor import BatchProcessor
from src.utils.file_utils import create_directories

# Configuração da página
st.set_page_config(
    page_title="Bradesco Centimetragem",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuração de logging
class SaoPauloFormatter(logging.Formatter):
    """Formattador de log que usa o fuso horário de São Paulo"""
    
    def formatTime(self, record, datefmt=None):
        sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
        ct = datetime.fromtimestamp(record.created, tz=sao_paulo_tz)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = ct.strftime(self.default_time_format)
        return s

def setup_logging():
    """Configura o sistema de logging"""
    formatter = SaoPauloFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Garantir que o diretório de logs existe
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    file_handler = logging.FileHandler(log_dir / 'app.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, stream_handler]
    )
    return logging.getLogger(__name__)

def rotate_logs():
    """Rotaciona os arquivos de log para manter apenas os últimos 3 processamentos"""
    logger.info("Iniciando rotação de logs")
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    base_log = log_dir / 'app.log'
    
    # Se o arquivo principal não existe, nada a fazer
    if not base_log.exists():
        logger.info("Arquivo de log principal não existe, pulando rotação")
        return
    
    # Rotacionar: mover .2 para .3 (deletar), .1 para .2, principal para .1
    log_3 = log_dir / 'app.log.3'
    if log_3.exists():
        log_3.unlink()  # Deletar o mais antigo
        logger.info("Deletado app.log.3")
    
    log_2 = log_dir / 'app.log.2'
    if log_2.exists():
        log_2.rename(log_3)
        logger.info("Movido app.log.2 para app.log.3")
    
    log_1 = log_dir / 'app.log.1'
    if log_1.exists():
        log_1.rename(log_2)
        logger.info("Movido app.log.1 para app.log.2")
    
    # Mover o principal para .1
    base_log.rename(log_1)
    logger.info("Movido app.log para app.log.1")

logger = setup_logging()

# Inicialização do session state
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'last_processed_file' not in st.session_state:
    st.session_state.last_processed_file = None
if 'processing_confirmed' not in st.session_state:
    st.session_state.processing_confirmed = False

def get_latest_files(directory='downloads', pattern='Tabela_atualizacao_em_lote_limpo_*.xlsx', limit=10):
    """
    Retorna os últimos N arquivos que correspondem ao padrão especificado
    
    Args:
        directory: Diretório onde procurar os arquivos
        pattern: Padrão de nome dos arquivos
        limit: Número máximo de arquivos a retornar
    
    Returns:
        Lista de tuplas (caminho_completo, nome_arquivo, data_modificação)
    """
    try:
        # Fuso horário de São Paulo
        sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
        
        # Tentar vários caminhos possíveis
        possible_paths = [
            directory,
            f'/app/{directory}',
            os.path.join(os.getcwd(), directory)
        ]
        
        files = []
        for base_path in possible_paths:
            if os.path.exists(base_path):
                search_pattern = os.path.join(base_path, pattern)
                found_files = glob(search_pattern)
                if found_files:
                    files.extend(found_files)
                    break
        
        if not files:
            # Se não encontrou nada, criar o diretório
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.warning(f"Nenhum arquivo encontrado em {directory} com padrão {pattern}")
            return []
        
        # Remover duplicatas mantendo o caminho mais curto
        unique_files = {}
        for f in files:
            basename = os.path.basename(f)
            if basename not in unique_files or len(f) < len(unique_files[basename]):
                unique_files[basename] = f
        
        # Ordenar por data de modificação (mais recente primeiro)
        files_with_time = [
            (f, os.path.basename(f), datetime.fromtimestamp(os.path.getmtime(f), tz=sao_paulo_tz))
            for f in unique_files.values()
        ]
        files_with_time.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(f"Encontrados {len(files_with_time)} arquivo(s) em {directory}")
        
        return files_with_time[:limit]
    
    except Exception as e:
        logger.error(f"Erro ao buscar arquivos: {str(e)}")
        return []

def run_processing():
    """
    Executa o processamento completo do sistema
    """
    try:
        # Criar diretórios necessários
        create_directories()
        
        # Carregar configurações
        config_manager = ConfigManager()
        logger.info("Configurações carregadas com sucesso")
        
        # Etapa 1: Chamar API e carregar dados
        with st.spinner('📡 Chamando API e carregando dados...'):
            logger.info("Iniciando chamada da API...")
            api_caller = APICaller(config_manager)
            final_df = api_caller.fetch_data()
            
            if final_df.empty:
                st.error("❌ Nenhum dado foi retornado pela API")
                return None
            
            logger.info(f"API retornou {len(final_df)} registros")
            st.success(f"✅ API retornou {len(final_df)} registros")
        
        # Etapa 2: Análise de protagonismo
        with st.spinner('🔍 Analisando protagonismo das marcas...'):
            logger.info("Iniciando análise de protagonismo...")
            protagonismo_analyzer = ProtagonismoAnalyzer(config_manager)
            df_resultados = protagonismo_analyzer.analyze_protagonismo(final_df)
            
            if df_resultados.empty:
                st.error("❌ Análise de protagonismo não retornou resultados")
                return None
            
            logger.info(f"Análise de protagonismo gerou {len(df_resultados)} resultados")
            st.success(f"✅ Análise gerou {len(df_resultados)} resultados")
        
        # Etapa 3: Consolidação dos dados
        with st.spinner('📊 Consolidando dados...'):
            logger.info("Iniciando consolidação dos dados...")
            consolidator = DataConsolidator(config_manager)
            final_df_consolidado = consolidator.consolidate_data(final_df, df_resultados)
            
            logger.info(f"Consolidação gerou {len(final_df_consolidado)} registros")
            st.success(f"✅ Consolidação gerou {len(final_df_consolidado)} registros")
        
        # Etapa 4: Processamento em lote
        with st.spinner('⚙️ Processando em lote e gerando arquivo final...'):
            logger.info("Iniciando processamento em lote...")
            batch_processor = BatchProcessor(config_manager)
            arquivo_final = batch_processor.process_batch(final_df_consolidado, final_df)
            
            if arquivo_final:
                logger.info(f"Processamento concluído. Arquivo gerado: {arquivo_final}")
                st.success(f"✅ Arquivo gerado com sucesso!")
                
                # Tentar encontrar o arquivo no diretório de downloads
                # O batch_processor pode retornar o caminho completo ou relativo
                if os.path.exists(arquivo_final):
                    return arquivo_final
                elif os.path.exists(f"downloads/{os.path.basename(arquivo_final)}"):
                    return f"downloads/{os.path.basename(arquivo_final)}"
                elif os.path.exists(f"/app/downloads/{os.path.basename(arquivo_final)}"):
                    return f"/app/downloads/{os.path.basename(arquivo_final)}"
                else:
                    logger.warning(f"Arquivo gerado mas não encontrado em: {arquivo_final}")
                    return arquivo_final
            else:
                logger.error("Erro ao gerar arquivo final")
                return None
        
    except Exception as e:
        logger.error(f"Erro durante a execução: {str(e)}", exc_info=True)
        return None

def load_logo():
    """Carrega o logo do Bradesco"""
    logo_paths = [
        'bradesco-logo.png',
        '/app/bradesco-logo.png',
        'assets/bradesco-logo.png',
        '/app/assets/bradesco-logo.png'
    ]
    
    for logo_path in logo_paths:
        if os.path.exists(logo_path):
            try:
                return Image.open(logo_path)
            except Exception as e:
                logger.error(f"Erro ao carregar logo de {logo_path}: {str(e)}")
    
    logger.warning("Logo do Bradesco não encontrado")
    return None

def main():
    """Interface principal do Streamlit"""
    
    # Carregar e exibir logo no topo
    logo = load_logo()
    
    # Header com logo e título
    col_logo, col_title = st.columns([1, 4])
    
    with col_logo:
        if logo:
            st.image(logo, width=150)
    
    with col_title:
        st.title("Bradesco Centimetragem")
        st.markdown("Sistema de Análise de Notícias")
    
    st.markdown("---")
    
    # Sidebar com informações
    with st.sidebar:
        # Logo menor na sidebar
        if logo:
            st.image(logo, width=120)
            st.markdown("---")
        
        st.header("ℹ️ Informações")
        st.markdown("""
        Este sistema realiza:
        - 📡 Coleta de dados via API
        - 🔍 Análise de protagonismo
        - 📊 Consolidação de dados
        - ⚙️ Processamento em lote
        - 📥 Geração de arquivo final
        """)
        
        st.markdown("---")
        
        # Status do processamento
        st.header("📊 Status")
        if st.session_state.processing:
            st.warning("🔄 Processamento em andamento...")
        else:
            st.success("✅ Sistema pronto")
        
        st.markdown("---")
        
        # Informações de log
        st.header("📝 Últimos Logs")
        log_dir = Path('logs')
        log_files = [log_dir / 'app.log', log_dir / 'app.log.1', log_dir / 'app.log.2', log_dir / 'app.log.3']
        all_logs = []
        
        for log_file in log_files:
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                        if lines:
                            # Pegar as últimas 3 linhas de cada arquivo de log
                            last_lines = lines[-3:]
                            all_logs.extend(last_lines)
                except Exception as e:
                    logger.error(f"Erro ao ler {log_file}: {str(e)}")
        
        if all_logs:
            # Combinar todas as linhas (já ordenadas por recência de arquivo)
            last_logs = ''.join(all_logs)
            st.text_area("Logs", last_logs, height=200, label_visibility="collapsed")
        else:
            st.info("Nenhum log disponível ainda")
    
    # Área principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🚀 Processamento")
        
        # Botão de processamento
        if not st.session_state.processing:
            if st.button("▶️ Iniciar Processamento", 
                        type="primary", 
                        use_container_width=True,
                        disabled=st.session_state.processing_confirmed):
                st.session_state.processing_confirmed = True
                st.rerun()
        
        # Confirmação de processamento
        if st.session_state.processing_confirmed and not st.session_state.processing:
            st.warning("⚠️ Você tem certeza que deseja iniciar o processamento?")
            
            col_yes, col_no = st.columns(2)
            
            with col_yes:
                if st.button("✅ Sim, processar", type="primary", use_container_width=True):
                    # Rotacionar logs antes de iniciar novo processamento
                    rotate_logs()
                    st.session_state.processing = True
                    st.session_state.processing_confirmed = False
                    st.rerun()
            
            with col_no:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state.processing_confirmed = False
                    st.rerun()
        
        # Executar processamento
        if st.session_state.processing:
            st.info("🔄 Processamento em andamento. Por favor, aguarde...")
            
            # Container para mensagens de progresso
            progress_container = st.container()
            
            with progress_container:
                arquivo_final = run_processing()
                
                if arquivo_final:
                    st.session_state.last_processed_file = arquivo_final
                    st.balloons()
                    st.success("🎉 Processamento concluído com sucesso!")
                    
                    # Informar sobre o arquivo gerado
                    st.info(f"📄 Arquivo: {os.path.basename(arquivo_final)}")
                else:
                    # Tentar encontrar arquivo gerado recentemente
                    recent_files = get_latest_files(limit=1)
                    if recent_files:
                        arquivo_final = recent_files[0][0]
                        st.session_state.last_processed_file = arquivo_final
                        st.balloons()
                        st.success("🎉 Processamento concluído com sucesso!")
                        st.info(f"📄 Arquivo: {os.path.basename(arquivo_final)}")
                        logger.info(f"Arquivo encontrado apesar de process_batch retornar None: {arquivo_final}")
                    else:
                        st.error("❌ Processamento falhou. Verifique os logs para mais detalhes.")
            
            # Resetar estado
            st.session_state.processing = False
            time.sleep(2)
            st.rerun()
    
    with col2:
        st.header("📊 Estatísticas")
        
        # Buscar arquivos gerados
        files = get_latest_files()
        
        if files:
            st.metric("Arquivos Gerados", len(files))
            
            # Último arquivo processado
            if files:
                last_file = files[0]
                st.metric("Último Processamento", 
                         last_file[2].strftime("%d/%m/%Y %H:%M"))
        else:
            st.info("Nenhum arquivo gerado ainda")
    
    # Seção de download
    st.markdown("---")
    st.header("📥 Downloads Disponíveis")
    
    files = get_latest_files()
    
    if files:
        st.success(f"✅ {len(files)} arquivo(s) disponível(is) para download")
        
        # Criar colunas para downloads
        for idx, (filepath, filename, mod_time) in enumerate(files):
            col_info, col_download = st.columns([3, 1])
            
            with col_info:
                # Destacar o último arquivo processado
                if st.session_state.last_processed_file and filepath == st.session_state.last_processed_file:
                    st.markdown(f"**🆕 {filename}**")
                else:
                    st.markdown(f"📄 {filename}")
                
                st.caption(f"Gerado em: {mod_time.strftime('%d/%m/%Y às %H:%M:%S')}")
            
            with col_download:
                try:
                    with open(filepath, 'rb') as f:
                        st.download_button(
                            label="⬇️ Download",
                            data=f,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_{idx}"
                        )
                except Exception as e:
                    st.error(f"Erro: {str(e)}")
                    logger.error(f"Erro ao preparar download de {filepath}: {str(e)}")
            
            if idx < len(files) - 1:
                st.markdown("---")
    else:
        st.info("ℹ️ Nenhum arquivo disponível para download. Execute o processamento para gerar arquivos.")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray; padding: 20px;'>
            Bradesco Centimetragem | Sistema de Análise de Notícias | Desenvolvido com Streamlit
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()