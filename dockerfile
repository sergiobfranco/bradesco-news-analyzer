# Use Python 3.11 slim como base
FROM python:3.11-slim

# Define diretório de trabalho
WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copia arquivo de requisitos
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia código fonte
COPY . .

# Cria diretórios necessários
RUN mkdir -p dados/api dados/marca_setor config logs downloads

# Define variáveis de ambiente
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expõe porta (se for necessário para interface web futura)
EXPOSE 8000

# Comando padrão
CMD ["python", "main.py"]