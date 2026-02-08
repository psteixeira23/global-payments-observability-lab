from __future__ import annotations

from dataclasses import dataclass

from shared.contracts.enums import ErrorCategory


@dataclass
class ProcessorError(Exception):
    category: ErrorCategory
    message: str


class ProviderTimeoutError(ProcessorError):
    def __init__(self, message: str = "Provider timeout") -> None:
        super().__init__(ErrorCategory.PROVIDER_TIMEOUT, message)


class Provider5xxError(ProcessorError):
    def __init__(self, message: str = "Provider 5xx") -> None:
        super().__init__(ErrorCategory.PROVIDER_5XX, message)
