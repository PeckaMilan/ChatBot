"""HTML content extraction utilities."""

import re
from urllib.parse import urljoin, urlparse


class HTMLExtractor:
    """Extract clean text content from HTML."""

    # Tags to remove completely (with content)
    REMOVE_TAGS = [
        'script', 'style', 'nav', 'footer', 'header',
        'aside', 'form', 'noscript', 'iframe', 'svg',
        'button', 'input', 'select', 'textarea',
    ]

    # Tags that typically contain main content
    CONTENT_SELECTORS = ['article', 'main', '[role="main"]', '.content', '#content']

    def extract(self, html: str, url: str) -> dict:
        """
        Extract text and metadata from HTML.

        Args:
            html: Raw HTML string
            url: Source URL for resolving relative links

        Returns:
            Dict with title, content, links, word_count
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'lxml')

        # Extract title
        title = self._extract_title(soup)

        # Remove unwanted tags
        for tag in self.REMOVE_TAGS:
            for element in soup.find_all(tag):
                element.decompose()

        # Try to find main content area
        main_content = self._find_main_content(soup)

        # Extract text
        text = main_content.get_text(separator='\n', strip=True)

        # Clean up text
        text = self._clean_text(text)

        # Extract links for sitemap crawling
        links = self._extract_links(soup, url)

        return {
            'title': title,
            'content': text,
            'links': links,
            'word_count': len(text.split()),
        }

    def _extract_title(self, soup) -> str | None:
        """Extract page title."""
        if soup.title and soup.title.string:
            return soup.title.string.strip()

        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)

        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content']

        return None

    def _find_main_content(self, soup):
        """Find the main content area of the page."""
        for selector in self.CONTENT_SELECTORS:
            if selector.startswith('.'):
                element = soup.find(class_=selector[1:])
            elif selector.startswith('#'):
                element = soup.find(id=selector[1:])
            elif selector.startswith('['):
                # Attribute selector like [role="main"]
                match = re.match(r'\[(\w+)="(\w+)"\]', selector)
                if match:
                    element = soup.find(attrs={match.group(1): match.group(2)})
                else:
                    element = None
            else:
                element = soup.find(selector)

            if element:
                return element

        return soup.body or soup

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\t+', ' ', text)

        # Remove common boilerplate patterns
        boilerplate_patterns = [
            r'Cookie.*?consent.*?\n',
            r'Accept\s+all\s+cookies.*?\n',
            r'Privacy\s+Policy.*?\n',
            r'©\s*\d{4}.*?\n',
            r'All\s+rights\s+reserved.*?\n',
        ]
        for pattern in boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text.strip()

    def _extract_links(self, soup, base_url: str) -> list[str]:
        """Extract valid links from the page."""
        links = []
        base_parsed = urlparse(base_url)

        for a in soup.find_all('a', href=True):
            href = a['href']

            # Skip anchors and javascript
            if href.startswith('#') or href.startswith('javascript:'):
                continue

            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            # Same domain only
            if parsed.netloc != base_parsed.netloc:
                continue

            # Skip non-HTML resources
            skip_extensions = [
                '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg',
                '.css', '.js', '.zip', '.doc', '.docx', '.xls', '.xlsx',
            ]
            if any(parsed.path.lower().endswith(ext) for ext in skip_extensions):
                continue

            links.append(full_url)

        return list(set(links))
