/**
 * PWA インストール診断モジュール
 * Android Chrome の「ホーム画面に追加」が出ない原因をリアルタイムで診断・表示する
 *
 * 使い方:
 *   <script type="module" src="/js/pwa-diagnostics.js"></script>
 *   または import '/js/pwa-diagnostics.js';
 *
 * 画面右下に折りたたみ可能な診断パネルが表示される
 */

(() => {
  // ──────────────────────────────────────────────
  // 診断結果ストア
  // ──────────────────────────────────────────────
  const checks = [
    { id: 'https',        label: 'HTTPS または localhost',        status: 'pending', detail: '' },
    { id: 'manifest',     label: 'manifest.json 読み込み成功',    status: 'pending', detail: '' },
    { id: 'manifest_name',label: 'manifest: name フィールド',     status: 'pending', detail: '' },
    { id: 'manifest_start',label:'manifest: start_url フィールド',status: 'pending', detail: '' },
    { id: 'manifest_display',label:'manifest: display=standalone/fullscreen/minimal-ui', status: 'pending', detail: '' },
    { id: 'manifest_icon192', label: 'manifest: アイコン 192px 存在', status: 'pending', detail: '' },
    { id: 'manifest_icon512', label: 'manifest: アイコン 512px 存在', status: 'pending', detail: '' },
    { id: 'manifest_icon_purpose', label: 'manifest: アイコンに purpose 設定', status: 'pending', detail: '' },
    { id: 'sw_supported', label: 'Service Worker API サポート',   status: 'pending', detail: '' },
    { id: 'sw_registered',label: 'Service Worker 登録成功',       status: 'pending', detail: '' },
    { id: 'sw_active',    label: 'Service Worker アクティブ',     status: 'pending', detail: '' },
    { id: 'beforeinstall',label: 'beforeinstallprompt イベント受信', status: 'pending', detail: '（ユーザー操作・訪問回数などChrome内部条件依存）' },
  ];

  let deferredPrompt = null;
  let panelEl = null;
  let listEl = null;

  // ──────────────────────────────────────────────
  // UI 構築
  // ──────────────────────────────────────────────
  function buildPanel() {
    const style = document.createElement('style');
    style.textContent = `
      #pwa-diag-toggle {
        position: fixed; bottom: 16px; right: 16px; z-index: 99999;
        background: #1976d2; color: #fff; border: none; border-radius: 50%;
        width: 48px; height: 48px; font-size: 22px; cursor: pointer;
        box-shadow: 0 2px 8px rgba(0,0,0,0.35);
        display: flex; align-items: center; justify-content: center;
      }
      #pwa-diag-panel {
        position: fixed; bottom: 72px; right: 16px; z-index: 99998;
        background: #fff; border-radius: 10px; width: 340px; max-height: 75vh;
        overflow-y: auto; box-shadow: 0 4px 24px rgba(0,0,0,0.25);
        font-family: -apple-system, sans-serif; font-size: 13px; color: #212121;
        display: none;
      }
      #pwa-diag-panel.open { display: block; }
      #pwa-diag-header {
        background: #1976d2; color: #fff; padding: 10px 14px;
        border-radius: 10px 10px 0 0; font-weight: 700; font-size: 14px;
        display: flex; justify-content: space-between; align-items: center;
        position: sticky; top: 0; z-index: 1;
      }
      #pwa-diag-header span { font-size: 11px; font-weight: 400; opacity: 0.85; }
      #pwa-diag-list { padding: 8px 0; }
      .pwa-diag-item {
        display: flex; align-items: flex-start; gap: 8px;
        padding: 7px 14px; border-bottom: 1px solid #f0f0f0;
        transition: background 0.2s;
      }
      .pwa-diag-item:last-child { border-bottom: none; }
      .pwa-diag-icon { font-size: 16px; min-width: 20px; text-align: center; line-height: 1.4; }
      .pwa-diag-text { flex: 1; }
      .pwa-diag-label { font-weight: 600; line-height: 1.4; }
      .pwa-diag-detail { font-size: 11px; color: #666; margin-top: 2px; word-break: break-all; }
      .pwa-diag-item.ok    .pwa-diag-icon::before { content: "✅"; }
      .pwa-diag-item.ng    .pwa-diag-icon::before { content: "❌"; }
      .pwa-diag-item.warn  .pwa-diag-icon::before { content: "⚠️"; }
      .pwa-diag-item.pending .pwa-diag-icon::before { content: "⏳"; }
      #pwa-diag-install-btn {
        display: block; width: calc(100% - 28px); margin: 10px 14px;
        padding: 10px; background: #2e7d32; color: #fff; border: none;
        border-radius: 6px; font-size: 14px; font-weight: 700; cursor: pointer;
        display: none;
      }
      #pwa-diag-install-btn.visible { display: block; }
      #pwa-diag-summary {
        padding: 8px 14px 4px; font-size: 12px;
        background: #f9f9f9; border-radius: 0 0 10px 10px;
      }
    `;
    document.head.appendChild(style);

    // FABボタン
    const fab = document.createElement('button');
    fab.id = 'pwa-diag-toggle';
    fab.title = 'PWA診断';
    fab.innerHTML = '🔍';
    fab.addEventListener('click', togglePanel);
    document.body.appendChild(fab);

    // パネル本体
    panelEl = document.createElement('div');
    panelEl.id = 'pwa-diag-panel';
    panelEl.innerHTML = `
      <div id="pwa-diag-header">
        PWA インストール診断
        <span id="pwa-diag-ts"></span>
      </div>
      <div id="pwa-diag-list"></div>
      <button id="pwa-diag-install-btn">📲 今すぐインストール</button>
      <div id="pwa-diag-summary"></div>
    `;
    document.body.appendChild(panelEl);

    listEl = document.getElementById('pwa-diag-list');

    document.getElementById('pwa-diag-install-btn').addEventListener('click', () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choice) => {
          setCheck('beforeinstall',
            choice.outcome === 'accepted' ? 'ok' : 'warn',
            `ユーザー選択: ${choice.outcome}`
          );
          deferredPrompt = null;
          document.getElementById('pwa-diag-install-btn').classList.remove('visible');
        });
      }
    });

    renderAll();
  }

  function togglePanel() {
    panelEl.classList.toggle('open');
    if (panelEl.classList.contains('open')) {
      document.getElementById('pwa-diag-ts').textContent =
        new Date().toLocaleTimeString('ja-JP');
    }
  }

  function renderAll() {
    if (!listEl) return;
    listEl.innerHTML = '';
    checks.forEach((c) => {
      const item = document.createElement('div');
      item.className = `pwa-diag-item ${c.status}`;
      item.id = `pwa-diag-item-${c.id}`;
      item.innerHTML = `
        <div class="pwa-diag-icon"></div>
        <div class="pwa-diag-text">
          <div class="pwa-diag-label">${c.label}</div>
          ${c.detail ? `<div class="pwa-diag-detail">${escHtml(c.detail)}</div>` : ''}
        </div>`;
      listEl.appendChild(item);
    });
    updateSummary();
  }

  function setCheck(id, status, detail = '') {
    const c = checks.find((x) => x.id === id);
    if (!c) return;
    c.status = status;
    c.detail = detail;
    const item = document.getElementById(`pwa-diag-item-${id}`);
    if (item) {
      item.className = `pwa-diag-item ${status}`;
      const labelEl = item.querySelector('.pwa-diag-label');
      if (labelEl) labelEl.textContent = c.label;
      let detailEl = item.querySelector('.pwa-diag-detail');
      if (detail) {
        if (!detailEl) {
          detailEl = document.createElement('div');
          detailEl.className = 'pwa-diag-detail';
          item.querySelector('.pwa-diag-text').appendChild(detailEl);
        }
        detailEl.textContent = detail;
      } else if (detailEl) {
        detailEl.remove();
      }
    }
    updateSummary();
  }

  function updateSummary() {
    const el = document.getElementById('pwa-diag-summary');
    if (!el) return;
    const ng = checks.filter((c) => c.status === 'ng').length;
    const ok = checks.filter((c) => c.status === 'ok').length;
    const warn = checks.filter((c) => c.status === 'warn').length;
    const total = checks.length;
    if (ng === 0 && ok + warn === total) {
      el.innerHTML = '<span style="color:#2e7d32;font-weight:700">🎉 すべての条件をクリア！インストール可能です</span>';
    } else if (ng > 0) {
      el.innerHTML = `<span style="color:#c62828;font-weight:700">❌ ${ng}件の問題があります（OK:${ok} / NG:${ng} / WARN:${warn}）</span>`;
    } else {
      el.innerHTML = `<span style="color:#888">⏳ 診断中... (OK:${ok} / ${total})</span>`;
    }
  }

  function escHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ──────────────────────────────────────────────
  // 診断ロジック
  // ──────────────────────────────────────────────

  // 1. HTTPS / localhost
  function checkHttps() {
    const proto = location.protocol;
    const host = location.hostname;
    if (proto === 'https:' || host === 'localhost' || host === '127.0.0.1') {
      setCheck('https', 'ok', `${proto}//${host}`);
    } else {
      setCheck('https', 'ng', `現在: ${proto}//${host}  → HTTPSが必須です`);
    }
  }

  // 2. manifest.json の読み込みと各フィールド検証
  async function checkManifest() {
    const linkEl = document.querySelector('link[rel="manifest"]');
    if (!linkEl) {
      setCheck('manifest', 'ng', '<link rel="manifest"> タグが見つかりません');
      ['manifest_name','manifest_start','manifest_display','manifest_icon192','manifest_icon512','manifest_icon_purpose'].forEach(
        (id) => setCheck(id, 'ng', 'manifest未読み込みのため確認不可')
      );
      return;
    }

    const href = linkEl.getAttribute('href');
    let manifest;
    try {
      const res = await fetch(href, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      manifest = await res.json();
      setCheck('manifest', 'ok', `取得成功: ${href}`);
    } catch (e) {
      setCheck('manifest', 'ng', `取得失敗: ${e.message}`);
      ['manifest_name','manifest_start','manifest_display','manifest_icon192','manifest_icon512','manifest_icon_purpose'].forEach(
        (id) => setCheck(id, 'ng', 'manifest取得失敗のため確認不可')
      );
      return;
    }

    // name
    if (manifest.name && manifest.name.trim()) {
      setCheck('manifest_name', 'ok', `"${manifest.name}"`);
    } else {
      setCheck('manifest_name', 'ng', 'name フィールドが空またはありません');
    }

    // start_url
    if (manifest.start_url) {
      setCheck('manifest_start', 'ok', `"${manifest.start_url}"`);
    } else {
      setCheck('manifest_start', 'ng', 'start_url フィールドがありません');
    }

    // display
    const validDisplays = ['standalone','fullscreen','minimal-ui'];
    if (validDisplays.includes(manifest.display)) {
      setCheck('manifest_display', 'ok', `display="${manifest.display}"`);
    } else {
      setCheck('manifest_display', 'ng',
        `display="${manifest.display}" → standalone/fullscreen/minimal-ui のいずれかが必要`);
    }

    // icons
    const icons = manifest.icons || [];
    const icon192 = icons.find((i) => i.sizes && i.sizes.includes('192'));
    const icon512 = icons.find((i) => i.sizes && i.sizes.includes('512'));

    if (icon192) {
      // 実際にfetchして存在確認
      try {
        const r = await fetch(icon192.src, { method: 'HEAD', cache: 'no-store' });
        if (r.ok) {
          setCheck('manifest_icon192', 'ok', `${icon192.src} (${r.status})`);
        } else {
          setCheck('manifest_icon192', 'ng', `ファイルが見つかりません: ${icon192.src} → HTTP ${r.status}`);
        }
      } catch (e) {
        setCheck('manifest_icon192', 'ng', `取得エラー: ${icon192.src} → ${e.message}`);
      }
    } else {
      setCheck('manifest_icon192', 'ng', '192x192 アイコンが manifest に未登録');
    }

    if (icon512) {
      try {
        const r = await fetch(icon512.src, { method: 'HEAD', cache: 'no-store' });
        if (r.ok) {
          setCheck('manifest_icon512', 'ok', `${icon512.src} (${r.status})`);
        } else {
          setCheck('manifest_icon512', 'ng', `ファイルが見つかりません: ${icon512.src} → HTTP ${r.status}`);
        }
      } catch (e) {
        setCheck('manifest_icon512', 'ng', `取得エラー: ${icon512.src} → ${e.message}`);
      }
    } else {
      setCheck('manifest_icon512', 'ng', '512x512 アイコンが manifest に未登録');
    }

    // purpose
    const hasPurpose = icons.some((i) => i.purpose);
    if (hasPurpose) {
      const purposes = icons.map((i) => `${i.sizes}:${i.purpose||'(none)'}`).join(', ');
      setCheck('manifest_icon_purpose', 'ok', purposes);
    } else {
      setCheck('manifest_icon_purpose', 'warn',
        'purpose 未設定。Android Chrome では "any maskable" 推奨。インストール可能だがアイコン表示に影響する場合あり');
    }
  }

  // 3. Service Worker
  async function checkServiceWorker() {
    if (!('serviceWorker' in navigator)) {
      setCheck('sw_supported', 'ng', 'このブラウザは Service Worker 非対応です');
      setCheck('sw_registered', 'ng', 'SW未対応のため確認不可');
      setCheck('sw_active', 'ng', 'SW未対応のため確認不可');
      return;
    }
    setCheck('sw_supported', 'ok', 'Service Worker API 利用可能');

    try {
      const reg = await navigator.serviceWorker.getRegistration('/');
      if (reg) {
        setCheck('sw_registered', 'ok', `scope: ${reg.scope}`);
        const sw = reg.active || reg.installing || reg.waiting;
        if (reg.active) {
          setCheck('sw_active', 'ok', `state: active  scriptURL: ${reg.active.scriptURL}`);
        } else if (reg.installing) {
          setCheck('sw_active', 'warn', `state: installing（まだアクティブではありません）`);
          reg.installing.addEventListener('statechange', function() {
            if (this.state === 'activated') {
              setCheck('sw_active', 'ok', `state: activated`);
            }
          });
        } else if (reg.waiting) {
          setCheck('sw_active', 'warn', `state: waiting（ページをリロードするとアクティブになります）`);
        }
      } else {
        // まだ登録されていない可能性 → 全スコープを確認
        const regs = await navigator.serviceWorker.getRegistrations();
        if (regs.length > 0) {
          const scopes = regs.map((r) => r.scope).join(', ');
          setCheck('sw_registered', 'warn', `別スコープで登録済み: ${scopes}`);
          const anyActive = regs.find((r) => r.active);
          if (anyActive) {
            setCheck('sw_active', 'ok', `active: ${anyActive.active.scriptURL}`);
          } else {
            setCheck('sw_active', 'warn', 'アクティブなSWなし（インストール中の可能性）');
          }
        } else {
          setCheck('sw_registered', 'ng', 'Service Worker が未登録です。app.js の読み込みを確認してください');
          setCheck('sw_active', 'ng', 'SW未登録');
        }
      }
    } catch (e) {
      setCheck('sw_registered', 'ng', `getRegistration エラー: ${e.message}`);
      setCheck('sw_active', 'ng', 'エラーのため確認不可');
    }
  }

  // 4. beforeinstallprompt (インストールプロンプト)
  function listenInstallPrompt() {
    // すでにインストール済みかチェック
    if (window.matchMedia('(display-mode: standalone)').matches ||
        navigator.standalone === true) {
      setCheck('beforeinstall', 'ok', '既にスタンドアロンモードで動作中（インストール済み）');
      return;
    }

    setCheck('beforeinstall', 'pending',
      '待機中... Chrome が内部条件（訪問回数・エンゲージメント等）を満たすと発火します');

    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      setCheck('beforeinstall', 'ok',
        'インストールプロンプト受信！「今すぐインストール」ボタンを押せます');
      const btn = document.getElementById('pwa-diag-install-btn');
      if (btn) btn.classList.add('visible');
      // パネルを自動的に開く
      if (panelEl && !panelEl.classList.contains('open')) {
        panelEl.classList.add('open');
      }
    });

    window.addEventListener('appinstalled', () => {
      setCheck('beforeinstall', 'ok', '✅ アプリがホーム画面にインストールされました！');
      deferredPrompt = null;
    });
  }

  // ──────────────────────────────────────────────
  // メイン実行
  // ──────────────────────────────────────────────
  function run() {
    buildPanel();

    // beforeinstallprompt は早めに登録（load前に来ることがある）
    listenInstallPrompt();

    checkHttps();

    // manifest & SW は非同期
    checkManifest().catch((e) => {
      setCheck('manifest', 'ng', `診断エラー: ${e.message}`);
    });

    checkServiceWorker().catch((e) => {
      setCheck('sw_registered', 'ng', `診断エラー: ${e.message}`);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
