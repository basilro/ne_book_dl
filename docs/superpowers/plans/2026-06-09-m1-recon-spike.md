# M1 정찰 스파이크 (go/no-go) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 안드로이드 네이버 시리즈 앱이 회차 본문을 어디서·어떤 형태로 평문화하는지 규명하는 Frida 계측 하니스와 go/no-go 보고서를 만든다.

**Architecture:** 리눅스 호스트의 KVM 가속 Android 에뮬레이터(AVD)에서 시리즈 앱을 구동하고, Frida로 후보 렌더/복호화 지점을 후킹해 통과하는 데이터를 관찰한다. 캡처 후보는 공용 텍스트 유틸(한국어 글자수·HTML 판별)로 "진짜 본문인지" 분류한다. 후킹이 깨끗하지 않으면 Frida `Memory.scan` 폴백으로 `<html` 청크를 찾는다.

**Tech Stack:** Python 3.11+, frida / frida-tools, pytest, Android Studio AVD(non-Play AOSP x86_64), adb, uiautomator2(선택).

**실행 위치 표기:** 각 Task에 `[DEV]`(Windows/리눅스 어디서나, 코드 작성·단위테스트) 또는 `[LINUX-RUNTIME]`(리눅스+KVM 호스트에서 사람이 실기 실행) 표시.

---

## File Structure

```
naver_series_mobile/
├── requirements.txt              # 런타임 의존성
├── requirements-dev.txt          # pytest
├── .gitignore
├── README.md
├── nsm/
│   ├── __init__.py
│   └── textutil.py               # html_to_text / count_korean / classify_capture (테스트됨)
├── recon/
│   ├── frida/
│   │   └── observe.js            # 후보 렌더/복호화 지점 후킹
│   ├── observe.py                # frida 드라이버: attach + observe.js 로드 + 캡처 분류·저장
│   ├── memscan.py                # 폴백: frida Memory.scan 으로 <html 탐색
│   └── out/.gitkeep              # 캡처 산출물(내용은 gitignore)
├── docs/
│   ├── RUNBOOK-m1.md             # 리눅스 셋업 + 정찰 절차
│   ├── FINDINGS-m1.md            # go/no-go 보고서 템플릿
│   └── superpowers/...           # 설계/계획 문서
└── tests/
    └── test_textutil.py
```

각 책임: `nsm/textutil.py`는 순수 함수(어디서나 테스트 가능). `recon/`는 디바이스가 있어야 도는 계측 하니스. `docs/RUNBOOK-m1.md`는 사람이 따라 하는 절차. `docs/FINDINGS-m1.md`는 결정 산출물.

---

## Task 0: 리포지토리 스캐폴드 [DEV]

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `README.md`, `nsm/__init__.py`, `recon/out/.gitkeep`

- [ ] **Step 1: requirements.txt 작성**

Create `requirements.txt`:
```
frida>=16,<17
frida-tools>=12
requests>=2.31
```

- [ ] **Step 2: requirements-dev.txt 작성**

Create `requirements-dev.txt`:
```
-r requirements.txt
pytest>=8
```

- [ ] **Step 3: .gitignore 작성**

Create `.gitignore`:
```
__pycache__/
*.pyc
.venv/
venv/
recon/out/*
!recon/out/.gitkeep
*.apk
cookie.txt
.env
```

- [ ] **Step 4: README.md 작성**

Create `README.md`:
```markdown
# naver_series_mobile

리눅스 위 안드로이드 네이버 시리즈 앱을 헤드리스 구동해, 앱이 복호화한
회차 본문 평문을 Frida 후킹(폴백: 메모리 스캔)으로 캡처하는 추출기.
DRM 자체를 깨지 않고 공식 앱이 화면에 펼친 본문을 읽는 개인 백업 도구.
본인이 라이센스 보유한 콘텐츠만 대상.

설계: `docs/superpowers/specs/2026-06-09-naver-series-mobile-extractor-design.md`
현재 단계: M1 정찰 스파이크 — `docs/RUNBOOK-m1.md` 참고.

## 개발 환경
    python -m venv .venv && . .venv/bin/activate
    pip install -r requirements-dev.txt
    pytest
```

