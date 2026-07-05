import re
from collections.abc import Iterable

from prism_compiler.schemas import EntityDetection


class RegexDetector:
    entity_type: str
    pattern: re.Pattern[str]

    def detect(self, text: str) -> Iterable[EntityDetection]:
        for match in self.pattern.finditer(text):
            yield EntityDetection(
                text=match.group(0),
                entity_type=self.entity_type,
                start=match.start(),
                end=match.end(),
                confidence=1.0,
            )


class EmailDetector(RegexDetector):
    entity_type = "email"
    pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


class PhoneDetector(RegexDetector):
    entity_type = "phone"
    pattern = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")


class InvoiceDetector(RegexDetector):
    entity_type = "invoice"
    pattern = re.compile(r"\bINV-\d+\b", re.IGNORECASE)


class SimpleNameDetector(RegexDetector):
    entity_type = "person"
    pattern = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")
