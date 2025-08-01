# Data Models Reference

All data models in Dexscreen are Pydantic models, providing automatic validation and type safety.

> **🔍 Quick Find**: Use Ctrl+F to search for specific models or fields. All models are fully documented with examples.

## Core Models

### TokenPair

The primary data model representing a trading pair. This is what you'll work with most often.

**Returned by**: Most query and streaming methods, contains all essential trading data.

```python
class TokenPair(BaseModel):
    chain_id: str                      # Blockchain identifier
    dex_id: str                        # DEX identifier
    url: str                           # DEXScreener URL
    pair_address: str                  # Pair contract address
    base_token: BaseToken              # Base token info
    quote_token: BaseToken             # Quote token info
    price_native: float                # Price in native token
    price_usd: Optional[float]         # Price in USD
    transactions: PairTransactionCounts # Transaction statistics
    volume: VolumeChangePeriods        # Volume data
    price_change: PriceChangePeriods   # Price changes
    liquidity: Optional[Liquidity]     # Liquidity info
    fdv: Optional[float]               # Fully diluted valuation
    pair_created_at: Optional[datetime] # Creation timestamp
```

**Complete Usage Example:**

```python
pair = client.get_pair_by_pair_address("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")
if pair:
    # Basic information
    print(f"Pair: {pair.base_token.symbol}/{pair.quote_token.symbol}")
    print(f"DEX: {pair.dex_id}")
    print(f"Chain: {pair.chain_id.upper()}")

    # Price and market data
    print(f"Price: ${pair.price_usd:,.6f}")
    print(f"24h Volume: ${pair.volume.h24:,.0f}")
    print(f"24h Change: {pair.price_change.h24:+.2f}%")

    # Liquidity information
    if pair.liquidity:
        print(f"Total Liquidity: ${pair.liquidity.usd:,.0f}")
        print(f"Base Liquidity: {pair.liquidity.base:,.2f} {pair.base_token.symbol}")
        print(f"Quote Liquidity: {pair.liquidity.quote:,.2f} {pair.quote_token.symbol}")

    # Trading activity
    print(f"24h Transactions: {pair.transactions.h24.buys + pair.transactions.h24.sells}")
    print(f"Buy/Sell Ratio: {pair.transactions.h24.buys}/{pair.transactions.h24.sells}")
```

### BaseToken

Represents token information within a trading pair.

```python
class BaseToken(BaseModel):
    address: str    # Contract address (checksummed)
    name: str       # Full token name
    symbol: str     # Token symbol/ticker
```

**Practical Usage Examples:**

```python
# Example 1: Identify tokens in a pair
if pair.base_token.symbol == "USDC":
    trading_token = pair.quote_token
    print(f"USDC/{trading_token.symbol} pair")
else:
    trading_token = pair.base_token
    print(f"{trading_token.symbol}/USDC pair")

# Example 2: Check if it's a stablecoin pair
stablecoins = {"USDC", "USDT", "DAI", "BUSD", "FRAX"}
base_is_stable = pair.base_token.symbol in stablecoins
quote_is_stable = pair.quote_token.symbol in stablecoins

if base_is_stable and quote_is_stable:
    print("Stablecoin pair - low volatility expected")
elif base_is_stable or quote_is_stable:
    print("Token-stablecoin pair - good for price tracking")
else:
    print("Token-token pair - higher volatility expected")

# Example 3: Get token addresses for external APIs
print(f"Base token address: {pair.base_token.address}")
print(f"Quote token address: {pair.quote_token.address}")
```

## Transaction Statistics

### TransactionCount

Buy and sell transaction counts.

```python
class TransactionCount(BaseModel):
    buys: int      # Number of buy transactions
    sells: int     # Number of sell transactions
```

### PairTransactionCounts

Transaction statistics across different time periods.

```python
class PairTransactionCounts(BaseModel):
    m5: TransactionCount    # 5 minutes
    h1: TransactionCount    # 1 hour
    h6: TransactionCount    # 6 hours
    h24: TransactionCount   # 24 hours
```

**Advanced Usage Examples:**