- [ ] **Step 5: 패키지/디렉토리 초기화**

Create `nsm/__init__.py` (빈 파일).
Create `recon/out/.gitkeep` (빈 파일).

- [ ] **Step 6: 커밋**

```bash
cd D:/04.source/naver_series_mobile
git add -A
git commit -m "chore: 프로젝트 스캐폴드 (deps, gitignore, README, 패키지 구조)"
```

---

## Task 1: 텍스트 유틸 — TDD [DEV]

`naver_books_dl/extractor.py`의 `_html_to_text`/한국어 필터 로직을 순수 함수로 이식하고, 캡처 후보를 "진짜 본문"으로 분류하는 `classify_capture`를 추가한다. M1에서 캡처가 본문인지 판정하는 데 쓰인다.

**Files:**
- Create: `tests/test_textutil.py`
- Create: `nsm/textutil.py`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `tests/test_textutil.py`:
```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_textutil.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'nsm.textutil'`

- [ ] **Step 3: 최소 구현 작성**

Create `nsm/textutil.py`:
```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_textutil.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: 커밋**

```bash
git add nsm/textutil.py tests/test_textutil.py
git commit -m "feat: 본문 정제·분류 텍스트 유틸 (naver_books_dl에서 이식 + TDD)"
```

---

## Task 2: Frida 관찰 스크립트 observe.js [DEV 작성 / LINUX-RUNTIME 검증]

본문이 통과할 만한 후보 지점을 모두 후킹해, 한글이 많거나 `<html`을 포함한 데이터가 흐르면 Python 드라이버로 샘플을 `send()` 한다. 디바이스 없이는 단위테스트 불가 → 작성 후 런북에서 실기 검증.

**Files:**
- Create: `recon/frida/observe.js`

- [ ] **Step 1: observe.js 작성**

Create `recon/frida/observe.js`:
```javascript
'use strict';
// 안드로이드 시리즈 앱 본문 평문화 지점 정찰용 Frida 스크립트.
// 후보: WebView 로드 계열, TextView.setText, 네이티브 라이브러리 로드(dlopen).
// 한글이 충분하거나 <html 포함 시 host(observe.py)로 샘플 전송.

var MIN_HANGUL = 50; // 정찰 단계는 낮게 — 본문 조각도 보기 위함

function hangulCount(s) {
  if (!s) return 0;
  var n = 0;
  for (var i = 0; i < s.length; i++) {
    var c = s.charCodeAt(i);
    if (c >= 0xAC00 && c <= 0xD7A3) n++;
  }
  return n;
}

function report(source, text) {
  if (text == null) return;
  var str = '' + text;
  var hc = hangulCount(str);
  var hasHtml = str.toLowerCase().indexOf('<html') >= 0;
  if (hc < MIN_HANGUL && !hasHtml) return;
  send({ source: source, hangul: hc, hasHtml: hasHtml, length: str.length },
       str.length > 200000 ? str.substring(0, 200000) : str);
}

Java.perform(function () {
  // 1) WebView 로드 계열
  try {
    var WebView = Java.use('android.webkit.WebView');
    WebView.loadDataWithBaseURL.implementation = function (base, data, mime, enc, hist) {
      report('WebView.loadDataWithBaseURL', data);
      return this.loadDataWithBaseURL(base, data, mime, enc, hist);
    };
    WebView.loadData.implementation = function (data, mime, enc) {
      report('WebView.loadData', data);
      return this.loadData(data, mime, enc);
    };
    WebView.loadUrl.overload('java.lang.String').implementation = function (url) {
      send({ source: 'WebView.loadUrl', url: '' + url }, null);
      return this.loadUrl(url);
    };
    WebView.evaluateJavascript.implementation = function (js, cb) {
      report('WebView.evaluateJavascript', js);
      return this.evaluateJavascript(js, cb);
    };
    console.log('[observe] WebView hooks installed');
  } catch (e) { console.log('[observe] WebView hook fail: ' + e); }

  // 2) 네이티브 TextView 렌더
  try {
    var TextView = Java.use('android.widget.TextView');
    TextView.setText.overload('java.lang.CharSequence').implementation = function (cs) {
      report('TextView.setText', cs);
      return this.setText(cs);
    };
    console.log('[observe] TextView hook installed');
  } catch (e) { console.log('[observe] TextView hook fail: ' + e); }

  // 3) 네이티브 라이브러리 로드 추적 (Fasoo .so 식별)
  try {
    var Runtime = Java.use('java.lang.Runtime');
    Runtime.loadLibrary0.overload('java.lang.Class', 'java.lang.String').implementation = function (cls, name) {
      send({ source: 'loadLibrary', lib: '' + name }, null);
      return this.loadLibrary0(cls, name);
    };
    console.log('[observe] loadLibrary hook installed');
  } catch (e) { console.log('[observe] loadLibrary hook fail: ' + e); }
});

