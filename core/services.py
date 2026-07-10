import logging
from typing import Any, Dict, Type, TypeVar

from core.errors import ServiceInitializationError

logger = logging.getLogger("crisispilot.services")

T = TypeVar("T")


class ServiceRegistry:
    """
    Lightweight Dependency Injection Container and Service Registry.
    Ensures centralized management and lifecycle handling of core services.
    """
    _services: Dict[Type[Any], Any] = {}
    _initialized = False

    @classmethod
    def register(cls, interface: Type[T], implementation: T) -> None:
        """Registers a service instance."""
        if interface in cls._services:
            logger.warning(f"Service {interface.__name__} is already registered. Overwriting.")
        cls._services[interface] = implementation
        logger.debug(f"Registered service: {interface.__name__}")

    @classmethod
    def get(cls, interface: Type[T]) -> T:
        """Retrieves a registered service instance."""
        if interface not in cls._services:
            raise ServiceInitializationError(f"Service {interface.__name__} not found in registry.")
        return cls._services[interface]

    @classmethod
    def get_health(cls) -> Dict[str, str]:
        """Returns the health status of all registered services."""
        return {
            interface.__name__: "operational" 
            for interface in cls._services.keys()
        }
        
    @classmethod
    def clear(cls) -> None:
        """Clears the registry (useful for testing or shutdown)."""
        cls._services.clear()
        cls._initialized = False


# Global registry instance pattern
registry = ServiceRegistry()