```python
# Example 1: Calculate buy/sell pressure
def calculate_buy_pressure(transactions: TransactionCount) -> float:
    total = transactions.buys + transactions.sells
    return transactions.buys / total if total > 0 else 0.5

# Analyze different time periods
print("Buy Pressure Analysis:")
print(f"  5min: {calculate_buy_pressure(pair.transactions.m5):.1%}")
print(f"  1hour: {calculate_buy_pressure(pair.transactions.h1):.1%}")
print(f"  24hour: {calculate_buy_pressure(pair.transactions.h24):.1%}")

# Example 2: Detect unusual activity
recent_activity = pair.transactions.m5.buys + pair.transactions.m5.sells
hourly_avg = (pair.transactions.h1.buys + pair.transactions.h1.sells) / 12  # Per 5min

if hourly_avg > 0 and recent_activity > hourly_avg * 3:
    print("🚨 High activity alert: 3x normal transaction volume")

# Example 3: Trading pattern analysis
def analyze_trading_pattern(transactions: PairTransactionCounts):
    patterns = []

    # Check if buying is dominant
    if calculate_buy_pressure(transactions.h24) > 0.6:
        patterns.append("Strong buying pressure")
    elif calculate_buy_pressure(transactions.h24) < 0.4:
        patterns.append("Strong selling pressure")

    # Check activity level
    total_24h = transactions.h24.buys + transactions.h24.sells
    if total_24h > 1000:
        patterns.append("High activity")
    elif total_24h < 50:
        patterns.append("Low activity")

    return patterns

patterns = analyze_trading_pattern(pair.transactions)
print(f"Trading patterns: {', '.join(patterns)}")
```

## Market Data

### VolumeChangePeriods

Trading volume in USD across time periods.

```python
class VolumeChangePeriods(BaseModel):
    m5: Optional[float] = 0.0    # 5 minute volume
    h1: Optional[float] = 0.0    # 1 hour volume
    h6: Optional[float] = 0.0    # 6 hour volume
    h24: Optional[float] = 0.0   # 24 hour volume
```

### PriceChangePeriods

Price change percentages across time periods.

```python
class PriceChangePeriods(BaseModel):
    m5: Optional[float] = 0.0    # 5 minute change %
    h1: Optional[float] = 0.0    # 1 hour change %
    h6: Optional[float] = 0.0    # 6 hour change %
    h24: Optional[float] = 0.0   # 24 hour change %
```

**Advanced Market Analysis Examples:**

```python
# Example 1: Trend detection with volume confirmation
def detect_trends(pair: TokenPair) -> str:
    price_change = pair.price_change.h1 or 0
    volume_24h = pair.volume.h24 or 0

    # Strong uptrend: >5% price increase with good volume
    if price_change > 5 and volume_24h > 100_000:
        return f"📈 Strong uptrend: {pair.base_token.symbol}"

    # Strong downtrend: >5% price decrease with good volume
    elif price_change < -5 and volume_24h > 100_000:
        return f"📉 Strong downtrend: {pair.base_token.symbol}"

    # Consolidation: low price change despite good volume
    elif abs(price_change) < 2 and volume_24h > 50_000:
        return f"🔄 Consolidating: {pair.base_token.symbol}"

    return "No clear trend"

print(detect_trends(pair))

# Example 2: Volume acceleration analysis
def analyze_volume_acceleration(pair: TokenPair) -> dict:
    h1_vol = pair.volume.h1 or 0
    h6_vol = pair.volume.h6 or 0
    h24_vol = pair.volume.h24 or 0

    # Calculate hourly averages
    h6_hourly_avg = h6_vol / 6
    h24_hourly_avg = h24_vol / 24

    analysis = {
        "current_vs_6h_avg": h1_vol / h6_hourly_avg if h6_hourly_avg > 0 else 0,
        "current_vs_24h_avg": h1_vol / h24_hourly_avg if h24_hourly_avg > 0 else 0,
        "volume_trend": "increasing" if h1_vol > h6_hourly_avg * 1.5 else "normal"
    }

    return analysis

vol_analysis = analyze_volume_acceleration(pair)
if vol_analysis["current_vs_6h_avg"] > 3:
    print(f"🔥 Volume surge: {vol_analysis['current_vs_6h_avg']:.1f}x normal")

# Example 3: Multi-timeframe price momentum
def calculate_momentum_score(pair: TokenPair) -> float:
    """Calculate momentum score (0-100)"""
    changes = [
        pair.price_change.m5 or 0,
        pair.price_change.h1 or 0,
        pair.price_change.h6 or 0,
        pair.price_change.h24 or 0
    ]

    # Weight recent changes more heavily
    weights = [4, 3, 2, 1]
    weighted_score = sum(change * weight for change, weight in zip(changes, weights))
    total_weight = sum(weights)

    # Normalize to 0-100 scale (assuming max reasonable change is 50%)
    score = max(0, min(100, 50 + weighted_score / total_weight))
    return score

momentum = calculate_momentum_score(pair)
print(f"Momentum Score: {momentum:.1f}/100")
```