// 4) dlopen 추적 (libc 레벨)
try {
  var dlopen = Module.findExportByName(null, 'dlopen');
  if (dlopen) {
    Interceptor.attach(dlopen, {
      onEnter: function (args) {
        try { send({ source: 'dlopen', path: args[0].readUtf8String() }, null); } catch (e) {}
      }
    });
    console.log('[observe] dlopen hook installed');
  }
} catch (e) { console.log('[observe] dlopen hook fail: ' + e); }
```

- [ ] **Step 2: JS 문법 검증 (node 있으면)**

Run: `node --check recon/frida/observe.js`
Expected: 출력 없음(종료코드 0). node가 없으면 이 단계는 건너뛰고 런북의 실기 로드 시 frida가 파싱 오류를 보고한다.

- [ ] **Step 3: 커밋**

```bash
git add recon/frida/observe.js
git commit -m "feat: Frida 관찰 스크립트 — WebView/TextView/네이티브로드 후킹"
```

---

## Task 3: Frida 드라이버 observe.py [DEV 작성 / LINUX-RUNTIME 검증]

observe.js를 실행 중인 앱에 붙여 메시지를 받고, 각 샘플을 `classify_capture`로 분류해 콘솔에 요약 + `recon/out/`에 저장한다.

**Files:**
- Create: `recon/observe.py`

- [ ] **Step 1: observe.py 작성**

Create `recon/observe.py`:
```python
"""실행 중인 시리즈 앱에 Frida attach → observe.js 로드 → 캡처 분류·저장.

사용:
    python recon/observe.py --package com.nhn.android.nbooks
    # 패키지명 확인: adb shell pm list packages | grep -i nhn
"""
import argparse
import json
import sys
import time
from pathlib import Path

import frida

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nsm.textutil import classify_capture  # noqa: E402

OUT = Path(__file__).resolve().parent / 'out'
SCRIPT = Path(__file__).resolve().parent / 'frida' / 'observe.js'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', required=True, help='앱 패키지명 또는 프로세스명')
    ap.add_argument('--spawn', action='store_true', help='attach 대신 새로 spawn')
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    device = frida.get_usb_device(timeout=10)
    print(f'[*] device: {device}')

    if args.spawn:
        pid = device.spawn([args.package])
        session = device.attach(pid)
    else:
        session = device.attach(args.package)
    print(f'[*] attached to {args.package}')

    seen = {'n': 0}

    def on_message(message, data):
        if message.get('type') != 'send':
            print(f'[frida] {message}')
            return
        payload = message['payload']
        src = payload.get('source', '?')
        if 'lib' in payload or 'path' in payload or 'url' in payload:
            print(f'[lib/url] {src}: {payload}')
            return
        body = data.decode('utf-8', 'replace') if isinstance(data, (bytes, bytearray)) else (data or '')
        info = classify_capture(body)
        seen['n'] += 1
        idx = seen['n']
        flag = 'BODY!' if info['probably_body'] else 'ui?'
        print(f'[{idx:03d}][{flag}] {src} hangul={info["korean"]} html={info["has_html"]} '
              f'len={payload.get("length")} :: {info["preview"]!r}')
        (OUT / f'cap_{idx:03d}_{src.replace(".", "_")}.txt').write_text(body, encoding='utf-8')
        (OUT / f'cap_{idx:03d}_{src.replace(".", "_")}.json').write_text(
            json.dumps({**payload, **{k: v for k, v in info.items() if k != 'preview'}},
                       ensure_ascii=False, indent=1), encoding='utf-8')

    script = session.create_script(SCRIPT.read_text(encoding='utf-8'))
    script.on('message', on_message)
    script.load()
    if args.spawn:
        device.resume(pid)
    print('[*] observe.js loaded. 앱에서 회차를 열어보세요. Ctrl+C 로 종료.')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n[*] 종료')
        session.detach()


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: import 가능 여부 검증 (frida 미설치여도 파싱은 확인)**

