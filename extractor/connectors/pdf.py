"""PDF download and extraction connector."""
from __future__ import annotations

import io
import logging
from pathlib import Path

import httpx
from PyPDF2 import PdfReader

from ..state import FetchMethod, QueueItem, SourceConfig
from ..utils import rate_limiter

logger = logging.getLogger("news_radar.pdf")


async def download_pdf(
    url: str,
    timeout: int = 60,
) -> tuple[bytes | None, int, str | None]:
    """Download PDF file. Returns (content, status_code, error_type)."""
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            response = await client.get(url, headers={
                "User-Agent": "NewsRadarMVP/0.1 (+contact: security-research@yourorg.com)",
                "Accept": "application/pdf,*/*",
            })
            
            status = response.status_code
            
            if status == 200:
                return response.content, status, None
            elif status == 403:
                return None, status, "403"
            elif status == 402:
                return None, status, "paywall"
            else:
                return None, status, "unknown"
                
    except httpx.TimeoutException:
        logger.error(f"Timeout downloading PDF: {url}")
        return None, 0, "timeout"
    except Exception as e:
        logger.error(f"Error downloading PDF {url}: {e}")
        return None, 0, "unknown"


def extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF content."""
    try:
        reader = PdfReader(io.BytesIO(content))
        
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
        
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return ""


async def discover_pdf_items(
    source: SourceConfig,
    max_items: int = 10,
) -> list[QueueItem]:
    """Discover PDF items from source."""
    items = []
    
    pdf_urls = source.pdf_urls or []
    
    for url in pdf_urls[:max_items]:
        item = QueueItem(
            source_id=source.source_id,
            url=url,
            source_url=url,
            fetch_method=FetchMethod.PDF,
            requires_playwright=False,
        )
        items.append(item)
    
    logger.info(f"[{source.source_id}] Discovered {len(items)} PDF items")
    return items


async def fetch_and_extract_pdf(
    url: str,
    source_id: str,
    timeout: int = 60,
    rate_limit_rps: float = 1.0,
) -> tuple[str | None, str | None]:
    """
    Download and extract text from PDF.
    Returns (text, error_type).
    """
    await rate_limiter.wait(source_id, rate_limit_rps)
    
    logger.info(f"[{source_id}] Downloading PDF: {url}")
    
    content, status, error = await download_pdf(url, timeout)
    
    if error or not content:
        return None, error or "unknown"
    
    text = extract_pdf_text(content)
    
    if not text:
        return None, "parse"
    
    return text, None