### Liquidity

Liquidity information for the pair.

```python
class Liquidity(BaseModel):
    usd: Optional[float]    # Total liquidity in USD
    base: float             # Base token liquidity
    quote: float            # Quote token liquidity
```

**Advanced Liquidity Analysis Examples:**

```python
# Example 1: Liquidity quality assessment
def assess_liquidity_quality(pair: TokenPair) -> dict:
    if not pair.liquidity or not pair.liquidity.usd:
        return {"quality": "unknown", "risk": "high"}

    liquidity_usd = pair.liquidity.usd
    volume_24h = pair.volume.h24 or 0

    # Calculate volume-to-liquidity ratio
    vol_liq_ratio = volume_24h / liquidity_usd if liquidity_usd > 0 else 0

    assessment = {
        "liquidity_usd": liquidity_usd,
        "volume_liquidity_ratio": vol_liq_ratio,
        "daily_turnover": vol_liq_ratio,  # How many times liquidity turns over daily
    }

    # Quality assessment
    if liquidity_usd > 1_000_000:
        assessment["quality"] = "excellent"
        assessment["risk"] = "very_low"
    elif liquidity_usd > 100_000:
        assessment["quality"] = "good"
        assessment["risk"] = "low"
    elif liquidity_usd > 10_000:
        assessment["quality"] = "fair"
        assessment["risk"] = "medium"
    else:
        assessment["quality"] = "poor"
        assessment["risk"] = "high"

    # High turnover might indicate price manipulation
    if vol_liq_ratio > 10:
        assessment["warning"] = "High turnover - possible manipulation"

    return assessment

liq_analysis = assess_liquidity_quality(pair)
print(f"Liquidity Quality: {liq_analysis['quality']}")
print(f"Risk Level: {liq_analysis['risk']}")
print(f"Daily Turnover: {liq_analysis['daily_turnover']:.1f}x")

# Example 2: Price impact estimation
def estimate_price_impact(pair: TokenPair, trade_size_usd: float) -> float:
    """Rough estimate of price impact for a given trade size"""
    if not pair.liquidity or not pair.liquidity.usd:
        return float('inf')  # Unknown impact

    # Simple price impact model: impact = trade_size / liquidity
    # Real AMMs use more complex formulas, but this gives a rough estimate
    impact_percentage = (trade_size_usd / pair.liquidity.usd) * 100

    return min(impact_percentage, 100)  # Cap at 100%

# Test different trade sizes
trade_sizes = [1000, 5000, 10000, 50000]
print("\nEstimated Price Impact:")
for size in trade_sizes:
    impact = estimate_price_impact(pair, size)
    print(f"  ${size:,}: {impact:.2f}%")

# Example 3: Liquidity distribution analysis
def analyze_liquidity_distribution(pair: TokenPair):
    if not pair.liquidity:
        return "No liquidity data"

    base_value = pair.liquidity.base * (pair.price_usd or 0)
    quote_value = pair.liquidity.quote  # Assuming quote is USD or stablecoin
    total_value = base_value + quote_value

    if total_value > 0:
        base_percentage = (base_value / total_value) * 100
        quote_percentage = (quote_value / total_value) * 100

        return {
            "base_percentage": base_percentage,
            "quote_percentage": quote_percentage,
            "balance": "balanced" if 40 <= base_percentage <= 60 else "imbalanced"
        }

    return "Cannot analyze distribution"

distribution = analyze_liquidity_distribution(pair)
if isinstance(distribution, dict):
    print(f"\nLiquidity Distribution:")
    print(f"  {pair.base_token.symbol}: {distribution['base_percentage']:.1f}%")
    print(f"  {pair.quote_token.symbol}: {distribution['quote_percentage']:.1f}%")
    print(f"  Status: {distribution['balance']}")
```

## Token Information

### TokenInfo

Detailed token profile information.

