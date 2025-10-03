# Sistema de Análise de Notícias - Bradesco

Sistema automatizado para análise de protagonismo de marcas bancárias (Bradesco, Itaú, Santander) em notícias, utilizando API DeepSeek para classificação inteligente.

## 📋 Funcionalidades

- **Coleta de Dados**: Chamadas automatizadas para APIs de notícias
- **Análise de Protagonismo**: Classificação inteligente usando DeepSeek AI
- **Consolidação**: Processamento e organização dos dados
- **Relatórios**: Geração de planilhas Excel com hyperlinks
- **Containerização**: Suporte completo ao Docker

## 🚀 Instalação Rápida

### Opção 1: Docker (Recomendado)

```bash
# Clone o projeto
git clone <url-do-repositorio>
cd sistema-analise-noticias

# Configure a chave da API
cp .env.example .env
# Edite o arquivo .env e configure DEEPSEEK_API_KEY=sua_chave_aqui

# Execute com Docker
docker-compose up --build
```

### Opção 2: Instalação Local

```bash
# Clone o projeto
git clone <url-do-repositorio>
cd sistema-analise-noticias

# Execute o setup
python setup.py

# Configure a chave da API no arquivo .env
# Execute o sistema
python main.py
```

## 📁 Estrutura do Projeto

```
sistema-analise-noticias/
├── main.py                     # Programa principal
├── requirements.txt            # Dependências Python
├── Dockerfile                  # Configuração Docker
├── docker-compose.yml          # Orquestração Docker
├── setup.py                    # Script de instalação
├── .env.example               # Exemplo de configuração
├── src/                       # Código fonte
│   ├── config_manager.py      # Gerenciador de configurações
│   ├── api_caller.py          # Chamadas da API
│   ├── protagonismo_analyzer.py # Análise de protagonismo
│   ├── data_consolidator.py   # Consolidação de dados
│   ├── batch_processor.py     # Processamento em lote
│   └── utils/                 # Utilitários
│       └── file_utils.py      # Manipulação de arquivos
├── dados/                     # Dados processados
│   ├── api/                   # Dados brutos da API
│   └── marca_setor/          # Dados consolidados
├── config/                    # Arquivos de configuração
│   ├── api_marca_configs.json # Configurações da API
│   └── nivel_protagonismo_claude_bradesco.xlsx # Tabela de protagonismo
├── logs/                      # Logs do sistema
└── downloads/                 # Arquivos para download
```

## ⚙️ Configuração

### 1. Chave da API DeepSeek

Configure sua chave da API DeepSeek de uma das formas:

**Opção A: Arquivo .env**
```bash
DEEPSEEK_API_KEY=sk-sua_chave_aqui
```

**Opção B: Variável de ambiente**
```bash
export DEEPSEEK_API_KEY=sk-sua_chave_aqui
```

### 2. Arquivos de Configuração Necessários

Coloque os seguintes arquivos na pasta `config/`:

- `api_marca_configs.json`: Configurações das APIs de notícias
- `nivel_protagonismo_claude_bradesco.xlsx`: Tabela de níveis de protagonismo

### 3. Estrutura do arquivo api_marca_configs.json

```json
[
  {
    "url": "https://api.exemplo.com/noticias",
    "data": {
      "filtros": {...},
      "parametros": {...}
    }
  }
]
```

## 🔄 Fluxo de Processamento

1. **Coleta de Dados** (`api_caller.py`)
   - Lê configurações da API
   - Faz chamadas para endpoints configurados
   - Salva dados brutos e processados

2. **Análise de Protagonismo** (`protagonismo_analyzer.py`)
   - Analisa cada notícia para cada marca
   - Usa DeepSeek AI para classificação
   - Gera classificações: Dedicada, Conteúdo, Citação

3. **Consolidação** (`data_consolidator.py`)
   - Consolida dados de notícias e protagonismo
   - Aplica filtros e validações
   - Remove registros inválidos

4. **Processamento Final** (`batch_processor.py`)
   - Cria planilha de atualização em lote
   - Adiciona hyperlinks para URLs
   - Gera arquivo final com timestamp

