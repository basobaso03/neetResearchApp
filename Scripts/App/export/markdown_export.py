"""
Markdown Export Utility for NeetResearch App.

Provides simple markdown export without requiring LLM calls.
This is a lightweight alternative to the full HTML/PDF export.
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List


def clean_markdown(text: str) -> str:
    """
    Clean and format markdown text.
    
    Args:
        text: Raw markdown text
    
    Returns:
        Cleaned markdown text
    """
    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Fix common markdown issues
    # Ensure headers have space after #
    text = re.sub(r'^(#{1,6})([^#\s])', r'\1 \2', text, flags=re.MULTILINE)
    
    # Fix bullet points
    text = re.sub(r'^\s*[-*]\s*(.)', r'- \1', text, flags=re.MULTILINE)
    
    return text.strip()


def extract_title(text: str) -> str:
    """
    Extract title from markdown text.
    
    Args:
        text: Markdown text
    
    Returns:
        Extracted title or 'Research Report'
    """
    # Look for # Title
    match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    
    # Look for first line
    lines = text.strip().split('\n')
    if lines:
        first_line = lines[0].strip()
        if len(first_line) < 100:
            return first_line
    
    return "Research Report"


def export_to_markdown(
    content: str,
    filename: str = None,
    output_dir: str = "./output",
    add_metadata: bool = True,
    metadata: Optional[Dict] = None
) -> Path:
    """
    Export content to a markdown file.
    
    Args:
        content: Markdown content to export
        filename: Output filename (without extension)
        output_dir: Directory for output
        add_metadata: Whether to add metadata header
        metadata: Optional metadata dictionary
    
    Returns:
        Path to the exported file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename if not provided
    if not filename:
        title = extract_title(content)
        # Sanitize filename
        filename = re.sub(r'[^\w\s-]', '', title)[:50]
        filename = re.sub(r'[\s]+', '_', filename)
    
    # Add timestamp to filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    full_filename = f"{filename}_{timestamp}.md"
    
    # Build final content
    final_content = []
    
    if add_metadata:
        final_content.append("---")
        final_content.append(f"title: {extract_title(content)}")
        final_content.append(f"date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        final_content.append("generator: NeetResearch App")
        
        if metadata:
            for key, value in metadata.items():
                final_content.append(f"{key}: {value}")
        
        final_content.append("---")
        final_content.append("")
    
    # Clean and add content
    final_content.append(clean_markdown(content))
    
    # Write file
    output_path = Path(output_dir) / full_filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_content))
    
    print(f"✅ Exported to: {output_path}")
    return output_path


def export_with_sources(
    report: str,
    sources: List[str],
    filename: str = None,
    output_dir: str = "./output"
) -> Path:
    """
    Export report with formatted sources section.
    
    Args:
        report: Main report content
        sources: List of source strings
        filename: Output filename
        output_dir: Directory for output
    
    Returns:
        Path to the exported file
    """
    # Build full content
    content_parts = [report]
    
    if sources:
        content_parts.append("\n\n---\n\n## Sources\n")
        for i, source in enumerate(sources, 1):
            content_parts.append(f"{i}. {source}")
    
    full_content = '\n'.join(content_parts)
    
    return export_to_markdown(
        content=full_content,
        filename=filename,
        output_dir=output_dir,
        add_metadata=True
    )


class MarkdownExporter:
    """
    Class-based markdown exporter with configuration.
    """
    
    def __init__(
        self,
        output_dir: str = "./output",
        add_metadata: bool = True,
        with_toc: bool = False
    ):
        """
        Initialize exporter.
        
        Args:
            output_dir: Output directory
            add_metadata: Add YAML frontmatter
            with_toc: Add table of contents
        """
        self.output_dir = output_dir
        self.add_metadata = add_metadata
        self.with_toc = with_toc
        os.makedirs(output_dir, exist_ok=True)
    
    def _generate_toc(self, content: str) -> str:
        """Generate table of contents from headers."""
        toc_lines = ["## Table of Contents\n"]
        
        for line in content.split('\n'):
            if line.startswith('#'):
                level = len(re.match(r'^#+', line).group())
                title = line.lstrip('#').strip()
                anchor = re.sub(r'[^\w\s-]', '', title.lower())
                anchor = re.sub(r'\s+', '-', anchor)
                
                indent = "  " * (level - 1)
                toc_lines.append(f"{indent}- [{title}](#{anchor})")
        
        return '\n'.join(toc_lines) + '\n\n'
    
    def export(
        self,
        content: str,
        filename: str = None,
        metadata: Optional[Dict] = None
    ) -> Path:
        """
        Export content to markdown.
        
        Args:
            content: Content to export
            filename: Output filename
            metadata: Optional metadata
        
        Returns:
            Path to exported file
        """
        final_content = clean_markdown(content)
        
        if self.with_toc:
            toc = self._generate_toc(final_content)
            # Insert TOC after first header
            lines = final_content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('#'):
                    lines.insert(i + 1, '\n' + toc)
                    break
            final_content = '\n'.join(lines)
        
        return export_to_markdown(
            content=final_content,
            filename=filename,
            output_dir=self.output_dir,
            add_metadata=self.add_metadata,
            metadata=metadata
        )
