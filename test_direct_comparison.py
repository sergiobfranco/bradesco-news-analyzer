#!/usr/bin/env python3
"""
Teste Direto - Comparação entre implementações DeepSeek
Executa ambas as implementações com dados idênticos para identificar diferença
"""

import requests
import json
import sys
from pathlib import Path

# Setup imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from src.config_manager import ConfigManager
    from src.protagonismo_analyzer import ProtagonismoAnalyzer
except ImportError:
    import importlib.util
    
    # Carregar config_manager
    config_path = Path(__file__).parent / "config_manager.py"
    spec = importlib.util.spec_from_file_location("config_manager", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    ConfigManager = config_module.ConfigManager
    
    # Carregar protagonismo_analyzer
    prot_path = Path(__file__).parent / "protagonismo_analyzer.py"
    spec = importlib.util.spec_from_file_location("protagonismo_analyzer", prot_path)
    prot_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prot_module)
    ProtagonismoAnalyzer = prot_module.ProtagonismoAnalyzer

def test_protagonismo_analyzer():
    """Testa implementação do protagonismo_analyzer que funciona"""
    print("🔍 TESTE 1: ProtagonismoAnalyzer (FUNCIONA)")
    print("-" * 50)
    
    try:
        config = ConfigManager()
        analyzer = ProtagonismoAnalyzer(config)
        
        # Dados de teste
        titulo = "Bradesco anuncia novos produtos"
        conteudo = "O Bradesco lançou hoje uma nova linha de produtos financeiros."
        texto_completo = f"Título: {titulo}\nConteúdo: {conteudo}"
        
        print(f"📋 URL: {config.api_url}")
        print(f"📋 Headers: {analyzer.headers}")
        print()
        
        # Simular chamada do protagonismo_analyzer (método _call_deepseek_api)
        prompt = f"""
Analise o texto abaixo e responda SOMENTE com: "Nível 1", "Nível 2", "Nível 3" ou "Nenhum Nível Encontrado".

Texto da Notícia:
{texto_completo}
        """
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system", 
                    "content": "Você é um analista especializado em classificar o nível de protagonismo de marcas em notícias."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        
        print(f"📋 Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        print()
        
        print("🚀 Fazendo chamada...")
        response = requests.post(config.api_url, headers=analyzer.headers, json=payload)
        
        print(f"📊 Status: {response.status_code}")
        print(f"📊 Headers da resposta: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ Resposta: {content}")
            return True
        else:
            print(f"❌ Erro: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na implementação: {e}")
        return False

def test_brand_extractor_style():
    """Testa implementação estilo brand_extractor"""
    print("\n🔍 TESTE 2: Brand Extractor Style")
    print("-" * 40)
    
    try:
        config = ConfigManager()
        headers = config.get_api_headers()
        
        # Mesmos dados de teste
        titulo = "Bradesco anuncia novos produtos"
        conteudo = "O Bradesco lançou hoje uma nova linha de produtos financeiros."
        texto_completo = f"Título: {titulo}\nConteúdo: {conteudo}"
        
        print(f"📋 URL: {config.api_url}")
        print(f"📋 Headers: {headers}")
        print()
        
        prompt = f"""
Analise o texto a seguir e identifique TODAS as marcas/empresas mencionadas.

FORMATO DE RESPOSTA:
Responda APENAS com uma lista JSON de strings, sem explicações:
["Marca1", "Marca2", "Marca3"]

TEXTO:
{texto_completo}
"""
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system", 
                    "content": "Você é um analista especializado em identificar marcas/empresas mencionadas em textos."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        
        print(f"📋 Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        print()
        
        print("🚀 Fazendo chamada...")
        response = requests.post(config.api_url, headers=headers, json=payload)
        
        print(f"📊 Status: {response.status_code}")
        print(f"📊 Headers da resposta: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ Resposta: {content}")
            return True
        else:
            print(f"❌ Erro: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na implementação: {e}")
        return False

def compare_configurations():
    """Compara configurações detalhadamente"""
    print("\n🔍 TESTE 3: Comparação Detalhada de Configurações")
    print("-" * 55)
    
    try:
        config = ConfigManager()
        analyzer = ProtagonismoAnalyzer(config)
        
        print("📋 CONFIGURAÇÕES COMPARTILHADAS:")
        print(f"   API URL: {config.api_url}")
        print(f"   API Key (10 primeiros): {config.api_key[:10]}...")
        print()
        
        print("📋 HEADERS CONFIG_MANAGER:")
        config_headers = config.get_api_headers()
        for key, value in config_headers.items():
            if 'Authorization' in key:
                print(f"   {key}: Bearer {value[7:17]}...")
            else:
                print(f"   {key}: {value}")
        print()
        
        print("📋 HEADERS PROTAGONISMO_ANALYZER:")
        for key, value in analyzer.headers.items():
            if 'Authorization' in key:
                print(f"   {key}: Bearer {value[7:17]}...")
            else:
                print(f"   {key}: {value}")
        print()
        
        print("📋 COMPARAÇÃO:")
        if config_headers == analyzer.headers:
            print("   ✅ Headers são IDÊNTICOS")
        else:
            print("   ❌ Headers são DIFERENTES!")
            for key in set(list(config_headers.keys()) + list(analyzer.headers.keys())):
                config_val = config_headers.get(key, "AUSENTE")
                analyzer_val = analyzer.headers.get(key, "AUSENTE")
                if config_val != analyzer_val:
                    print(f"   DIFERENÇA em '{key}':")
                    print(f"     ConfigManager: {config_val}")
                    print(f"     ProtagonismoAnalyzer: {analyzer_val}")
                    
    except Exception as e:
        print(f"❌ Erro na comparação: {e}")

def test_raw_request():
    """Teste com request mais básico possível"""
    print("\n🔍 TESTE 4: Request Raw Básico")
    print("-" * 35)
    
    try:
        config = ConfigManager()
        
        # Request mais simples possível
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "Oi"}],
            "max_tokens": 10
        }
        
        print(f"📋 Headers básicos: {headers}")
        print(f"📋 Payload básico: {payload}")
        print()
        
        print("🚀 Fazendo chamada básica...")
        response = requests.post("https://api.deepseek.com/v1/chat/completions", 
                               headers=headers, json=payload)
        
        print(f"📊 Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Request básico funcionou!")
        else:
            print(f"❌ Request básico falhou: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro no request básico: {e}")

