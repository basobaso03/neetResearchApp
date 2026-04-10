"""
Citation Extractor for NeetResearch App.

Extracts, validates, and formats citations from research content.
Supports multiple citation formats (Harvard, APA, MLA).
"""

import re
from typing import List, Dict, Optional, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse


@dataclass
class Citation:
    """Represents a single citation."""
    url: str
    title: str = ""
    author: str = ""
    date: str = ""
    source_type: str = "web"  # web, pdf, database
    accessed_date: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))
    domain: str = ""
    
    def __post_init__(self):
        if self.url and not self.domain:
            parsed = urlparse(self.url)
            self.domain = parsed.netloc


class CitationExtractor:
    """
    Extracts citations from research notes and content.
    """
    
    # Common URL patterns
    URL_PATTERN = re.compile(
        r'https?://(?:www\.)?'
        r'[-a-zA-Z0-9@:%._\+~#=]{1,256}'
        r'\.[a-zA-Z0-9()]{1,6}\b'
        r'(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
    )
    
    # Pattern for inline citations like (Author, 2024) or [1]
    INLINE_CITATION_PATTERN = re.compile(
        r'\(([A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s*\d{4})\)'  # (Smith, 2024)
        r'|\[(\d+)\]'  # [1]
    )
    
    def __init__(self):
        self.citations: List[Citation] = []
        self.seen_urls: set = set()
    
    def extract_from_text(self, text: str) -> List[Citation]:
        """
        Extract all citations from text.
        
        Args:
            text: Text to extract citations from
            
        Returns:
            List of Citation objects
        """
        citations = []
        
        # Find all URLs
        urls = self.URL_PATTERN.findall(text)
        for url in urls:
            if url not in self.seen_urls:
                self.seen_urls.add(url)
                citation = Citation(url=url)
                # Try to extract title from context
                title = self._extract_title_from_context(text, url)
                if title:
                    citation.title = title
                citations.append(citation)
        
        self.citations.extend(citations)
        return citations
    
    def _extract_title_from_context(self, text: str, url: str) -> str:
        """
        Try to extract a title from the text near a URL.
        
        Args:
            text: Source text
            url: URL to find context for
            
        Returns:
            Extracted title or empty string
        """
        # Look for patterns like "Title" - url or Title (url)
        escaped_url = re.escape(url)
        
        # Pattern: "Title" followed by URL
        pattern1 = re.compile(
            rf'["\']([^"\']+)["\'][\s\-:]+{escaped_url}',
            re.IGNORECASE
        )
        
        # Pattern: Title (URL)
        pattern2 = re.compile(
            rf'([A-Z][^.!?]*?)\s*[\(\[]?{escaped_url}',
            re.IGNORECASE
        )
        
        for pattern in [pattern1, pattern2]:
            match = pattern.search(text)
            if match:
                title = match.group(1).strip()
                if len(title) > 5 and len(title) < 200:
                    return title
        
        return ""
    
    def extract_from_notes(self, notes: List[str]) -> List[Citation]:
        """
        Extract citations from a list of research notes.
        
        Args:
            notes: List of note strings
            
        Returns:
            List of all unique citations
        """
        for note in notes:
            self.extract_from_text(note)
        return self.citations
    
    def get_unique_citations(self) -> List[Citation]:
        """Get deduplicated citations."""
        seen = set()
        unique = []
        for c in self.citations:
            if c.url not in seen:
                seen.add(c.url)
                unique.append(c)
        return unique
    
    def format_citation(
        self, 
        citation: Citation, 
        style: str = "harvard"
    ) -> str:
        """
        Format a citation in a specific style.
        
        Args:
            citation: Citation to format
            style: Citation style (harvard, apa, mla, url)
            
        Returns:
            Formatted citation string
        """
        if style.lower() == "url":
            return citation.url
        
        author = citation.author or citation.domain or "Unknown"
        title = citation.title or "Untitled"
        date = citation.date or "n.d."
        accessed = citation.accessed_date
        
        if style.lower() == "harvard":
            return f"{author} ({date}) '{title}'. Available at: {citation.url} (Accessed: {accessed})"
        
        elif style.lower() == "apa":
            return f"{author}. ({date}). {title}. Retrieved from {citation.url}"
        
        elif style.lower() == "mla":
            return f'"{title}." {citation.domain}, {date}. Web. {accessed}.'
        
        else:
            return f"{title} - {citation.url}"
    
    def format_all(self, style: str = "harvard") -> str:
        """
        Format all citations in a specific style.
        
        Args:
            style: Citation style
            
        Returns:
            Formatted bibliography string
        """
        citations = self.get_unique_citations()
        formatted = []
        
        for i, c in enumerate(citations, 1):
            formatted.append(f"[{i}] {self.format_citation(c, style)}")
        
        return "\n\n".join(formatted)
    
    def to_dict_list(self) -> List[Dict]:
        """Convert citations to list of dictionaries."""
        return [
            {
                "url": c.url,
                "title": c.title,
                "author": c.author,
                "date": c.date,
                "domain": c.domain,
                "accessed": c.accessed_date,
            }
            for c in self.get_unique_citations()
        ]


def extract_citations(text: str, notes: List[str] = None) -> CitationExtractor:
    """
    Convenience function to extract citations.
    
    Args:
        text: Main text content
        notes: Optional list of notes
        
    Returns:
        CitationExtractor with extracted citations
    """
    extractor = CitationExtractor()
    
    if text:
        extractor.extract_from_text(text)
    
    if notes:
        extractor.extract_from_notes(notes)
    
    return extractor


def format_bibliography(
    citations: List[str], 
    style: str = "harvard"
) -> str:
    """
    Format a list of citation URLs into a bibliography.
    
    Args:
        citations: List of URLs
        style: Citation style
        
    Returns:
        Formatted bibliography
    """
    extractor = CitationExtractor()
    for url in citations:
        if url.startswith("http"):
            extractor.citations.append(Citation(url=url))
    
    return extractor.format_all(style)
