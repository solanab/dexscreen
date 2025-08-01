import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Base configuration for all models
base_config = ConfigDict(
    # Standard Pydantic config
    populate_by_name=True,
)


class BaseToken(BaseModel):
    model_config = base_config

    address: str
    name: str
    symbol: str


class TransactionCount(BaseModel):
    model_config = base_config

    buys: int
    sells: int


class PairTransactionCounts(BaseModel):
    model_config = base_config

    m5: TransactionCount
    h1: TransactionCount
    h6: TransactionCount
    h24: TransactionCount


class _TimePeriodsFloat(BaseModel):
    model_config = base_config

    m5: Optional[float] = 0.0
    h1: Optional[float] = 0.0
    h6: Optional[float] = 0.0
    h24: Optional[float] = 0.0


class VolumeChangePeriods(_TimePeriodsFloat): ...


class PriceChangePeriods(_TimePeriodsFloat): ...


class Liquidity(BaseModel):
    model_config = base_config

    usd: Optional[float] = None
    base: float
    quote: float


class TokenPair(BaseModel):
    model_config = base_config

    chain_id: str = Field(..., alias="chainId")
    dex_id: str = Field(..., alias="dexId")
    url: str = Field(...)
    pair_address: str = Field(..., alias="pairAddress")
    base_token: BaseToken = Field(..., alias="baseToken")
    quote_token: BaseToken = Field(..., alias="quoteToken")
    price_native: float = Field(..., alias="priceNative")
    price_usd: Optional[float] = Field(None, alias="priceUsd")
    transactions: PairTransactionCounts = Field(..., alias="txns")
    volume: VolumeChangePeriods
    price_change: PriceChangePeriods = Field(..., alias="priceChange")
    liquidity: Optional[Liquidity] = None
    fdv: Optional[float] = 0.0
    pair_created_at: Optional[dt.datetime] = Field(None, alias="pairCreatedAt")


class TokenLink(BaseModel):
    model_config = base_config

    type: Optional[str] = None
    label: Optional[str] = None
    url: Optional[str] = None


class TokenInfo(BaseModel):
    model_config = base_config

    url: str
    chain_id: str = Field(..., alias="chainId")
    token_address: str = Field(..., alias="tokenAddress")
    amount: float = 0.0  # Not sure if this is the best logic
    total_amount: float = Field(0.0, alias="totalAmount")
    icon: Optional[str] = None
    header: Optional[str] = None
    description: Optional[str] = None
    links: list[TokenLink] = []


class OrderInfo(BaseModel):
    model_config = base_config

    type: str
    status: str
    payment_timestamp: int = Field(..., alias="paymentTimestamp")
