"""
Simplified browser selector using only browser types
"""

import random
from typing import Optional

# Browser type market share
BROWSER_TYPES = [
    "chrome",  # ~65% market share
    "safari",  # ~20% market share
    "firefox",  # ~10% market share
    "edge",  # ~5% market share
]

# Browser list distributed by weight
WEIGHTED_BROWSERS = ["chrome"] * 65 + ["safari"] * 20 + ["firefox"] * 10 + ["edge"] * 5


def get_random_browser() -> str:
    """
    Get random browser type

    Returns:
        Browser type string
    """
    return random.choice(WEIGHTED_BROWSERS)


def get_browser(browser_type: Optional[str] = None) -> str:
    """
    Get browser type

    Args:
        browser_type: Specified browser type, if None then randomly select

    Returns:
        Browser type string
    """
    if browser_type and browser_type in BROWSER_TYPES:
        return browser_type
    return get_random_browser()


# Export simplified browser list
AVAILABLE_BROWSERS = BROWSER_TYPES


if __name__ == "__main__":
    # Test code

    # Test random selection
    for _i in range(10):
        browser = get_random_browser()

    for _browser_type in BROWSER_TYPES:
        pass
