#!/bin/bash

# Script para facilitar a execução do projeto

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Analisador de Protagonismo - Bradesco ===${NC}"

# Função para verificar se um comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Função para verificar arquivos necessários
check_requirements() {
    echo -e "${YELLOW}Verificando requisitos...${NC}"
    
    # Verificar Python
    if ! command_exists python3 && ! command_exists python; then
        echo -e "${RED}❌ Python não encontrado. Instale Python 3.9+${NC}"
        exit 1
    fi
    
    # Verificar se existe .env ou DEEPSEEK_API_KEY
    if [ ! -f .env ] && [ -z "$DEEPSEEK_API_KEY" ]; then
        echo -e "${RED}❌ Chave da API não configurada. Crie arquivo .env ou defina DEEPSEEK_API_KEY${NC}"
        exit 1
    fi
    
    # Verificar arquivos de configuração
    if [ ! -f config/api_marca_configs.json ]; then
        echo -e "${RED}❌ Arquivo config/api_marca_configs.json não encontrado${NC}"
        exit 1
    fi
    
    if [ ! -f config/nivel_protagonismo_claude_bradesco.xlsx ]; then
        echo -e "${RED}❌ Arquivo config/nivel_protagonismo_claude_bradesco.xlsx não encontrado${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Todos os requisitos atendidos${NC}"
}

# Função para configuração inicial
setup() {
    echo -e "${YELLOW}Executando configuração inicial...${NC}"
    
    # Criar diretórios
    mkdir -p config dados/api dados/marca_setor logs
    
    # Criar ambiente virtual se não existir
    if [ ! -d "venv" ]; then
        echo "Criando ambiente virtual..."
        python3 -m venv venv
    fi
    
    # Ativar ambiente virtual e instalar dependências
    echo "Instalando dependências..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo -e "${GREEN}✅ Configuração concluída${NC}"
}

# Função para executar o programa
run_local() {
    echo -e "${YELLOW}Executando localmente...${NC}"
    
    # Ativar ambiente virtual
    source venv/bin/activate
    
    # Executar programa principal
    python main.py
}

# Função para executar com Docker
run_docker() {
    echo -e "${YELLOW}Executando com Docker...${NC}"
    
    if ! command_exists docker; then
        echo -e "${RED}❌ Docker não encontrado. Instale Docker primeiro.${NC}"
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        echo -e "${RED}❌ Docker Compose não encontrado. Instale Docker Compose primeiro.${NC}"
        exit 1
    fi
    
    docker-compose up --build
}

# Função para mostrar ajuda
show_help() {
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "Comandos disponíveis:"
    echo "  setup     - Configuração inicial do projeto"
    echo "  local     - Executar localmente (padrão)"
    echo "  docker    - Executar com Docker"
    echo "  check     - Verificar requisitos"
    echo "  help      - Mostrar esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  $0              # Executa localmente"
    echo "  $0 setup        # Configuração inicial"
    echo "  $0 docker       # Executa com Docker"
}

# Processar argumentos
case "${1:-local}" in
    "setup")
        setup
        ;;
    "local")
        check_requirements
        run_local
        ;;
    "docker")
        run_docker
        ;;
    "check")
        check_requirements
        ;;
    "help")
        show_help
        ;;
    *)
        echo -e "${RED}❌ Comando desconhecido: $1${NC}"
        show_help
        exit 1
        ;;
esac

echo -e "${GREEN}=== Processo finalizado ===${NC}"