```python
class TokenInfo(BaseModel):
    url: str                        # DEXScreener URL
    chain_id: str                   # Blockchain identifier
    token_address: str              # Token contract address
    amount: float = 0.0             # Boost amount
    total_amount: float = 0.0       # Total boost amount
    icon: Optional[str]             # Icon URL
    header: Optional[str]           # Header image URL
    description: Optional[str]      # Token description
    links: List[TokenLink] = []     # Related links
```

### TokenLink

Links associated with a token.

```python
class TokenLink(BaseModel):
    type: Optional[str]     # Link type (website, twitter, etc.)
    label: Optional[str]    # Display label
    url: Optional[str]      # Link URL
```

**Complete Token Analysis Example:**

```python
# Get and analyze token profiles
profiles = client.get_latest_token_profiles()

for token in profiles:
    print(f"\n{'='*50}")
    print(f"Token: {token.token_address}")
    print(f"Chain: {token.chain_id.upper()}")
    print(f"URL: {token.url}")

    # Boost information
    if token.amount > 0:
        print(f"Boost Amount: {token.amount}")
        print(f"Total Boost: {token.total_amount}")

    # Description analysis
    if token.description:
        desc = token.description[:200] + "..." if len(token.description) > 200 else token.description
        print(f"Description: {desc}")

        # Simple keyword analysis
        keywords = ["meme", "utility", "defi", "gaming", "nft", "dao"]
        found_keywords = [kw for kw in keywords if kw.lower() in token.description.lower()]
        if found_keywords:
            print(f"Categories: {', '.join(found_keywords)}")

    # Social links analysis
    social_links = {}
    for link in token.links:
        if link.type and link.url:
            social_links[link.type] = link.url

    if social_links:
        print("Social Links:")
        for platform, url in social_links.items():
            print(f"  {platform.title()}: {url}")

    # Media presence
    if token.icon:
        print(f"Has Icon: Yes")
    if token.header:
        print(f"Has Header Image: Yes")

    # Get trading data for this token
    try:
        pairs = client.get_pairs_by_token_address(token.chain_id, token.token_address)
        if pairs:
            total_volume = sum(p.volume.h24 for p in pairs if p.volume.h24)
            total_liquidity = sum(p.liquidity.usd for p in pairs if p.liquidity and p.liquidity.usd)
            print(f"Trading Pairs: {len(pairs)}")
            print(f"Total 24h Volume: ${total_volume:,.0f}")
            print(f"Total Liquidity: ${total_liquidity:,.0f}")
    except Exception as e:
        print(f"Could not fetch trading data: {e}")
```

### OrderInfo

Order/payment information for tokens.

```python
class OrderInfo(BaseModel):
    type: str               # Order type
    status: str             # Order status
    payment_timestamp: int  # Payment timestamp (milliseconds)
```

**Advanced Order Analysis Example:**

```python
from datetime import datetime, timedelta

orders = client.get_orders_paid_of_token("ethereum", token_address)

if orders:
    print(f"Found {len(orders)} paid orders for token")
    print("\nOrder Analysis:")

    # Group orders by type and status
    order_stats = {}
    recent_orders = []

    for order in orders:
        # Convert timestamp
        timestamp = datetime.fromtimestamp(order.payment_timestamp / 1000)

        # Track statistics
        key = f"{order.type}_{order.status}"
        order_stats[key] = order_stats.get(key, 0) + 1

        # Check if order is recent (last 7 days)
        if timestamp > datetime.now() - timedelta(days=7):
            recent_orders.append((order, timestamp))

        print(f"  {order.type.title()} order: {order.status} at {timestamp.strftime('%Y-%m-%d %H:%M')}")

    # Summary statistics
    print("\nOrder Statistics:")
    for order_type, count in order_stats.items():
        print(f"  {order_type.replace('_', ' ').title()}: {count}")

    # Recent activity
    if recent_orders:
        print(f"\nRecent Activity (last 7 days): {len(recent_orders)} orders")
        for order, timestamp in recent_orders[-3:]:  # Show last 3
            print(f"  {timestamp.strftime('%m/%d')}: {order.type} ({order.status})")
    else:
        print("\nNo recent order activity")
else:
    print("No paid orders found for this token")
```

## Working with Optional Fields

Many fields are optional and may be None. Always use defensive programming:

