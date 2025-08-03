"""
Input validation utilities for Dexscreen API
"""

import re
from typing import Any, Callable, Optional, Union
from urllib.parse import urlparse

from .exceptions import (
    EmptyListError,
    InvalidAddressError,
    InvalidCallbackError,
    InvalidChainIdError,
    InvalidFilterError,
    InvalidIntervalError,
    InvalidParameterError,
    InvalidRangeError,
    InvalidTypeError,
    InvalidUrlError,
    TooManyItemsError,
)

# Common blockchain networks supported by Dexscreener
VALID_CHAIN_IDS = {
    "ethereum",
    "bsc",
    "polygon",
    "avalanche",
    "fantom",
    "cronos",
    "arbitrum",
    "optimism",
    "solana",
    "base",
    "linea",
    "scroll",
    "blast",
    "manta",
    "mantle",
    "mode",
    "sei",
    "pulsechain",
    "metis",
    "moonbeam",
    "moonriver",
    "celo",
    "fuse",
    "harmony",
    "kava",
    "evmos",
    "milkomeda",
    "aurora",
    "near",
    "telos",
    "wax",
    "eos",
    "tron",
    "aptos",
    "sui",
    "starknet",
    "zksync",
    "polygonzkevm",
    "immutablex",
    "loopring",
    "dydx",
    "osmosis",
    "cosmos",
    "terra",
    "thorchain",
    "bitcoin",
    "litecoin",
    "dogecoin",
    "cardano",
    "polkadot",
    "kusama",
    "algorand",
    "tezos",
    "flow",
    "hedera",
    "icp",
    "waves",
    "stellar",
    "xrp",
    "chia",
    "elrond",
    "zilliqa",
    "vechain",
    "nuls",
    "nem",
    "symbol",
    "iotex",
    "ontology",
    "qtum",
    "conflux",
    "nervos",
    "syscoin",
    "digibyte",
    "ravencoin",
    "zcash",
    "dash",
    "monero",
    "decred",
    "horizen",
    "beam",
    "grin",
}

# Address format patterns for different blockchains
ADDRESS_PATTERNS = {
    # Ethereum-style (hex, 40 chars + 0x prefix)
    "ethereum": re.compile(r"^0x[a-fA-F0-9]{40}$"),
    "bsc": re.compile(r"^0x[a-fA-F0-9]{40}$"),
    "polygon": re.compile(r"^0x[a-fA-F0-9]{40}$"),
    "arbitrum": re.compile(r"^0x[a-fA-F0-9]{40}$"),
    "optimism": re.compile(r"^0x[a-fA-F0-9]{40}$"),
    "avalanche": re.compile(r"^0x[a-fA-F0-9]{40}$"),
    "fantom": re.compile(r"^0x[a-fA-F0-9]{40}$"),
    "base": re.compile(r"^0x[a-fA-F0-9]{40}$"),
    # Solana (base58, 32-44 chars)
    "solana": re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$"),
    # Bitcoin (base58, starts with 1, 3, or bc1)
    "bitcoin": re.compile(r"^(1[1-9A-HJ-NP-Za-km-z]{25,34}|3[1-9A-HJ-NP-Za-km-z]{25,34}|bc1[a-z0-9]{39,59})$"),
    # Generic fallback (alphanumeric, 20-65 chars)
    "default": re.compile(r"^[a-zA-Z0-9]{20,65}$"),
}


def validate_string(
    value: Any, parameter_name: str, min_length: int = 1, max_length: int = 1000, allow_empty: bool = False
) -> str:
    """
    Validate string parameter.

    Args:
        value: Value to validate
        parameter_name: Name of parameter for error messages
        min_length: Minimum string length
        max_length: Maximum string length
        allow_empty: Whether to allow empty strings

    Returns:
        Validated string

    Raises:
        InvalidTypeError: If value is not a string
        InvalidParameterError: If string is empty when not allowed or outside length bounds
    """
    if not isinstance(value, str):
        raise InvalidTypeError(parameter_name, value, "string")

    if not allow_empty and len(value) == 0:
        raise InvalidParameterError(parameter_name, value, "non-empty string")

    if not (min_length <= len(value) <= max_length):
        raise InvalidRangeError(parameter_name, len(value), min_length, max_length)

    return value


def validate_chain_id(chain_id: Any) -> str:
    """
    Validate blockchain chain ID.

    Args:
        chain_id: Chain ID to validate

    Returns:
        Validated chain ID (lowercase)

    Raises:
        InvalidChainIdError: If chain ID is invalid
    """
    if not isinstance(chain_id, str):
        raise InvalidTypeError("chain_id", chain_id, "string")

    chain_id = chain_id.lower().strip()

    if not chain_id:
        raise InvalidParameterError("chain_id", chain_id, "non-empty string")

    if chain_id not in VALID_CHAIN_IDS:
        # Get similar chain IDs for better error message
        similar = [c for c in VALID_CHAIN_IDS if chain_id in c or c in chain_id][:5]
        raise InvalidChainIdError(chain_id, similar if similar else list(VALID_CHAIN_IDS)[:10])

    return chain_id


