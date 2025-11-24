#!/usr/bin/env python3
"""
Diagnóstico da Configuração DeepSeek API
Script para verificar se a chave da API está configurada corretamente
"""

import os
import sys
from pathlib import Path
import requests

def check_env_file():
    """Verifica arquivo .env"""
    print("🔍 VERIFICANDO ARQUIVO .env")
    print("-" * 30)
    
    env_file = Path('.env')
    if env_file.exists():
        print("✅ Arquivo .env encontrado")
        
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'DEEPSEEK_API_KEY' in content:
                print("✅ DEEPSEEK_API_KEY encontrada no .env")
                
                # Extrair a chave
                for line in content.split('\n'):
                    if line.strip().startswith('DEEPSEEK_API_KEY='):
                        key = line.split('=', 1)[1].strip()
                        if key and key != 'sua_chave_aqui':
                            print(f"✅ Chave configurada: {key[:10]}...{key[-4:]}")
                            return key
                        else:
                            print("❌ Chave não configurada ou é exemplo")
                            return None
            else:
                print("❌ DEEPSEEK_API_KEY não encontrada no .env")
                return None
                
        except Exception as e:
            print(f"❌ Erro ao ler .env: {e}")
            return None
    else:
        print("❌ Arquivo .env não encontrado")
        return None

def check_env_variable():
    """Verifica variável de ambiente"""
    print("\n🔍 VERIFICANDO VARIÁVEL DE AMBIENTE")
    print("-" * 35)
    
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if api_key:
        print(f"✅ Variável de ambiente definida: {api_key[:10]}...{api_key[-4:]}")
        return api_key
    else:
        print("❌ Variável de ambiente DEEPSEEK_API_KEY não definida")
        return None

def test_api_key(api_key):
    """Testa a chave da API"""
    print("\n🔍 TESTANDO CHAVE DA API")
    print("-" * 25)
    
    if not api_key:
        print("❌ Nenhuma chave para testar")
        return False
    
    try:
        print("🚀 Fazendo chamada de teste...")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "Teste"}],
            "max_tokens": 10
        }
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ API funcionando corretamente!")
            return True
        elif response.status_code == 401:
            print("❌ Erro 401 - Chave inválida ou expirada")
            return False
        else:
            print(f"❌ Erro {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

def show_setup_instructions():
    """Mostra instruções de configuração"""
    print("\n📋 INSTRUÇÕES DE CONFIGURAÇÃO")
    print("=" * 35)
    print()
    
    print("1. 🌐 OBTER CHAVE DA API:")
    print("   - Acesse: https://platform.deepseek.com/")
    print("   - Faça login ou crie uma conta")
    print("   - Vá em 'API Keys'")
    print("   - Clique em 'Create API Key'")
    print("   - Copie a chave (começa com 'sk-')")
    print()
    
    print("2. ⚙️ CONFIGURAR NO PROJETO:")
    print("   Método A - Arquivo .env (RECOMENDADO):")
    print("   - Crie arquivo .env na raiz do projeto")
    print("   - Adicione: DEEPSEEK_API_KEY=sk-sua_chave_aqui")
    print()
    print("   Método B - Variável de ambiente:")
    print("   - Windows PowerShell: $env:DEEPSEEK_API_KEY='sk-sua_chave_aqui'")
    print("   - Windows CMD: set DEEPSEEK_API_KEY=sk-sua_chave_aqui")
    print("   - Linux/Mac: export DEEPSEEK_API_KEY=sk-sua_chave_aqui")
    print()
    
    print("3. 🔄 CRIAR ARQUIVO .env:")
    env_content = """# Configurações da API DeepSeek
DEEPSEEK_API_KEY=sk-sua_chave_aqui_substitua_esta_linha

# Exemplo de chave válida (NÃO use esta):
# DEEPSEEK_API_KEY=sk-1234567890abcdef1234567890abcdef
"""
    
    print("   Conteúdo do arquivo .env:")
    print(env_content)
    
    print("4. ✅ VERIFICAR:")
    print("   - Execute este script novamente")
    print("   - Ou execute: python brand_extractor_fixed.py")

def create_sample_env():
    """Cria arquivo .env de exemplo"""
    env_file = Path('.env')
    
    if not env_file.exists():
        try:
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write("# Configurações da API DeepSeek\n")
                f.write("DEEPSEEK_API_KEY=sk-sua_chave_aqui_substitua_esta_linha\n")
                f.write("\n")
                f.write("# Exemplo de chave válida (NÃO use esta):\n")
                f.write("# DEEPSEEK_API_KEY=sk-1234567890abcdef1234567890abcdef\n")
            
            print(f"✅ Arquivo .env criado em: {env_file.absolute()}")
            print("📝 IMPORTANTE: Edite o arquivo e substitua 'sk-sua_chave_aqui' pela sua chave real!")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar .env: {e}")
            return False
    else:
        print("ℹ️ Arquivo .env já existe")
        return True

def main():
    """Função principal de diagnóstico"""
    
    print("🔐 DIAGNÓSTICO DA API DEEPSEEK")
    print("=" * 40)
    print()
    
    # Verificar arquivo .env
    env_key = check_env_file()
    
    # Verificar variável de ambiente
    var_key = check_env_variable()
    
    # Usar a chave encontrada (prioridade para variável de ambiente)
    api_key = var_key or env_key
    
    # Testar API
    api_working = test_api_key(api_key) if api_key else False
    
    print("\n" + "=" * 40)
    print("📊 RESUMO DO DIAGNÓSTICO")
    print("=" * 40)
    
    if api_working:
        print("✅ CONFIGURAÇÃO OK!")
        print("   Sua chave DeepSeek está funcionando corretamente")
        print("   Você pode executar o brand_extractor sem problemas")
        
    else:
        print("❌ CONFIGURAÇÃO COM PROBLEMAS")
        
        if not api_key:
            print("   Chave da API não encontrada")
            print("   SOLUÇÃO: Configure a chave conforme instruções abaixo")
            
            # Perguntar se quer criar .env
            try:
                create = input("\n🤔 Quer que eu crie um arquivo .env para você? (s/n): ").lower()
                if create in ['s', 'sim', 'y', 'yes']:
                    create_sample_env()
            except KeyboardInterrupt:
                print("\n\nOperação cancelada pelo usuário")
        else:
            print("   Chave encontrada mas não está funcionando")
            print("   SOLUÇÃO: Verifique se a chave está correta e não expirou")
        
        show_setup_instructions()

if __name__ == "__main__":
    main()