```python
# Pattern 1: Simple None checks
if pair.price_usd:
    print(f"Price: ${pair.price_usd:,.6f}")
else:
    print("USD price not available")

# Pattern 2: Default values with or operator
volume_24h = pair.volume.h24 or 0
liquidity_usd = pair.liquidity.usd if pair.liquidity else 0
fdv = pair.fdv or 0

# Pattern 3: Safe chaining with nested checks
if pair.liquidity and pair.liquidity.usd and pair.liquidity.usd > 100_000:
    print("High liquidity pair")

# Pattern 4: Helper function for safe access
def safe_get(obj, *attrs, default=None):
    """Safely access nested attributes"""
    try:
        for attr in attrs:
            obj = getattr(obj, attr)
            if obj is None:
                return default
        return obj
    except AttributeError:
        return default

# Usage examples
liquidity_usd = safe_get(pair, 'liquidity', 'usd', default=0)
volume_h1 = safe_get(pair, 'volume', 'h1', default=0)
buys_5m = safe_get(pair, 'transactions', 'm5', 'buys', default=0)

print(f"Safely accessed values:")
print(f"  Liquidity: ${liquidity_usd:,.0f}")
print(f"  1h Volume: ${volume_h1:,.0f}")
print(f"  5min Buys: {buys_5m}")

# Pattern 5: Comprehensive data validation
def validate_pair_data(pair: TokenPair) -> dict:
    """Validate and score data completeness"""
    validation = {
        "has_price": bool(pair.price_usd),
        "has_volume": bool(pair.volume.h24),
        "has_liquidity": bool(pair.liquidity and pair.liquidity.usd),
        "has_price_changes": bool(pair.price_change.h24 is not None),
        "has_transactions": bool(pair.transactions.h24.buys + pair.transactions.h24.sells > 0),
        "has_fdv": bool(pair.fdv),
        "creation_date": bool(pair.pair_created_at)
    }

    # Calculate completeness score
    score = sum(validation.values()) / len(validation) * 100
    validation["completeness_score"] = score

    # Quality assessment
    if score >= 80:
        validation["quality"] = "excellent"
    elif score >= 60:
        validation["quality"] = "good"
    elif score >= 40:
        validation["quality"] = "fair"
    else:
        validation["quality"] = "poor"

    return validation

# Validate pair data
validation = validate_pair_data(pair)
print(f"\nData Quality Assessment:")
print(f"  Completeness: {validation['completeness_score']:.1f}%")
print(f"  Quality: {validation['quality']}")
print(f"  Missing data: {[k for k, v in validation.items() if isinstance(v, bool) and not v]}")
```

## Type Hints and IDE Support

All models have full type hints for excellent IDE support:

```python
from dexscreen import TokenPair, DexscreenerClient

def analyze_pair(pair: TokenPair) -> dict:
    """Analyze a trading pair"""
    return {
        "symbol": pair.base_token.symbol,
        "price": pair.price_usd,
        "volume_24h": pair.volume.h24,
        "liquidity": pair.liquidity.usd if pair.liquidity else 0,
        "buy_pressure": calculate_buy_pressure(pair.transactions)
    }

def calculate_buy_pressure(txns: PairTransactionCounts) -> float:
    """Calculate buy pressure from transactions"""
    total = txns.h24.buys + txns.h24.sells
    return txns.h24.buys / total if total > 0 else 0.5
```

## Model Validation & Error Handling

Pydantic provides automatic validation with detailed error messages:

