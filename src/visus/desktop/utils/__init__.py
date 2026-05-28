"""
Visus Desktop - Utilities

This module contains utilities for Visus Desktop.
"""

from .config import BotVisionConfig, create_config_from_file, get_default_config
from .retry import retry
from .text_filters import (
    clean_text,
    extract_letters_from_text,
    extract_numbers_from_text,
    limpar_texto,
    matches_filter,
    validate_text_input,
)

__all__ = [
    # Text filters
    "clean_text",
    "limpar_texto",
    "matches_filter",
    "validate_text_input",
    "extract_numbers_from_text",
    "extract_letters_from_text",
    # Config
    "BotVisionConfig",
    "create_config_from_file",
    "get_default_config",
    # Reliability helpers
    "retry",
]