def main():
    print("🔧 TESTE DIRETO - COMPARAÇÃO DE IMPLEMENTAÇÕES DEEPSEEK")
    print("=" * 60)
    
    # Teste 1: ProtagonismoAnalyzer (que funciona)
    prot_works = test_protagonismo_analyzer()
    
    # Teste 2: Style Brand Extractor
    brand_works = test_brand_extractor_style()
    
    # Teste 3: Comparar configurações
    compare_configurations()
    
    # Teste 4: Request básico
    test_raw_request()
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    print(f"ProtagonismoAnalyzer funciona: {'✅ SIM' if prot_works else '❌ NÃO'}")
    print(f"Brand Extractor style funciona: {'✅ SIM' if brand_works else '❌ NÃO'}")
    
    if prot_works and not brand_works:
        print("\n💡 CONCLUSÃO: Problema específico no brand_extractor")
        print("   - ProtagonismoAnalyzer funciona")
        print("   - Brand Extractor não funciona")
        print("   - Precisa identificar diferença sutil")
        
    elif not prot_works and not brand_works:
        print("\n💡 CONCLUSÃO: Problema geral com DeepSeek")
        print("   - Nenhuma implementação funciona")
        print("   - Problema pode ser com chave ou configuração")
        
    else:
        print("\n💡 CONCLUSÃO: Ambos funcionam ou problema intermitente")

if __name__ == "__main__":
    main()