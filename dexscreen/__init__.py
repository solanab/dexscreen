"""
Dexscreen - Python SDK for DexScreener API

A modern, stable, and reliable Python SDK for DexScreener API with HTTP support.
"""

from .api.client import DexscreenerClient
from .core.models import (
    BaseToken,
    Liquidity,
    PairTransactionCounts,
    PriceChangePeriods,
    TokenPair,
    TransactionCount,
    VolumeChangePeriods,
)
from .utils.filters import FilterConfig, FilterPresets

__version__ = "1.0.0"
__all__ = [
    "BaseToken",
    "DexscreenerClient",
    "FilterConfig",
    "FilterPresets",
    "Liquidity",
    "PairTransactionCounts",
    "PriceChangePeriods",
    "TokenPair",
    "TransactionCount",
    "VolumeChangePeriods",
]
