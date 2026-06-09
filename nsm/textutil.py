"""캡처한 HTML/텍스트 후보를 사람이 읽을 본문으로 정제·분류하는 순수 함수들.

naver_books_dl/extractor.py 의 _html_to_text + 한국어 글자수 필터 로직 이식.
"""
import html as _html
import re

_MIN_KOREAN_CHARS = 200


def html_to_text(raw) -> str:
    """XHTML(bytes 또는 str) → 텍스트만. UTF-8 가정."""
    if isinstance(raw, (bytes, bytearray)):
        s = bytes(raw).decode('utf-8', errors='replace')
    else:
        s = raw
    s = re.sub(r'<script[^>]*>.*?</script>', '', s, flags=re.DOTALL | re.IGNORECASE)
    s = re.sub(r'<style[^>]*>.*?</style>', '', s, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '\n', s)
    text = _html.unescape(text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()


def count_korean(text: str) -> int:
    """완성형 한글 음절(가~힣) 개수."""
    return sum(1 for ch in text if '가' <= ch <= '힣')


def classify_capture(raw, min_korean_chars: int = _MIN_KOREAN_CHARS) -> dict:
    """캡처 후보가 '진짜 본문'인지 분류.

    반환: {korean, has_html, probably_body, preview}
    """
    if isinstance(raw, (bytes, bytearray)):
        rawstr = bytes(raw).decode('utf-8', errors='replace')
    else:
        rawstr = raw
    text = html_to_text(raw)
    kr = count_korean(text)
    return {
        'korean': kr,
        'has_html': '<html' in rawstr.lower(),
        'probably_body': kr >= min_korean_chars,
        'preview': text[:120],
    }
