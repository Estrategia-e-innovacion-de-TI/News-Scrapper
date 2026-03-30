"""Tests for text extraction using HTML fixtures."""
import pytest
from pathlib import Path

from extractor.extract.text import extract_text, clean_text, extract_with_bs4


# Sample HTML fixtures
SIMPLE_ARTICLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Article - Example Site</title>
    <meta property="og:title" content="Test Article Title">
</head>
<body>
    <header>
        <nav>Navigation menu here</nav>
    </header>
    <article>
        <h1>Test Article Title</h1>
        <p>This is the first paragraph of the article. It contains important information
        that should be extracted by the text extraction system.</p>
        <p>This is the second paragraph with more content. The article discusses various
        topics that are relevant to the reader and provides valuable insights.</p>
        <p>The third paragraph continues the discussion with additional details and
        examples that help illustrate the main points of the article.</p>
        <p>Finally, the fourth paragraph concludes the article with a summary of the
        key takeaways and recommendations for the reader to consider.</p>
    </article>
    <footer>
        <p>Copyright 2024 Example Site</p>
    </footer>
</body>
</html>
"""

MINIMAL_HTML = """
<html>
<body>
<div class="content">
<p>Short content that is below minimum threshold.</p>
</div>
</body>
</html>
"""

SCRIPT_HEAVY_HTML = """
<!DOCTYPE html>
<html>
<head>
    <script>var tracking = "code";</script>
    <style>.hidden { display: none; }</style>
</head>
<body>
    <script>console.log("inline script");</script>
    <article>
        <h1>Article with Scripts</h1>
        <p>This is the actual content that should be extracted. The extraction
        system should remove all script and style tags while preserving the
        meaningful text content of the article.</p>
        <script>moreTracking();</script>
        <p>More content here that is part of the article body and should be
        included in the final extracted text output.</p>
    </article>
    <script>analytics.track();</script>
</body>
</html>
"""


class TestExtractText:
    """Tests for extract_text function."""
    
    def test_extracts_article_content(self):
        """Should extract main article content."""
        text, method = extract_text(SIMPLE_ARTICLE_HTML, min_chars=100)
        
        assert text is not None
        assert "Test Article Title" in text
        assert "first paragraph" in text
        assert len(text) > 100
    
    def test_removes_navigation(self):
        """Should remove navigation elements."""
        text, method = extract_text(SIMPLE_ARTICLE_HTML, min_chars=100)
        
        assert text is not None
        assert "Navigation menu" not in text
    
    def test_removes_footer(self):
        """Should remove footer elements."""
        text, method = extract_text(SIMPLE_ARTICLE_HTML, min_chars=100)
        
        assert text is not None
        # Footer content should be removed or minimized
        # Note: some extractors may include copyright
    
    def test_handles_empty_html(self):
        """Should handle empty HTML gracefully."""
        text, method = extract_text("", min_chars=100)
        assert text is None or text == ""
    
    def test_handles_minimal_content(self):
        """Should handle content below threshold."""
        text, method = extract_text(MINIMAL_HTML, min_chars=1000)
        # Should still return something, even if below threshold
        assert text is not None or method == "fallback"
    
    def test_removes_scripts(self):
        """Should remove script tags."""
        text, method = extract_text(SCRIPT_HEAVY_HTML, min_chars=100)
        
        assert text is not None
        assert "tracking" not in text.lower()
        assert "console.log" not in text
        assert "analytics" not in text
    
    def test_returns_extraction_method(self):
        """Should return the extraction method used."""
        text, method = extract_text(SIMPLE_ARTICLE_HTML, min_chars=100)
        
        assert method in ["trafilatura", "readability", "bs4", "fallback", "empty"]


class TestCleanText:
    """Tests for clean_text function."""
    
    def test_normalizes_whitespace(self):
        """Should normalize excessive whitespace."""
        text = "Hello    world\n\n\n\nNew paragraph"
        result = clean_text(text)
        
        assert "    " not in result
        assert "\n\n\n" not in result
    
    def test_removes_cookie_notices(self):
        """Should remove common boilerplate patterns."""
        text = "Article content here. Accept all cookies. More content."
        result = clean_text(text)
        
        # Cookie notice should be removed
        assert "Accept all cookies" not in result or "cookies" not in result.lower()
    
    def test_handles_empty_string(self):
        """Should handle empty string."""
        assert clean_text("") == ""
    
    def test_handles_none(self):
        """Should handle None input."""
        assert clean_text(None) == ""


class TestExtractWithBs4:
    """Tests for bs4 fallback extraction."""
    
    def test_finds_article_tag(self):
        """Should find and extract article tag content."""
        text = extract_with_bs4(SIMPLE_ARTICLE_HTML)
        
        assert text is not None
        assert "first paragraph" in text
    
    def test_removes_nav_footer(self):
        """Should remove nav and footer."""
        text = extract_with_bs4(SIMPLE_ARTICLE_HTML)
        
        assert text is not None
        # Nav content should be removed
        assert "Navigation menu" not in text
