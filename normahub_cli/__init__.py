"""
NormaHub CLI - Universal Local AI Gateway, Engine & Model Arena.
Connect 30 AI models to any IDE, bot, or pipeline in Russia without VPN.
"""

from .cache import LocalCacheManager
from .models_data import MODELS_CATALOG
from .patcher import IDEPatcher
from .router import ParetoRouter
from .server import NormaHubGatewayServer

__version__ = "1.0.0"
__all__ = [
    "NormaHubGatewayServer",
    "LocalCacheManager",
    "ParetoRouter",
    "IDEPatcher",
    "MODELS_CATALOG",
]