Run: `python -c "import ast; ast.parse(open('recon/observe.py', encoding='utf-8').read()); print('parse ok')"`
Expected: `parse ok`

- [ ] **Step 3: 커밋**

```bash
git add recon/observe.py
git commit -m "feat: Frida 드라이버 — attach + observe.js + 캡처 분류/저장"
```

---

## Task 4: 메모리 스캔 폴백 memscan.py [DEV 작성 / LINUX-RUNTIME 검증]

후킹이 깨끗하지 않을 때, frida `Memory.scan`으로 앱 프로세스 메모리에서 `<html` 바이트 패턴을 찾아 청크를 덤프하고 `classify_capture`로 분류한다. (Windows판 extractor.py의 안드로이드 대응.)

**Files:**
- Create: `recon/memscan.py`

- [ ] **Step 1: memscan.py 작성**

Create `recon/memscan.py`:
```python
"""폴백: frida Memory.scan 으로 앱 메모리에서 <html ... </html> 청크 탐색.

사용:
    python recon/memscan.py --package com.nhn.android.nbooks
"""
import argparse
import sys
import time
from pathlib import Path

import frida

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nsm.textutil import classify_capture  # noqa: E402

OUT = Path(__file__).resolve().parent / 'out'

# rw- 영역을 훑어 <html 패턴(UTF-8 "3c 68 74 6d 6c") 검색, 최대 4MB 청크 추출
SCAN_JS = r"""
'use strict';
var PATTERN = '3c 68 74 6d 6c'; // "<html"
function run() {
  var ranges = Process.enumerateRanges({ protection: 'r--', coalesce: true });
  send({ kind: 'info', ranges: ranges.length });
  var hits = 0;
  ranges.forEach(function (r) {
    try {
      Memory.scanSync(r.base, r.size, PATTERN).forEach(function (m) {
        try {
          var max = 4 * 1024 * 1024;
          var avail = r.size - m.address.sub(r.base).toInt32();
          var n = Math.min(max, avail);
          var bytes = Memory.readByteArray(m.address, n);
          hits++;
          send({ kind: 'hit', addr: m.address.toString(), len: n }, bytes);
        } catch (e) {}
      });
    } catch (e) {}
  });
  send({ kind: 'done', hits: hits });
}
run();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', required=True)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    device = frida.get_usb_device(timeout=10)
    session = device.attach(args.package)
    print(f'[*] attached to {args.package}')

    state = {'i': 0}

    def on_message(message, data):
        if message.get('type') != 'send':
            print(f'[frida] {message}')
            return
        p = message['payload']
        if p.get('kind') == 'info':
            print(f'[*] scanning {p["ranges"]} ranges...')
        elif p.get('kind') == 'hit' and data:
            body = bytes(data)
            # </html> 까지로 자르기
            end = body.lower().find(b'</html>')
            if end >= 0:
                body = body[:end + 7]
            info = classify_capture(body)
            if not info['probably_body']:
                return
            state['i'] += 1
            idx = state['i']
            print(f'[hit {idx:03d}] addr={p["addr"]} hangul={info["korean"]} '
                  f':: {info["preview"]!r}')
            (OUT / f'mem_{idx:03d}.txt').write_text(
                body.decode('utf-8', 'replace'), encoding='utf-8')
        elif p.get('kind') == 'done':
            print(f'[*] scan done. raw hits={p["hits"]}, body hits saved={state["i"]}')

    script = session.create_script(SCAN_JS)
    script.on('message', on_message)
    script.load()
    time.sleep(2)
    session.detach()


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 파싱 검증**

Run: `python -c "import ast; ast.parse(open('recon/memscan.py', encoding='utf-8').read()); print('parse ok')"`
Expected: `parse ok`

- [ ] **Step 3: 커밋**

```bash
git add recon/memscan.py
git commit -m "feat: 메모리 스캔 폴백 — frida Memory.scan 으로 <html 청크 추출"
```

---

## Task 5: 리눅스 정찰 런북 작성 [DEV 작성 / LINUX-RUNTIME 사용]

**Files:**
- Create: `docs/RUNBOOK-m1.md`

- [ ] **Step 1: RUNBOOK-m1.md 작성**

Create `docs/RUNBOOK-m1.md`:
```markdown
# M1 정찰 런북 (리눅스 + KVM)