```python
from pydantic import ValidationError
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Example 1: Basic validation error handling
try:
    # This would fail validation
    token = BaseToken(
        address="invalid_address",  # Should be a valid address format
        name="",                    # Should not be empty
        symbol=""                   # Should not be empty
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
    # Log specific field errors
    for error in e.errors():
        print(f"Field '{error['loc'][0]}': {error['msg']}")

# Example 2: Robust API response handling
def safely_parse_pair_data(raw_data: dict) -> TokenPair | None:
    """Safely parse raw API data into TokenPair model"""
    try:
        return TokenPair.model_validate(raw_data)
    except ValidationError as e:
        logger.warning(f"Failed to parse pair data: {e}")

        # Log specific issues for debugging
        for error in e.errors():
            field_path = ' -> '.join(str(loc) for loc in error['loc'])
            logger.debug(f"Invalid field {field_path}: {error['msg']}")

        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing pair data: {e}")
        return None

# Example 3: Data quality validation
def validate_trading_data_quality(pair: TokenPair) -> list[str]:
    """Validate trading data quality and return warnings"""
    warnings = []

    # Check for suspicious data
    if pair.price_usd and pair.price_usd <= 0:
        warnings.append("Invalid price: price is zero or negative")

    if pair.volume.h24 and pair.volume.h24 < 0:
        warnings.append("Invalid volume: negative 24h volume")

    if pair.liquidity and pair.liquidity.usd and pair.liquidity.usd < 1000:
        warnings.append("Low liquidity warning: less than $1,000")

    # Check for data consistency
    total_tx = pair.transactions.h24.buys + pair.transactions.h24.sells
    if total_tx == 0 and pair.volume.h24 and pair.volume.h24 > 0:
        warnings.append("Data inconsistency: volume without transactions")

    # Check for extreme values
    if pair.price_change.h24 and abs(pair.price_change.h24) > 1000:
        warnings.append(f"Extreme price change: {pair.price_change.h24:.1f}%")

    return warnings

# Usage example
warnings = validate_trading_data_quality(pair)
if warnings:
    print("Data Quality Warnings:")
    for warning in warnings:
        print(f"  ⚠️ {warning}")
else:
    print("✅ Data quality looks good")

# Example 4: Custom validation for trading strategies
def is_suitable_for_trading(pair: TokenPair, min_liquidity: float = 50000, min_volume: float = 10000) -> dict:
    """Check if pair is suitable for trading based on criteria"""
    result = {
        "suitable": True,
        "reasons": [],
        "score": 0
    }

    # Check liquidity
    if not pair.liquidity or not pair.liquidity.usd or pair.liquidity.usd < min_liquidity:
        result["suitable"] = False
        result["reasons"].append(f"Insufficient liquidity (need ${min_liquidity:,})")
    else:
        result["score"] += 25

    # Check volume
    volume_24h = pair.volume.h24 or 0
    if volume_24h < min_volume:
        result["suitable"] = False
        result["reasons"].append(f"Low volume (need ${min_volume:,})")
    else:
        result["score"] += 25

    # Check price availability
    if not pair.price_usd:
        result["suitable"] = False
        result["reasons"].append("No USD price available")
    else:
        result["score"] += 25

    # Check trading activity
    total_tx = pair.transactions.h24.buys + pair.transactions.h24.sells
    if total_tx < 10:
        result["suitable"] = False
        result["reasons"].append("Insufficient trading activity")
    else:
        result["score"] += 25

    return result

# Test trading suitability
suitability = is_suitable_for_trading(pair)
print(f"\nTrading Suitability:")
print(f"  Suitable: {'✅ Yes' if suitability['suitable'] else '❌ No'}")
print(f"  Score: {suitability['score']}/100")
if suitability["reasons"]:
    print(f"  Issues: {', '.join(suitability['reasons'])}")
```

## JSON Serialization & Data Export

All models support flexible serialization for storage and analysis:

```python
import json
from datetime import datetime

# Basic serialization
pair_dict = pair.model_dump()
pair_json = pair.model_dump_json()

# Clean serialization (exclude None values)
clean_dict = pair.model_dump(exclude_none=True)

# Custom serialization with datetime handling
def serialize_pair_for_analysis(pair: TokenPair) -> dict:
    """Serialize pair data optimized for analysis"""
    data = pair.model_dump(exclude_none=True)

    # Add computed fields
    data['computed'] = {
        'total_transactions_24h': pair.transactions.h24.buys + pair.transactions.h24.sells,
        'buy_sell_ratio': pair.transactions.h24.buys / max(pair.transactions.h24.sells, 1),
        'volume_to_liquidity_ratio': (pair.volume.h24 or 0) / (pair.liquidity.usd if pair.liquidity else 1),
        'last_updated': datetime.now().isoformat()
    }

    return data

# Export to different formats
analysis_data = serialize_pair_for_analysis(pair)

# Save to JSON file
with open(f"pair_data_{pair.base_token.symbol}_{pair.quote_token.symbol}.json", "w") as f:
    json.dump(analysis_data, f, indent=2)

# Save to CSV (flattened)
import pandas as pd

def flatten_dict(d, parent_key='', sep='_'):
    """Flatten nested dictionary for CSV export"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

flat_data = flatten_dict(analysis_data)
df = pd.DataFrame([flat_data])
df.to_csv(f"pair_data_{pair.base_token.symbol}_{pair.quote_token.symbol}.csv", index=False)

print(f"Data exported to JSON and CSV files")
print(f"JSON size: {len(json.dumps(analysis_data))} characters")
print(f"CSV columns: {len(flat_data)} fields")
```
