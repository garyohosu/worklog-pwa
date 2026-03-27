// アプリ初期化、SW登録
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js')
      .then((reg) => {
        console.log('[app.js] Service Worker registered:', reg.scope);
        // 診断モジュールがロード済みなら SW 登録後に再チェックを促す
        reg.addEventListener('updatefound', () => {
          console.log('[app.js] SW update found');
        });
      })
      .catch((err) => {
        console.error('[app.js] Service Worker registration failed:', err);
      });
  });
}