## 📊 Saídas do Sistema

### Arquivos Gerados

- `Favoritos_Marcas.xlsx`: Dados completos da API
- `Favoritos_Marcas_small.xlsx`: Dados resumidos da API  
- `resultados_protagonismo_TIMESTAMP.xlsx`: Resultados da análise
- `Favoritos_Marca_Consolidado.xlsx`: Dados consolidados
- `Tabela_atualizacao_em_lote_limpo_TIMESTAMP.xlsx`: Arquivo final

### Colunas do Arquivo Final

- `Id`: Identificador da notícia
- `UrlVisualizacao`: Link para visualizar notícia (com hyperlink)
- `UrlOriginal`: URL original da notícia
- `Titulo`: Título da notícia
- `Nivel de Protagonismo Bradesco`: Classificação para Bradesco
- `Nivel de Protagonismo Itaú`: Classificação para Itaú  
- `Nivel de Protagonismo Santander`: Classificação para Santander

### Classificações de Protagonismo

- **Dedicada**: Notícia focada na marca
- **Conteúdo**: Marca mencionada no conteúdo principal
- **Citação**: Marca apenas citada

## 🐳 Uso com Docker

### Comandos Básicos

```bash
# Construir e executar
docker-compose up --build

# Executar em background
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar serviços
docker-compose down
```

### Volumes Mapeados

- `./dados:/app/dados`: Dados processados
- `./config:/app/config`: Arquivos de configuração
- `./logs:/app/logs`: Logs do sistema
- `./downloads:/app/downloads`: Arquivos para download

## 📝 Logs

O sistema gera logs detalhados em:
- Console (durante execução)
- Arquivo `logs/app.log`

### Níveis de Log

- **INFO**: Informações gerais de processamento
- **WARNING**: Avisos sobre situações não críticas
- **ERROR**: Erros que impedem o funcionamento

## 🔧 Desenvolvimento

### Estrutura Modular

O sistema é dividido em módulos independentes:

- `ConfigManager`: Centraliza todas as configurações
- `APICaller`: Gerencia chamadas para APIs externas
- `ProtagonismoAnalyzer`: Análise com DeepSeek AI
- `DataConsolidator`: Consolidação e limpeza de dados
- `BatchProcessor`: Processamento final e geração de relatórios

### Adicionando Novas Funcionalidades

1. Crie novos módulos na pasta `src/`
2. Importe e use no `main.py`
3. Adicione configurações no `ConfigManager`
4. Atualize logs e tratamento de erros

## 🔒 Segurança

- **API Keys**: Nunca commitadas no código
- **Variáveis de Ambiente**: Uso de .env para configurações sensíveis
- **Logs**: Não registram informações sensíveis
- **Docker**: Isolamento em container

## 📋 Requisitos do Sistema

### Python
- Python 3.8+
- Dependências listadas em `requirements.txt`

### Docker
- Docker 20.10+
- Docker Compose 2.0+

### APIs
- Chave válida da DeepSeek API
- Acesso às APIs de notícias configuradas

## 🐛 Solução de Problemas

### Erros Comuns

**Erro: Chave da API não encontrada**
```
ValueError: Chave da API DeepSeek não encontrada
```
**Solução**: Configure a variável `DEEPSEEK_API_KEY` no arquivo .env

**Erro: Arquivo de configuração não encontrado**
```
FileNotFoundError: Arquivo de configuração não encontrado
```
**Solução**: Coloque os arquivos necessários na pasta `config/`

**Erro: Permissões no Docker**
```
Permission denied
```
**Solução**: Execute com `sudo docker-compose up` ou configure permissões do Docker

### Debug

Para debug mais detalhado, altere o nível de log:

```python
# Em main.py, na função setup_logging()
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.

## 📞 Suporte

Para dúvidas ou problemas:

1. Consulte a seção de Solução de Problemas
2. Verifique os logs do sistema
3. Abra uma issue no GitHub
4. Entre em contato com a equipe de desenvolvimento

---

**Versão**: 1.0.0  
**Última Atualização**: Janeiro 2025