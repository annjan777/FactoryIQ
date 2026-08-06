import re
from typing import Any, Set

class HallucinationGate:
    @staticmethod
    def _extract_numbers_from_text(text: str) -> Set[float]:
        """
        Finds all numbers (integers and decimals) in the given text block.
        e.g., 'Order SO-1024 has 180 units ready.' -> {1024.0, 180.0}
        """
        # Matches integers and decimal floats. Handles negative numbers or signs.
        pattern = re.compile(r'-?\b\d+(?:\.\d+)?\b')
        matches = pattern.findall(text)
        numbers = set()
        for m in matches:
            try:
                numbers.add(float(m))
            except ValueError:
                continue
        return numbers

    @staticmethod
    def _extract_numbers_from_source(data: Any) -> Set[float]:
        """
        Recursively extracts all numeric values (int, float) from a dictionary or list.
        """
        numbers = set()
        if isinstance(data, dict):
            for v in data.values():
                numbers.update(HallucinationGate._extract_numbers_from_source(v))
        elif isinstance(data, list):
            for item in data:
                numbers.update(HallucinationGate._extract_numbers_from_source(item))
        elif isinstance(data, (int, float)):
            numbers.add(float(data))
        elif isinstance(data, str):
            # Attempt parsing string-encoded values e.g., "180.0" or "SO-1024"
            pattern = re.compile(r'-?\b\d+(?:\.\d+)?\b')
            matches = pattern.findall(data)
            for m in matches:
                try:
                    numbers.add(float(m))
                except ValueError:
                    continue
        return numbers

    @classmethod
    def verify_grounding(cls, generated_text: str, source_data: dict) -> bool:
        """
        Validates that every number referenced by the SLM is present
        in the structural backend facts payload.
        """
        text_numbers = cls._extract_numbers_from_text(generated_text)
        source_numbers = cls._extract_numbers_from_source(source_data)
        
        # Check if text numbers are a subset of source numbers
        for num in text_numbers:
            # Tolerant match to check float conversions (e.g. 180 matches 180.0)
            if num not in source_numbers:
                # Let's verify if there is an approximate or formatting match
                # e.g., a year segment like 2026, or ID strings.
                return False
        return True
