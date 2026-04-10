"""
Utilities package for NeetResearch App.

Provides:
- Citation extraction and formatting
- Metadata extraction from web pages
- Input validation and sanitization
- Logging configuration
- Caching layer
"""

from .citation_extractor import (
    Citation,
    CitationExtractor,
    extract_citations,
    format_bibliography,
)

from .metadata_extractor import (
    PageMetadata,
    MetadataExtractor,
    extract_metadata,
)

from .input_validator import (
    InputValidator,
    ValidationResult,
    validate_topic,
    sanitize_text,
    get_validator,
)

from .logger import (
    setup_logging,
    get_logger,
    ResearchLogger,
    get_research_logger,
)

from .cache import (
    SimpleCache,
    LLMCache,
    SearchCache,
    get_llm_cache,
    get_search_cache,
    cached_llm_call,
)

__all__ = [
    # Citations
    "Citation",
    "CitationExtractor",
    "extract_citations",
    "format_bibliography",
    # Metadata
    "PageMetadata",
    "MetadataExtractor",
    "extract_metadata",
    # Input Validation
    "InputValidator",
    "ValidationResult",
    "validate_topic",
    "sanitize_text",
    "get_validator",
    # Logging
    "setup_logging",
    "get_logger",
    "ResearchLogger",
    "get_research_logger",
    # Caching
    "SimpleCache",
    "LLMCache",
    "SearchCache",
    "get_llm_cache",
    "get_search_cache",
    "cached_llm_call",
]