> 사람이 리눅스 호스트에서 순서대로 실행. Ubuntu 22.04+ 기준.

## 0. 사전 점검
    egrep -c '(vmx|svm)' /proc/cpuinfo   # > 0 이면 가상화 지원
    ls /dev/kvm                          # 존재해야 함 (없으면 BIOS 가상화 ON + kvm 모듈)
    sudo usermod -aG kvm "$USER"         # 로그아웃/로그인

## 1. Android SDK / 에뮬레이터 (cmdline-tools)
    # https://developer.android.com/studio#command-line-tools-only 에서 linux zip
    mkdir -p ~/Android/cmdline-tools && cd ~/Android/cmdline-tools
    # unzip 후 latest/ 로 배치
    export ANDROID_SDK_ROOT=~/Android
    export PATH=$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/emulator
    sdkmanager --licenses
    # non-Play(=google_apis, NOT google_apis_playstore) 이미지여야 adb root 가능
    sdkmanager "platform-tools" "emulator" "system-images;android-33;google_apis;x86_64"
    avdmanager create avd -n nsm -k "system-images;android-33;google_apis;x86_64" -d pixel_5

## 2. 에뮬레이터 헤드리스 기동
    emulator -avd nsm -no-window -no-audio -gpu swiftshader_indirect -no-snapshot &
    adb wait-for-device
    adb root                              # google_apis 이미지에서 성공해야 함
    adb shell getprop ro.build.version.release

## 3. frida-server 설치 (디바이스 아키텍처 x86_64)
    pip install frida-tools               # 호스트. 버전 메모: frida --version
    # https://github.com/frida/frida/releases 에서 frida-server-<버전>-android-x86_64.xz
    unxz frida-server-*-android-x86_64.xz
    adb push frida-server-*-android-x86_64 /data/local/tmp/frida-server
    adb shell chmod 755 /data/local/tmp/frida-server
    adb shell "/data/local/tmp/frida-server &"
    frida-ps -U | head                    # 디바이스 프로세스 보이면 OK

## 4. 시리즈 앱 설치 + 로그인
    adb install /path/to/네이버시리즈.apk   # 본인이 확보한 APK
    # 앱 실행 후 로그인(2단계 인증 계정은 '애플리케이션 비밀번호' 사용)
    adb shell monkey -p com.nhn.android.nbooks 1   # 앱 시작(패키지명 확인 필요)
    # 패키지명 확인:
    adb shell pm list packages | grep -i -E 'nhn|series|book'

## 5. 관찰 실행 + 회차 열기
    # 터미널 A: 관찰 시작 (패키지명은 4에서 확인한 값)
    python recon/observe.py --package com.nhn.android.nbooks
    # 터미널 B 또는 화면: 앱에서 본인 라이센스 보유(또는 무료) 회차 1편 진입
    # → 터미널 A 에 [BODY!] 로그가 뜨고 recon/out/cap_*.txt 가 본문이면 = A(후킹) go

## 6. 후킹이 본문을 못 잡으면 폴백
    # 회차를 화면에 띄운 상태에서:
    python recon/memscan.py --package com.nhn.android.nbooks
    # recon/out/mem_*.txt 에 본문이 나오면 = B(메모리 스캔) go

## 7. 결과 기록
    docs/FINDINGS-m1.md 의 표를 채운다.
