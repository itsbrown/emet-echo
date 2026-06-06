import re
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    """Extract human-readable plain text from an HTML document."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'head'):
            self._skip = True
        if tag in ('p', 'br', 'div', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr'):
            self._parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'head'):
            self._skip = False
        if tag in ('p', 'div', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr'):
            self._parts.append('\n')

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self):
        text = ''.join(self._parts)
        lines = [line.rstrip() for line in text.splitlines()]
        return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def extract_plain_text(raw_html):
    """Convert a raw HTML document to clean, human-readable plain text,
    preserving paragraph and line structure via block-level tag newlines."""
    extractor = _TextExtractor()
    extractor.feed(raw_html)
    return extractor.get_text()


def sanitize_html(html_or_text, strip=True):
    """Sanitize user/external content for safe display in templates.
    
    Uses bleach to remove dangerous tags/scripts while allowing a safe subset
    of HTML (for future rich content from trafilatura output_format='html').
    
    For plain text content (current default), this effectively HTML-escapes it.
    
    Call this on ingest for 'content' fields before storing.
    Then render the result with |safe in templates (only for sanitized fields).
    """
    import bleach

    if not html_or_text:
        return ""

    # Safe allowlist based on common article content needs
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'b', 'i', 'u',
        'ul', 'ol', 'li', 'blockquote', 'code', 'pre',
        'a', 'span', 'div'
    ]
    allowed_attrs = {
        'a': ['href', 'title', 'rel', 'target'],
        'span': ['class'],
        'div': ['class'],
    }

    cleaned = bleach.clean(
        html_or_text,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=strip,
        protocols=['http', 'https', 'mailto']
    )
    return cleaned
