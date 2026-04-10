"""
Input Validator for NeetResearch App.

Provides input validation and sanitization for:
- Research topics
- File paths
- API parameters
"""

import re
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of validation check."""
    is_valid: bool
    cleaned_value: str
    errors: List[str]
    warnings: List[str]


class InputValidator:
    """
    Validates and sanitizes user input.
    """
    
    # Dangerous patterns to reject
    DANGEROUS_PATTERNS = [
        re.compile(r'<script', re.IGNORECASE),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),  # onclick, onerror, etc.
        re.compile(r'data:', re.IGNORECASE),
    ]
    
    # Maximum lengths
    MAX_TOPIC_LENGTH = 1000
    MAX_FILENAME_LENGTH = 255
    MIN_TOPIC_LENGTH = 3
    
    # Allowed characters for filenames
    SAFE_FILENAME_PATTERN = re.compile(r'^[\w\s\-_.]+$')
    
    def validate_research_topic(self, topic: str) -> ValidationResult:
        """
        Validate and sanitize a research topic.
        
        Args:
            topic: User's research topic
            
        Returns:
            ValidationResult with cleaned topic
        """
        errors = []
        warnings = []
        
        if not topic or not topic.strip():
            return ValidationResult(
                is_valid=False,
                cleaned_value="",
                errors=["Research topic cannot be empty"],
                warnings=[]
            )
        
        # Clean whitespace
        cleaned = topic.strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Check length
        if len(cleaned) < self.MIN_TOPIC_LENGTH:
            errors.append(f"Topic must be at least {self.MIN_TOPIC_LENGTH} characters")
        
        if len(cleaned) > self.MAX_TOPIC_LENGTH:
            warnings.append(f"Topic truncated from {len(cleaned)} to {self.MAX_TOPIC_LENGTH} chars")
            cleaned = cleaned[:self.MAX_TOPIC_LENGTH]
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.search(cleaned):
                errors.append("Topic contains potentially dangerous content")
                cleaned = pattern.sub('', cleaned)
        
        # Remove any remaining HTML-like tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # Warn about special characters
        special_chars = set(re.findall(r'[^\w\s.,?!\'"-]', cleaned))
        if special_chars:
            warnings.append(f"Topic contains special characters: {special_chars}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            cleaned_value=cleaned,
            errors=errors,
            warnings=warnings
        )
    
    def validate_filename(self, filename: str) -> ValidationResult:
        """
        Validate and sanitize a filename.
        
        Args:
            filename: Proposed filename
            
        Returns:
            ValidationResult with safe filename
        """
        errors = []
        warnings = []
        
        if not filename or not filename.strip():
            return ValidationResult(
                is_valid=False,
                cleaned_value="output",
                errors=["Filename cannot be empty"],
                warnings=[]
            )
        
        # Clean whitespace
        cleaned = filename.strip()
        
        # Remove path separators
        cleaned = re.sub(r'[/\\]', '_', cleaned)
        
        # Remove dangerous characters
        cleaned = re.sub(r'[<>:"|?*]', '', cleaned)
        
        # Prevent directory traversal
        cleaned = cleaned.replace('..', '')
        
        # Check length
        if len(cleaned) > self.MAX_FILENAME_LENGTH:
            warnings.append(f"Filename truncated to {self.MAX_FILENAME_LENGTH} chars")
            cleaned = cleaned[:self.MAX_FILENAME_LENGTH]
        
        # Ensure we have something left
        if not cleaned:
            cleaned = "output"
            errors.append("Invalid filename, using 'output' as default")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            cleaned_value=cleaned,
            errors=errors,
            warnings=warnings
        )
    
    def validate_url(self, url: str) -> ValidationResult:
        """
        Validate a URL.
        
        Args:
            url: URL to validate
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        
        if not url or not url.strip():
            return ValidationResult(
                is_valid=False,
                cleaned_value="",
                errors=["URL cannot be empty"],
                warnings=[]
            )
        
        cleaned = url.strip()
        
        # Check for valid URL format
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        
        if not url_pattern.match(cleaned):
            # Try adding https://
            if not cleaned.startswith(('http://', 'https://')):
                cleaned = 'https://' + cleaned
                warnings.append("Added https:// prefix")
                
                if not url_pattern.match(cleaned):
                    errors.append("Invalid URL format")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            cleaned_value=cleaned,
            errors=errors,
            warnings=warnings
        )
    
    def sanitize_for_prompt(self, text: str) -> str:
        """
        Sanitize text for use in LLM prompts.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Remove potential prompt injection attempts
        cleaned = text
        
        # Remove markdown code blocks that might hide instructions
        cleaned = re.sub(r'```[\s\S]*?```', '[code block removed]', cleaned)
        
        # Remove potential system/instruction tokens
        cleaned = re.sub(r'\[INST\]|\[/INST\]|\[SYSTEM\]', '', cleaned, flags=re.IGNORECASE)
        
        # Limit length
        max_len = 50000
        if len(cleaned) > max_len:
            cleaned = cleaned[:max_len] + "... [truncated]"
        
        return cleaned


# Convenience functions
_validator: Optional[InputValidator] = None


def get_validator() -> InputValidator:
    """Get the global validator instance."""
    global _validator
    if _validator is None:
        _validator = InputValidator()
    return _validator


def validate_topic(topic: str) -> Tuple[bool, str, List[str]]:
    """
    Convenience function to validate a research topic.
    
    Args:
        topic: Research topic
        
    Returns:
        Tuple of (is_valid, cleaned_topic, errors)
    """
    validator = get_validator()
    result = validator.validate_research_topic(topic)
    return result.is_valid, result.cleaned_value, result.errors


def sanitize_text(text: str) -> str:
    """
    Convenience function to sanitize text.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text
    """
    validator = get_validator()
    return validator.sanitize_for_prompt(text)