```

- [ ] **Step 2: 커밋**

```bash
git add docs/RUNBOOK-m1.md
git commit -m "docs: M1 리눅스 정찰 런북 (KVM/AVD/frida/관찰 절차)"
```

---

## Task 6: go/no-go 보고서 템플릿 [DEV 작성 / LINUX-RUNTIME 채움]

**Files:**
- Create: `docs/FINDINGS-m1.md`

- [ ] **Step 1: FINDINGS-m1.md 작성**

Create `docs/FINDINGS-m1.md`:
```markdown
# M1 정찰 결과 / go-no-go

작성일: ____   /   앱 버전: ____   /   디바이스: AVD android-33 x86_64 google_apis

## 1. 환경 체크
- [ ] /dev/kvm 사용 가능
- [ ] AVD non-Play 이미지에서 `adb root` 성공
- [ ] frida-server 기동 + `frida-ps -U` 정상
- [ ] 시리즈 APK 설치 + 로그인 성공
- [ ] 루팅/에뮬 탐지로 막힘? (예/아니오 + 증상)

## 2. 패키지/구조
- 패키지명: ____
- 로드된 네이티브 라이브러리(dlopen/loadLibrary 로그 중 의심): ____
- 본문 뷰어가 WebView인가 네이티브인가 (관찰 근거): ____

## 3. 캡처 결과 (recon/out)
| 출처(source) | hangul | has_html | 본문? | 비고 |
|---|---|---|---|---|
| WebView.loadDataWithBaseURL |  |  |  |  |
| WebView.evaluateJavascript |  |  |  |  |
| TextView.setText |  |  |  |  |
| memscan(<html>) |  |  |  |  |

## 4. 판정
- [ ] **go (A)**: 후킹 한 지점에서 회차 본문 XHTML/텍스트 결정적 캡처 → 후킹 지점: ____
- [ ] **부분 go (B)**: 메모리 스캔에서 본문 `<html>` 확보
- [ ] **no-go**: 평문이 메모리에도 없음 → C(접근성/OCR) 검토 또는 중단

## 5. 다음 단계 메모 (M2 계획 입력)
- 확정 메커니즘: ____
- 안정적 캡처를 위해 필요한 대기/네비 조건: ____
- 우회 필요했던 보호(루트탐지 등): ____
```

- [ ] **Step 2: 커밋**

```bash
git add docs/FINDINGS-m1.md
git commit -m "docs: M1 go/no-go 보고서 템플릿"
```

---

## Self-Review

**1. Spec coverage (설계 문서 대비):**
- §5 정찰 스파이크 1~4단계 → Task 2/3/4(하니스) + Task 5(런북) + Task 6(보고서)로 커버.
- §5 go/no-go 기준 → Task 6 §4 판정표.
- §4③ HTML→텍스트/한국어필터 이식 → Task 1.
- §6 AVD-first 런타임 → Task 5 런북(google_apis non-Play, `adb root`, `-no-window`).
- §10 리스크(루트탐지) → Task 6 §1/§5 기록 항목.
- M2~M5는 본 계획 범위 밖(M1 결과 의존) — 의도된 스코프 분리.

**2. Placeholder scan:** 코드 단계는 전부 실제 내용. 보고서/런북의 `____` 빈칸은 *런타임에 사람이 채우는 산출물 필드*이지 계획의 미완성이 아님(의도적).

**3. Type/이름 일관성:** `classify_capture`가 반환하는 키(`korean`, `has_html`, `probably_body`, `preview`)를 Task 1에서 정의하고 Task 3/4에서 동일하게 사용. `html_to_text`/`count_korean` 시그니처 일관. 패키지 import 경로 `nsm.textutil` 일관.

---

## 비고 (실행 현실)
- Task 0~1, 그리고 2~6의 "작성/파싱검증" 단계는 이 세션(또는 어디서나)에서 자동 실행·테스트 가능.
- Task 2~6의 `[LINUX-RUNTIME]` 검증/사용 단계(에뮬레이터·frida·실기 관찰)는 **리눅스+KVM 호스트에서 사람이** 수행한다. 자동 에이전트가 대신할 수 없는 탐사다.
- M1 종료 조건: `docs/FINDINGS-m1.md` §4 판정 완료. 이후 그 결과로 M2(최소 추출 PoC) 계획을 새로 작성한다.
