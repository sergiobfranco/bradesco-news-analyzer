"""
Configurações de mapeamento de canais para marcas
Permite manutenção centralizada dos mapeamentos sem alterar código
"""

# Mapeamento de termos nos canais para marcas específicas
CHANNEL_BRAND_MAPPING = {
    "Bradesco": [
        "Asset",
        "Atacado / Banco de Investimento", 
        "Corretora/Ágora",
        "Economia",
        "ESG",
        "Inovação/TI",
        "Institucional/Negócios",
        "MKT",
        "Bradesco"  # Inclui o próprio nome da marca
    ],
    "Itaú": [
        "Itaú",
        # Futuramente podem ser adicionados outros termos para Itaú
    ],
    "Santander": [
        "Santander",
        # Futuramente podem ser adicionados outros termos para Santander
    ]
}

# Mapeamento de termos específicos que devem ser verificados no conteúdo
# Estrutura: canal -> termo_a_buscar_no_conteudo
SPECIFIC_CONTENT_VERIFICATION = {
    "Asset": "Bradesco Asset",
    "Corretora/Ágora": "Ágora"
}

def get_brand_terms(brand_name: str) -> list:
    """
    Retorna os termos associados a uma marca específica
    
    Args:
        brand_name: Nome da marca (ex: "Bradesco")
        
    Returns:
        Lista de termos que identificam a marca nos canais
    """
    return CHANNEL_BRAND_MAPPING.get(brand_name, [brand_name])

def get_all_mappings() -> dict:
    """
    Retorna todos os mapeamentos configurados
    
    Returns:
        Dicionário completo com mapeamentos marca -> termos
    """
    return CHANNEL_BRAND_MAPPING.copy()

def get_specific_content_terms() -> dict:
    """
    Retorna os mapeamentos de verificação específica de conteúdo
    
    Returns:
        Dicionário com canal -> termo_a_buscar
    """
    return SPECIFIC_CONTENT_VERIFICATION.copy()

def check_specific_content_requirements(channel_content: str, news_content: str) -> dict:
    """
    Verifica se há termos específicos que devem ser procurados no conteúdo
    baseado nos canais presentes
    
    Args:
        channel_content: Conteúdo do campo Canais
        news_content: Conteúdo completo da notícia (título + corpo)
        
    Returns:
        Dict com informações sobre termos específicos encontrados
    """
    import re
    
    results = {
        'found_specific_terms': [],
        'should_be_minimum_citation': False
    }
    
    # Verifica cada mapeamento específico
    for channel_term, content_term in SPECIFIC_CONTENT_VERIFICATION.items():
        # Se o canal contém o termo específico
        if re.search(r'\b' + re.escape(channel_term) + r'\b', channel_content, re.IGNORECASE):
            # Verifica se o termo correspondente está no conteúdo da notícia
            if re.search(r'\b' + re.escape(content_term) + r'\b', news_content, re.IGNORECASE):
                results['found_specific_terms'].append({
                    'channel_term': channel_term,
                    'content_term': content_term,
                    'found_in_content': True
                })
                results['should_be_minimum_citation'] = True
    
    return results

def normalize_channel_field(channel_content: str) -> str:
    """
    Normaliza o campo Canais substituindo termos específicos pelas marcas correspondentes
    
    Args:
        channel_content: Conteúdo original do campo Canais
        
    Returns:
        Campo Canais normalizado com marcas substituídas
    """
    import re
    
    # Copia o conteúdo original
    normalized_content = str(channel_content)
    
    # Para cada marca, verifica se algum dos seus termos está presente
    for brand_name, brand_terms in CHANNEL_BRAND_MAPPING.items():
        found_terms = []
        
        # Verifica quais termos desta marca estão presentes
        for term in brand_terms:
            # Busca case-insensitive por palavra completa
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, normalized_content, re.IGNORECASE):
                found_terms.append(term)
        
        # Se encontrou pelo menos um termo desta marca
        if found_terms:
            # Remove todos os termos encontrados
            for term in found_terms:
                pattern = r'\b' + re.escape(term) + r'\b'
                normalized_content = re.sub(pattern, '', normalized_content, flags=re.IGNORECASE)
            
            # Adiciona a marca uma única vez (se ainda não estiver presente)
            if not re.search(r'\b' + re.escape(brand_name) + r'\b', normalized_content, re.IGNORECASE):
                # Remove vírgulas duplicadas e espaços extras antes de adicionar
                normalized_content = re.sub(r',\s*,', ',', normalized_content)
                normalized_content = normalized_content.strip().strip(',').strip()
                
                # Adiciona a marca
                if normalized_content:
                    normalized_content = f"{normalized_content}, {brand_name}"
                else:
                    normalized_content = brand_name
    
    # Limpeza final: remove vírgulas duplicadas e espaços extras
    normalized_content = re.sub(r',\s*,+', ',', normalized_content)
    normalized_content = re.sub(r'\s+', ' ', normalized_content)
    normalized_content = normalized_content.strip().strip(',').strip()
    
    return normalized_content