def validate_address(address: Any, chain_id: Optional[str] = None) -> str:
    """
    Validate blockchain address format.

    Args:
        address: Address to validate
        chain_id: Optional chain ID for chain-specific validation

    Returns:
        Validated address

    Raises:
        InvalidAddressError: If address format is invalid
    """
    if not isinstance(address, str):
        raise InvalidTypeError("address", address, "string")

    address = address.strip()

    if not address:
        raise InvalidAddressError(address, "Address cannot be empty")

    # Basic length check
    if len(address) < 20 or len(address) > 70:
        raise InvalidAddressError(address, "Address length must be between 20 and 70 characters")

    # Chain-specific validation
    if chain_id:
        pattern = ADDRESS_PATTERNS.get(chain_id.lower(), ADDRESS_PATTERNS["default"])
        if not pattern.match(address):
            raise InvalidAddressError(address, f"Invalid address format for {chain_id}")

    return address


def validate_addresses_list(
    addresses: Any,
    parameter_name: str = "addresses",
    min_count: int = 1,
    max_count: int = 30,
    chain_id: Optional[str] = None,
) -> list[str]:
    """
    Validate list of addresses.

    Args:
        addresses: List of addresses to validate
        parameter_name: Name of parameter for error messages
        min_count: Minimum number of addresses
        max_count: Maximum number of addresses
        chain_id: Optional chain ID for address validation

    Returns:
        Validated list of addresses

    Raises:
        InvalidTypeError: If not a list
        EmptyListError: If list is empty when not allowed
        TooManyItemsError: If too many addresses
        InvalidAddressError: If any address is invalid
    """
    if not isinstance(addresses, (list, tuple)):
        raise InvalidTypeError(parameter_name, addresses, "list")

    addresses = list(addresses)

    if len(addresses) < min_count:
        if min_count == 1:
            raise EmptyListError(parameter_name)
        else:
            raise InvalidParameterError(parameter_name, addresses, f"at least {min_count} items")

    if len(addresses) > max_count:
        raise TooManyItemsError(parameter_name, len(addresses), max_count)

    # Validate each address
    validated_addresses = []
    for i, addr in enumerate(addresses):
        try:
            validated_addr = validate_address(addr, chain_id)
            validated_addresses.append(validated_addr)
        except InvalidAddressError as e:
            raise InvalidAddressError(addr, f"Address at index {i}: {e.reason}") from e

    # Check for duplicates
    if len(set(validated_addresses)) != len(validated_addresses):
        raise InvalidParameterError(parameter_name, addresses, "unique addresses (duplicates found)")

    return validated_addresses


def validate_numeric(
    value: Any,
    parameter_name: str,
    expected_type: type = float,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    allow_none: bool = False,
) -> Union[int, float, None]:
    """
    Validate numeric parameter.

    Args:
        value: Value to validate
        parameter_name: Name of parameter for error messages
        expected_type: Expected numeric type (int or float)
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        allow_none: Whether to allow None values

    Returns:
        Validated numeric value

    Raises:
        InvalidTypeError: If value is not numeric
        InvalidRangeError: If value is outside valid range
    """
    if value is None and allow_none:
        return None

    if not isinstance(value, (int, float)):
        raise InvalidTypeError(parameter_name, value, expected_type.__name__)

    # Convert to expected type
    try:
        if expected_type is int:
            value = int(value)
        elif expected_type is float:
            value = float(value)
    except (ValueError, OverflowError) as e:
        raise InvalidTypeError(parameter_name, value, expected_type.__name__) from e

    # Check for special float values
    if expected_type is float and (value != value or value == float("inf") or value == float("-inf")):
        raise InvalidParameterError(parameter_name, value, "finite number")

    # Range validation
    if min_value is not None and value < min_value:
        raise InvalidRangeError(parameter_name, value, min_value, max_value)

    if max_value is not None and value > max_value:
        raise InvalidRangeError(parameter_name, value, min_value, max_value)

    return value


def validate_interval(interval: Any, min_interval: float = 0.1, max_interval: float = 3600.0) -> float:
    """
    Validate polling interval.

    Args:
        interval: Interval to validate
        min_interval: Minimum allowed interval
        max_interval: Maximum allowed interval

    Returns:
        Validated interval

    Raises:
        InvalidIntervalError: If interval is invalid
    """
    try:
        interval = validate_numeric(interval, "interval", float, min_interval, max_interval)
    except (InvalidTypeError, InvalidRangeError) as e:
        raise InvalidIntervalError(interval, min_interval, max_interval) from e

    return interval


