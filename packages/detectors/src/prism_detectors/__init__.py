"""Entity detector package."""

from prism_detectors.patterns import (
    EmailDetector,
    InvoiceDetector,
    PhoneDetector,
    SimpleNameDetector,
)

__all__ = ["EmailDetector", "InvoiceDetector", "PhoneDetector", "SimpleNameDetector"]
