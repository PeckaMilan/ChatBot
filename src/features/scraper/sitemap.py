"""Sitemap parsing utilities."""

import xml.etree.ElementTree as ET
from urllib.parse import urljoin

import httpx


class SitemapParser:
    """Parse XML sitemaps to extract URLs."""

    SITEMAP_NAMESPACE = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    async def parse(self, sitemap_url: str, max_urls: int = 500) -> list[str]:
        """
        Parse sitemap and return URLs.

        Args:
            sitemap_url: URL to sitemap.xml
            max_urls: Maximum URLs to return

        Returns:
            List of URLs from sitemap
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                sitemap_url,
                timeout=30.0,
                follow_redirects=True,
                headers={'User-Agent': 'ChatBot-Scraper/1.0'},
            )
            response.raise_for_status()

        urls = []

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError:
            # Try to extract URLs from text if XML parsing fails
            return self._extract_urls_from_text(response.text, max_urls)

        # Check if this is a sitemap index
        sitemap_refs = root.findall('.//sm:sitemap/sm:loc', self.SITEMAP_NAMESPACE)

        # Also try without namespace (some sitemaps don't use it)
        if not sitemap_refs:
            sitemap_refs = root.findall('.//sitemap/loc')

        if sitemap_refs:
            # Recursively parse referenced sitemaps
            for ref in sitemap_refs[:10]:  # Limit sitemap count
                if ref.text:
                    try:
                        sub_urls = await self.parse(ref.text, max_urls - len(urls))
                        urls.extend(sub_urls)
                        if len(urls) >= max_urls:
                            break
                    except Exception:
                        continue
        else:
            # Regular sitemap - extract URLs
            url_elements = root.findall('.//sm:url/sm:loc', self.SITEMAP_NAMESPACE)

            # Try without namespace
            if not url_elements:
                url_elements = root.findall('.//url/loc')

            for elem in url_elements:
                if elem.text:
                    urls.append(elem.text.strip())
                if len(urls) >= max_urls:
                    break

        return urls[:max_urls]

    def _extract_urls_from_text(self, text: str, max_urls: int) -> list[str]:
        """Fallback: extract URLs from text content."""
        import re
        url_pattern = r'https?://[^\s<>"\']+(?:\.html?|/)?'
        matches = re.findall(url_pattern, text)
        return list(set(matches))[:max_urls]

    async def find_sitemap(self, base_url: str) -> str | None:
        """Try to find sitemap for a domain."""
        common_paths = [
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemap/',
            '/sitemap.xml.gz',
        ]

        async with httpx.AsyncClient() as client:
            for path in common_paths:
                try:
                    url = urljoin(base_url, path)
                    response = await client.head(
                        url,
                        timeout=10.0,
                        follow_redirects=True,
                    )
                    if response.status_code == 200:
                        return url
                except Exception:
                    continue

            # Try robots.txt for sitemap location
            try:
                robots_url = urljoin(base_url, '/robots.txt')
                response = await client.get(robots_url, timeout=10.0)
                if response.status_code == 200:
                    for line in response.text.split('\n'):
                        if line.lower().startswith('sitemap:'):
                            return line.split(':', 1)[1].strip()
            except Exception:
                pass

        return None