def validate_callback(callback: Any) -> Callable:
    """
    Validate callback function.

    Args:
        callback: Callback to validate

    Returns:
        Validated callback

    Raises:
        InvalidCallbackError: If callback is invalid
    """
    if not callable(callback):
        raise InvalidCallbackError(callback, "Must be callable")

    return callback


def validate_url(url: Any, require_https: bool = False) -> str:
    """
    Validate URL format.

    Args:
        url: URL to validate
        require_https: Whether to require HTTPS scheme

    Returns:
        Validated URL

    Raises:
        InvalidUrlError: If URL is invalid
    """
    if not isinstance(url, str):
        raise InvalidTypeError("url", url, "string")

    url = url.strip()

    if not url:
        raise InvalidUrlError(url, "URL cannot be empty")

    try:
        parsed = urlparse(url)

        if not parsed.scheme:
            raise InvalidUrlError(url, "URL must include scheme (http/https)")

        if require_https and parsed.scheme != "https":
            raise InvalidUrlError(url, "URL must use HTTPS")

        if not parsed.netloc:
            raise InvalidUrlError(url, "URL must include domain")

    except Exception as e:
        raise InvalidUrlError(url, "Invalid URL format") from e

    return url


def validate_filter_config(filter_config: Any) -> Any:
    """
    Validate filter configuration.

    Args:
        filter_config: Filter config to validate

    Returns:
        Validated filter config

    Raises:
        InvalidFilterError: If filter config is invalid
    """
    from ..utils.filters import FilterConfig

    if filter_config is None:
        return None

    if isinstance(filter_config, bool):
        return filter_config

    if not isinstance(filter_config, FilterConfig):
        raise InvalidFilterError(f"Must be bool or FilterConfig, got {type(filter_config).__name__}")

    # Validate filter config fields
    if hasattr(filter_config, "price_change_threshold") and filter_config.price_change_threshold is not None:
        validate_numeric(filter_config.price_change_threshold, "price_change_threshold", float, 0.0, 1.0)

    if hasattr(filter_config, "volume_change_threshold") and filter_config.volume_change_threshold is not None:
        validate_numeric(filter_config.volume_change_threshold, "volume_change_threshold", float, 0.0, 10.0)

    if hasattr(filter_config, "max_updates_per_second") and filter_config.max_updates_per_second is not None:
        validate_numeric(filter_config.max_updates_per_second, "max_updates_per_second", float, 0.01, 100.0)

    return filter_config


def validate_query_string(query: Any, max_length: int = 200) -> str:
    """
    Validate search query string.

    Args:
        query: Query to validate
        max_length: Maximum query length

    Returns:
        Validated query

    Raises:
        InvalidParameterError: If query is invalid
    """
    query = validate_string(query, "query", 1, max_length)

    # Remove potentially dangerous characters
    if any(char in query for char in ["<", ">", '"', "'"]):
        raise InvalidParameterError("query", query, "query without HTML/script characters")

    return query.strip()


def validate_dict_config(config: Any, parameter_name: str = "config", allow_none: bool = True) -> Optional[dict]:
    """
    Validate dictionary configuration.

    Args:
        config: Config dict to validate
        parameter_name: Name of parameter for error messages
        allow_none: Whether to allow None values

    Returns:
        Validated config dict

    Raises:
        InvalidTypeError: If config is not dict or None
    """
    if config is None and allow_none:
        return None

    if not isinstance(config, dict):
        raise InvalidTypeError(parameter_name, config, "dict")

    return config


def validate_boolean(value: Any, parameter_name: str) -> bool:
    """
    Validate boolean parameter.

    Args:
        value: Value to validate
        parameter_name: Name of parameter for error messages

    Returns:
        Validated boolean

    Raises:
        InvalidTypeError: If value is not boolean
    """
    if not isinstance(value, bool):
        raise InvalidTypeError(parameter_name, value, "bool")

    return value


def validate_list_not_empty(value: Any, parameter_name: str) -> list:
    """
    Validate that list is not empty.

    Args:
        value: List to validate
        parameter_name: Name of parameter for error messages

    Returns:
        Validated list

    Raises:
        InvalidTypeError: If value is not a list
        EmptyListError: If list is empty
    """
    if not isinstance(value, (list, tuple)):
        raise InvalidTypeError(parameter_name, value, "list")

    if len(value) == 0:
        raise EmptyListError(parameter_name)

    return list(value)
