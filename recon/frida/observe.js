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
