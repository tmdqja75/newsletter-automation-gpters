"""Content extraction and analysis tools."""

import json
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def fetch_article_content(url: str) -> str:
    """Fetch and extract the main content from a URL.

    Args:
        url: The URL of the article to fetch

    Returns:
        JSON string containing the extracted title, content, and metadata
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string or ""
        elif soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)

        # Extract main content
        # Try common article containers
        content = ""
        article_selectors = [
            "article",
            '[role="main"]',
            ".post-content",
            ".article-content",
            ".entry-content",
            "main",
            ".content",
        ]

        for selector in article_selectors:
            article = soup.select_one(selector)
            if article:
                content = article.get_text(separator="\n", strip=True)
                break

        if not content:
            # Fallback to body content
            body = soup.find("body")
            if body:
                content = body.get_text(separator="\n", strip=True)

        # Clean up content
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        content = "\n".join(lines)

        # Truncate if too long
        if len(content) > 10000:
            content = content[:10000] + "...[truncated]"

        # Extract metadata
        domain = urlparse(url).netloc
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content", "")

        return json.dumps(
            {
                "url": url,
                "domain": domain,
                "title": title,
                "description": description,
                "content": content,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return json.dumps({"error": str(e), "url": url})


def analyze_tech_blog(url: str) -> str:
    """Analyze a tech blog post and extract key insights.

    Specialized for tech company blogs (Anthropic, OpenAI, Google).

    Args:
        url: URL of the tech blog post

    Returns:
        JSON string with structured analysis including key points and summary
    """
    # First fetch the content
    content_result = fetch_article_content(url)
    content_data = json.loads(content_result)

    if "error" in content_data:
        return content_result

    domain = content_data.get("domain", "")
    title = content_data.get("title", "")
    content = content_data.get("content", "")

    # Identify blog type
    blog_type = "unknown"
    if "anthropic.com" in domain:
        blog_type = "anthropic"
    elif "openai.com" in domain:
        blog_type = "openai"
    elif "google" in domain or "deepmind" in domain:
        blog_type = "google"
    elif "huggingface.co" in domain:
        blog_type = "huggingface"

    # Extract sections (basic heuristic)
    sections = []
    current_section = {"heading": "Introduction", "content": []}

    for line in content.split("\n"):
        # Simple heading detection
        if len(line) < 100 and line.isupper():
            if current_section["content"]:
                sections.append(current_section)
            current_section = {"heading": line, "content": []}
        else:
            current_section["content"].append(line)

    if current_section["content"]:
        sections.append(current_section)

    # Format sections
    formatted_sections = []
    for section in sections[:10]:  # Limit to 10 sections
        formatted_sections.append({
            "heading": section["heading"],
            "preview": "\n".join(section["content"][:5]),
        })

    return json.dumps(
        {
            "url": url,
            "blog_type": blog_type,
            "title": title,
            "sections": formatted_sections,
            "full_content_length": len(content),
        },
        ensure_ascii=False,
        indent=2,
    )
