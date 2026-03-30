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
