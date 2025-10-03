"""
Módulo de configurações do sistema
Centraliza mapeamentos e configurações
"""

from .channel_mappings import (
    CHANNEL_BRAND_MAPPING,
    get_brand_terms,
    get_all_mappings,
    normalize_channel_field
)

__all__ = [
    'CHANNEL_BRAND_MAPPING',
    'get_brand_terms',
    'get_all_mappings', 
    'normalize_channel_field'
]