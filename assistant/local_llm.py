import ipaddress
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


class WebFetcher:
    def _validate(self, url: str):
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Only http and https URLs are supported.")
        host = parsed.hostname.lower()
        if host in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Local URLs are not allowed.")
        try:
            addresses = socket.getaddrinfo(host, None)
            for address in addresses:
                ip = ipaddress.ip_address(address[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    raise ValueError("Private-network URLs are not allowed.")
        except socket.gaierror as exc:
            raise ValueError("The host could not be resolved.") from exc

    def fetch(self, url: str, max_bytes: int = 1_000_000):
        self._validate(url)
        response = requests.get(url, timeout=20, headers={"User-Agent": "Local-AI-Assistant/1.0"}, stream=True)
        response.raise_for_status()
        data = b""
        for chunk in response.iter_content(8192):
            data += chunk
            if len(data) > max_bytes:
                raise ValueError("The page is larger than the configured limit.")
        soup = BeautifulSoup(data, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return {"url": response.url, "title": soup.title.get_text(strip=True) if soup.title else response.url, "text": soup.get_text(" ", strip=True)}
