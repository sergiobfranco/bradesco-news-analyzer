#!/usr/bin/env python3
"""
Script de setup e instalação do Sistema de Análise de Notícias
"""

import os
import sys
import shutil
from pathlib import Path

def create_project_structure():
    """Cria a estrutura de diretórios do projeto"""
    print("Criando estrutura de diretórios...")
    
    directories = [
        "dados/api",
        "dados/marca_setor",
        "config",
        "logs",
        "downloads",
        "src/utils"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✓ Diretório criado: {dir_path}")

def create_init_files():
    """Cria arquivos __init__.py necessários"""
    print("\nCriando arquivos de inicialização...")
    
    init_files = [
        "src/__init__.py",
        "src/utils/__init__.py"
    ]
    
    for init_file in init_files:
        Path(init_file).touch()
        print(f"✓ Arquivo criado: {init_file}")

def copy_config_examples():
    """Copia arquivos de exemplo de configuração"""
    print("\nConfigurando arquivos de exemplo...")
    
    # Cria arquivo .env se não existir
    env_file = Path(".env")
    if not env_file.exists():
        shutil.copy(".env.example", ".env")
        print("✓ Arquivo .env criado a partir do exemplo")
        print("  ATENÇÃO: Configure sua DEEPSEEK_API_KEY no arquivo .env")
    else:
        print("✓ Arquivo .env já existe")

def check_python_version():
    """Verifica se a versão do Python é adequada"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ é necessário")
        sys.exit(1)
    else:
        print(f"✓ Python {sys.version} detectado")

def install_requirements():
    """Instala as dependências"""
    print("\nInstalando dependências...")
    os.system("pip install -r requirements.txt")
    print("✓ Dependências instaladas")

def main():
    print("=" * 60)
    print("SETUP - Sistema de Análise de Notícias Bradesco")
    print("=" * 60)
    
    check_python_version()
    create_project_structure()
    create_init_files()
    copy_config_examples()
    install_requirements()
    
    print("\n" + "=" * 60)
    print("SETUP CONCLUÍDO!")
    print("=" * 60)
    print("\nPróximos passos:")
    print("1. Configure sua DEEPSEEK_API_KEY no arquivo .env")
    print("2. Coloque o arquivo nivel_protagonismo_claude_bradesco.xlsx na pasta config/")
    print("3. Coloque o arquivo api_marca_configs.json na pasta config/")
    print("4. Execute: python main.py")
    print("\nPara usar Docker:")
    print("1. docker-compose up --build")
    print("\nPara desenvolvimento:")
    print("1. python main.py")

if __name__ == "__main__":
    main()