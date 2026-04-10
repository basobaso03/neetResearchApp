"""
Metadata Extractor for NeetResearch App.

Extracts metadata from web pages and documents:
- Title, author, date
- Description/summary
- Publication info
"""

import re
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse


@dataclass
class PageMetadata:
    """Metadata extracted from a web page or document."""
    url: str
    title: str = ""
    author: str = ""
    date: str = ""
    description: str = ""
    domain: str = ""
    keywords: List[str] = field(default_factory=list)
    content_type: str = "web"
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        if self.url and not self.domain:
            parsed = urlparse(self.url)
            self.domain = parsed.netloc


class MetadataExtractor:
    """
    Extracts metadata from various sources.
    """
    
    # Common author patterns
    AUTHOR_PATTERNS = [
        re.compile(r'by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', re.IGNORECASE),
        re.compile(r'author[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', re.IGNORECASE),
        re.compile(r'written\s+by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', re.IGNORECASE),
    ]
    
    # Date patterns
    DATE_PATTERNS = [
        # ISO format: 2024-01-25
        re.compile(r'(\d{4}-\d{2}-\d{2})'),
        # US format: January 25, 2024
        re.compile(r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})'),
        # Short: Jan 25, 2024
        re.compile(r'([A-Z][a-z]{2,3}\s+\d{1,2},?\s+\d{4})'),
        # European: 25 January 2024
        re.compile(r'(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})'),
    ]
    
    def __init__(self):
        self.metadata_cache: Dict[str, PageMetadata] = {}
    
    def extract_from_html(self, html: str, url: str = "") -> PageMetadata:
        """
        Extract metadata from HTML content.
        
        Args:
            html: HTML content
            url: Source URL
            
        Returns:
            PageMetadata object
        """
        metadata = PageMetadata(url=url)
        
        # Extract title
        metadata.title = self._extract_title(html)
        
        # Extract author
        metadata.author = self._extract_author(html)
        
        # Extract date
        metadata.date = self._extract_date(html)
        
        # Extract description
        metadata.description = self._extract_description(html)
        
        # Cache the result
        if url:
            self.metadata_cache[url] = metadata
        
        return metadata
    
    def _extract_title(self, html: str) -> str:
        """Extract title from HTML."""
        # Try <title> tag
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        
        # Try <h1>
        h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
        if h1_match:
            return h1_match.group(1).strip()
        
        # Try og:title
        og_match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
        if og_match:
            return og_match.group(1).strip()
        
        return ""
    
    def _extract_author(self, html: str) -> str:
        """Extract author from HTML."""
        # Try meta author
        author_meta = re.search(
            r'<meta\s+name=["\']author["\']\s+content=["\'](.*?)["\']',
            html, re.IGNORECASE
        )
        if author_meta:
            return author_meta.group(1).strip()
        
        # Try common patterns in text
        for pattern in self.AUTHOR_PATTERNS:
            match = pattern.search(html)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_date(self, html: str) -> str:
        """Extract publication date from HTML."""
        # Try schema.org datePublished
        date_match = re.search(
            r'datePublished["\']?\s*[:\s]+["\']?(\d{4}-\d{2}-\d{2})',
            html, re.IGNORECASE
        )
        if date_match:
            return date_match.group(1)
        
        # Try meta date
        meta_date = re.search(
            r'<meta\s+(?:name|property)=["\'](?:article:published_time|date)["\'].*?content=["\'](.*?)["\']',
            html, re.IGNORECASE
        )
        if meta_date:
            return meta_date.group(1)[:10]  # First 10 chars for ISO date
        
        # Try common patterns
        for pattern in self.DATE_PATTERNS:
            match = pattern.search(html)
            if match:
                return match.group(1)
        
        return ""
    
    def _extract_description(self, html: str) -> str:
        """Extract description from HTML."""
        # Try meta description
        desc_match = re.search(
            r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
            html, re.IGNORECASE
        )
        if desc_match:
            return desc_match.group(1).strip()
        
        # Try og:description
        og_desc = re.search(
            r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']',
            html, re.IGNORECASE
        )
        if og_desc:
            return og_desc.group(1).strip()
        
        return ""
    
    def extract_from_text(self, text: str, url: str = "") -> PageMetadata:
        """
        Extract metadata from plain text content.
        
        Args:
            text: Plain text content
            url: Source URL
            
        Returns:
            PageMetadata object
        """
        metadata = PageMetadata(url=url, content_type="text")
        
        # Try to get title from first line
        lines = text.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            if len(first_line) < 200:
                metadata.title = first_line
        
        # Extract author
        for pattern in self.AUTHOR_PATTERNS:
            match = pattern.search(text)
            if match:
                metadata.author = match.group(1)
                break
        
        # Extract date
        for pattern in self.DATE_PATTERNS:
            match = pattern.search(text)
            if match:
                metadata.date = match.group(1)
                break
        
        return metadata
    
    def get_cached(self, url: str) -> Optional[PageMetadata]:
        """Get cached metadata for a URL."""
        return self.metadata_cache.get(url)
    
    def to_citation_info(self, metadata: PageMetadata) -> Dict:
        """
        Convert metadata to citation info dict.
        
        Args:
            metadata: PageMetadata object
            
        Returns:
            Dictionary suitable for citation formatting
        """
        return {
            "url": metadata.url,
            "title": metadata.title or "Untitled",
            "author": metadata.author or metadata.domain or "Unknown",
            "date": metadata.date or "n.d.",
            "accessed": metadata.extracted_at[:10],
        }


def extract_metadata(content: str, url: str = "", is_html: bool = False) -> PageMetadata:
    """
    Convenience function to extract metadata.
    
    Args:
        content: Content to extract from
        url: Source URL
        is_html: Whether content is HTML
        
    Returns:
        PageMetadata object
    """
    extractor = MetadataExtractor()
    
    if is_html:
        return extractor.extract_from_html(content, url)
    else:
        return extractor.extract_from_text(content, url)
