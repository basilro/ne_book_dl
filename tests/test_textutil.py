from nsm.textutil import html_to_text, count_korean, classify_capture


def test_html_to_text_strips_tags_and_unescapes():
    assert html_to_text('<p>안녕&amp;하세요</p>') == '안녕&하세요'


def test_html_to_text_drops_script_and_style():
    out = html_to_text('<div>본문<script>var x=1;</script><style>.a{}</style>끝</div>')
    assert 'var x' not in out
    assert '.a{' not in out
    assert '본문' in out and '끝' in out


def test_html_to_text_accepts_bytes():
    assert html_to_text('<p>가나다</p>'.encode('utf-8')) == '가나다'


def test_count_korean_counts_only_hangul_syllables():
    assert count_korean('abc가나다123힣') == 4


def test_classify_capture_flags_real_body():
    raw = '<html><body>' + ('가' * 250) + '</body></html>'
    info = classify_capture(raw)
    assert info['has_html'] is True
    assert info['korean'] >= 250
    assert info['probably_body'] is True


def test_classify_capture_rejects_ui_chrome():
    raw = '<div class="rank">랭킹 1 2 3</div>'
    info = classify_capture(raw)
    assert info['probably_body'] is False
