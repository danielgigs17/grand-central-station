"""Platform adapter factory and registry."""
from typing import Type, Dict, Optional
from app.adapters.base import PlatformAdapter
from app.adapters.grindr import GrindrAdapter
from app.adapters.alibaba import AlibabaAdapter, AlibabaBrowserAdapter
from app.adapters.alibaba_real import AlibabaRealAdapter, AlibabaRealBrowserAdapter
from app.adapters.alibaba_production import AlibabaProductionAdapter
from app.models.platform import PlatformAccount


# Registry of available adapters
ADAPTER_REGISTRY: Dict[str, Type[PlatformAdapter]] = {
    "grindr": GrindrAdapter,
    "alibaba": AlibabaProductionAdapter,  # Use the production implementation
    "alibaba_real": AlibabaRealAdapter,  # Keep real implementation
    "sniffies": None,  # Placeholder for future implementation
}

# Browser-based fallback adapters
BROWSER_ADAPTER_REGISTRY: Dict[str, Type[PlatformAdapter]] = {
    "alibaba": AlibabaProductionAdapter,  # Use the production browser implementation
    "alibaba_real": AlibabaRealBrowserAdapter,  # Keep real browser implementation
    # Add other browser adapters as needed
}


def get_adapter(
    platform_name: str, 
    account: PlatformAccount, 
    use_browser: bool = False
) -> PlatformAdapter:
    """
    Factory function to get the appropriate adapter for a platform.
    
    Args:
        platform_name: Name of the platform (e.g., 'grindr', 'alibaba')
        account: PlatformAccount instance with credentials
        use_browser: Whether to use browser-based adapter (if available)
        
    Returns:
        Instantiated adapter for the platform
        
    Raises:
        ValueError: If no adapter is found for the platform
    """
    # Check for browser adapter first if requested
    if use_browser:
        adapter_class = BROWSER_ADAPTER_REGISTRY.get(platform_name)
        if adapter_class:
            return adapter_class(account)
    
    # Fall back to regular adapter
    adapter_class = ADAPTER_REGISTRY.get(platform_name)
    if not adapter_class:
        raise ValueError(f"No adapter found for platform: {platform_name}")
    
    return adapter_class(account)


def get_available_platforms() -> list[str]:
    """Get list of platforms with available adapters."""
    return [name for name, adapter in ADAPTER_REGISTRY.items() if adapter is not None]


def is_browser_adapter_available(platform_name: str) -> bool:
    """Check if a browser-based adapter is available for the platform."""
    return platform_name in BROWSER_ADAPTER_REGISTRY and BROWSER_ADAPTER_REGISTRY[platform_name] is not None