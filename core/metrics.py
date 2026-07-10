import abc
from typing import Any, Dict


class MetricsProvider(abc.ABC):
    """
    Abstract interface for providers that expose runtime or in-memory metrics.
    Allows the Analytics layer to collect metrics without coupling to specific implementations.
    """

    @abc.abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """Returns a dictionary of relevant metrics."""
        pass
