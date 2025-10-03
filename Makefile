# Makefile para facilitar comandos do projeto

.PHONY: help install run clean build docker-build docker-run setup test

# Variáveis
PYTHON := python
VENV := venv
DOCKER_IMAGE := protagonismo-analyzer
DOCKER_CONTAINER := protagonismo-analyzer-container

help: ## Mostra esta ajuda
	@echo "Comandos disponíveis:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Configuração inicial do projeto
	@echo "Configurando projeto..."
	@$(PYTHON) -m venv $(VENV)
	@echo "Ativando ambiente virtual e instalando dependências..."
	@. $(VENV)/bin/activate && pip install --upgrade pip
	@. $(VENV)/bin/activate && pip install -r requirements.txt
	@echo "Criando diretórios necessários..."
	@mkdir -p config dados/api dados/marca_setor logs
	@echo "Copiando arquivos de exemplo..."
	@cp .env.example .env || echo "Arquivo .env já existe"
	@cp config/api_marca_configs.json.example config/api_marca_configs.json || echo "Arquivo de config já existe"
	@echo "Setup concluído! Configure o arquivo .env com sua chave da API"

install: ## Instala dependências
	@. $(VENV)/bin/activate && pip install -r requirements.txt

run: ## Executa o programa
	@. $(VENV)/bin/activate && $(PYTHON) main.py

clean: ## Limpa arquivos temporários
	@echo "Limpando arquivos temporários..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@rm -rf build/ dist/ *.egg-info/
	@rm -f *.log

build: ## Cria build de distribuição
	@. $(VENV)/bin/activate && $(PYTHON) setup.py sdist bdist_wheel

docker-build: ## Constrói imagem Docker
	@echo "Construindo imagem Docker..."
	@docker build -t $(DOCKER_IMAGE) .

docker-run: ## Executa com Docker Compose
	@echo "Executando com Docker Compose..."
	@docker-compose up --build

docker-stop: ## Para containers Docker
	@echo "Parando containers..."
	@docker-compose down

docker-logs: ## Mostra logs do container
	@docker-compose logs -f

test: ## Executa testes (quando implementados)
	@echo "Executando testes..."
	@. $(VENV)/bin/activate && $(PYTHON) -m pytest tests/ -v

lint: ## Executa linting do código
	@. $(VENV)/bin/activate && flake8 src/ main.py
	@. $(VENV)/bin/activate && black --check src/ main.py

format: ## Formata código
	@. $(VENV)/bin/activate && black src/ main.py

requirements: ## Atualiza requirements.txt
	@. $(VENV)/bin/activate && pip freeze > requirements.txt

dev-setup: setup ## Configuração para desenvolvimento
	@. $(VENV)/bin/activate && pip install black flake8 pytest
	@echo "Ambiente de desenvolvimento configurado!"

status: ## Mostra status do projeto
	@echo "Status do projeto:"
	@echo "- Ambiente virtual: $(shell [ -d $(VENV) ] && echo "✅ Existe" || echo "❌ Não existe")"
	@echo "- Arquivo .env: $(shell [ -f .env ] && echo "✅ Existe" || echo "❌ Não existe")"
	@echo "- Config API: $(shell [ -f config/api_marca_configs.json ] && echo "✅ Existe" || echo "❌ Não existe")"
	@echo "- Config Protagonismo: $(shell [ -f config/nivel_protagonismo_claude_bradesco.xlsx ] && echo "✅ Existe" || echo "❌ Não existe")"

all: clean setup ## Reinstalação completa

# Comando padrão
.DEFAULT_GOAL := help