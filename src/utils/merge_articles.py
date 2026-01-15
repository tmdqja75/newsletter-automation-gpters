"""Utility for merging individual articles into a complete newsletter."""

import re
from pathlib import Path
from typing import Optional

from ..config import (
    NEWSLETTER_HEADER_TEMPLATE,
    NEWSLETTER_FOOTER_TEMPLATE,
    ARTICLES_DIR,
)


def extract_title_from_article(content: str) -> str:
    """Extract the main title from an article.

    Args:
        content: The article content in markdown format

    Returns:
        The extracted title or empty string
    """
    lines = content.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line.startswith("## "):
            return line[3:].strip()
    return ""


def generate_toc(articles: list[tuple[str, str]]) -> str:
    """Generate table of contents from articles.

    Args:
        articles: List of (filename, content) tuples

    Returns:
        Formatted table of contents string
    """
    toc_items = []
    for filename, content in articles:
        title = extract_title_from_article(content)
        if title:
            # Remove emoji from title for TOC
            clean_title = re.sub(r"[\U0001F300-\U0001F9FF]", "", title).strip()
            toc_items.append(f"- **{clean_title}**")

    return "\n".join(toc_items)


def get_version_number(date_dir: str) -> str:
    """Calculate version number based on date directory.

    Simple incrementing version based on year-week.

    Args:
        date_dir: Date directory name (YYYY-MM-DD)

    Returns:
        Version string (e.g., "07")
    """
    # For now, return a simple placeholder
    # In production, this would track actual version numbers
    return "XX"


def merge_newsletter(date_dir: str, version: Optional[str] = None) -> str:
    """Merge individual articles into a complete newsletter.

    Args:
        date_dir: Date directory containing articles (e.g., "2026-01-15")
        version: Newsletter version number (optional, auto-generated if not provided)

    Returns:
        Path to the merged newsletter file
    """
    articles_path = Path(ARTICLES_DIR) / date_dir

    if not articles_path.exists():
        raise ValueError(f"Articles directory not found: {articles_path}")

    # Find and sort article files
    article_files = sorted(articles_path.glob("*.md"))
    article_files = [f for f in article_files if f.name != "newsletter.md"]

    if not article_files:
        raise ValueError(f"No article files found in {articles_path}")

    # Read all articles
    articles = []
    for file_path in article_files:
        content = file_path.read_text(encoding="utf-8")
        articles.append((file_path.name, content))

    # Get first article title for main title
    main_title = extract_title_from_article(articles[0][1]) if articles else "이번 주 AI 소식"

    # Generate subtitle from second article if exists
    subtitle = ""
    if len(articles) > 1:
        second_title = extract_title_from_article(articles[1][1])
        if second_title:
            subtitle = second_title

    # Generate TOC
    toc = generate_toc(articles)

    # Get version
    if version is None:
        version = get_version_number(date_dir)

    # Build header
    header = NEWSLETTER_HEADER_TEMPLATE.format(
        version=version,
        main_title=main_title,
        subtitle=subtitle,
        toc=toc,
    )

    # Combine all parts
    newsletter_parts = [header]

    for i, (filename, content) in enumerate(articles):
        # Add separator between articles
        if i > 0:
            newsletter_parts.append("\n\n---\n\n")
        newsletter_parts.append(content)

    newsletter_parts.append(NEWSLETTER_FOOTER_TEMPLATE)

    # Join and save
    full_newsletter = "\n".join(newsletter_parts)

    output_path = articles_path / "newsletter.md"
    output_path.write_text(full_newsletter, encoding="utf-8")

    return str(output_path)


def preview_newsletter(date_dir: str) -> str:
    """Preview the newsletter structure without saving.

    Args:
        date_dir: Date directory containing articles

    Returns:
        Preview string showing newsletter structure
    """
    articles_path = Path(ARTICLES_DIR) / date_dir

    if not articles_path.exists():
        return f"Directory not found: {articles_path}"

    article_files = sorted(articles_path.glob("*.md"))
    article_files = [f for f in article_files if f.name != "newsletter.md"]

    preview_lines = [f"Newsletter Preview for {date_dir}", "=" * 40, ""]

    for file_path in article_files:
        content = file_path.read_text(encoding="utf-8")
        title = extract_title_from_article(content)
        word_count = len(content.split())

        preview_lines.append(f"📄 {file_path.name}")
        preview_lines.append(f"   Title: {title}")
        preview_lines.append(f"   Words: {word_count}")
        preview_lines.append("")

    return "\n".join(preview_lines)
