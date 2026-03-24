# SPEC.md

# 1. 概要

## 1.1 プロジェクト名
worklog-pwa

## 1.2 アプリ概要
GitHub Pages 上で配信する PWA として動作する、スマホ向けの作業メモ・点検記録アプリを構築する。  
フロントエンドは GitHub Pages 上の静的サイトとして公開し、バックエンドは Sakura レンタルサーバー上の CGI API と SQLite を利用する。  
現場での点検、修理、保守、作業報告をスマホで簡単に記録し、オフライン時でも下書き保存と後同期を可能にする。

## 1.3 目的
- スマホからその場で記録できること
- 点検・修理・保守の履歴を一元管理すること
- オフラインでも入力を継続できること
- QR コードによる設備呼び出しを可能にすること
- ユーザー登録・ログイン付きの実用サービスとして成立させること
- Google AdSense を組み込み、公開サイトとして収益化可能にすること

---

# 2. システム構成

## 2.1 全体構成
- フロントエンド: GitHub Pages
- 配信形式: PWA
- ローカル保存: IndexedDB
- オフライン対応: Service Worker
- バックエンド: Sakura レンタルサーバー CGI
- データベース: SQLite
- 広告: Google AdSense

## 2.2 役割分担

### GitHub Pages 側
- ログイン画面
- 新規登録画面
- ホーム画面
- 記録一覧
- 記録詳細
- 記録編集
- 同期管理
- マイページ
- プライバシーポリシー
- お問い合わせ
- AdSense 表示
- PWA / キャッシュ / オフライン UI
- カメラ / QR スキャン UI

### Sakura CGI 側
- register.cgi
- login.cgi
- logout.cgi
- session_check.cgi
- change_password.cgi
- worklog_api.cgi
- equipment_api.cgi
- upload.cgi（将来または拡張）
- SQLite データ保存

---

# 3. 必須要件

## 3.1 機能要件
以下を必須とする。

1. ID / パスワードによる新規ユーザー登録
2. ID / パスワードによるログイン
3. ログアウト
4. パスワード変更
5. ログイン済みユーザーのみ作業記録を利用可能
6. 作業記録の新規作成
7. 作業記録の一覧表示
8. 作業記録の詳細表示
9. 作業記録の編集
10. 作業記録の状態変更
11. 設備マスタ参照
12. QR コードで設備呼び出し
13. カメラ利用
14. オフライン下書き保存
15. 通信復帰後の同期
16. Google AdSense 表示
17. privacy-policy / contact ページ配置

## 3.2 非機能要件
- HTTPS 前提
- スマホ表示に最適化
- PWA としてホーム画面追加可能
- キャッシュで最低限のオフライン利用が可能
- パスワード平文保存禁止
- ユーザーごとにアクセス制御
- 管理者権限を分離
- API は許可オリジンのみ受け入れる

---

# 4. ユーザー種別

## 4.1 user
- 自分の記録の作成
- 自分の記録の参照
- 自分の記録の編集
- 設備参照
- QR 読取
- 同期実行

## 4.2 admin
- 全記録参照
- 設備マスタ編集
- ユーザー管理
- 集計確認
- 必要な運用設定変更

---

# 5. データ設計

## 5.1 users
ユーザー情報を保持する。

- id: INTEGER PRIMARY KEY
- login_id: TEXT UNIQUE
- password_hash: TEXT
- display_name: TEXT
- email: TEXT
- role: TEXT
- is_active: INTEGER
- created_at: TEXT
- updated_at: TEXT
- last_login_at: TEXT

## 5.2 equipment
設備マスタを保持する。

- id: INTEGER PRIMARY KEY
- equipment_code: TEXT UNIQUE
- equipment_name: TEXT
- location: TEXT
- line_name: TEXT
- model: TEXT
- maker: TEXT
- qr_value: TEXT
- is_active: INTEGER
- created_at: TEXT
- updated_at: TEXT

## 5.3 work_logs
作業・点検・修理記録の本体を保持する。

- id: INTEGER PRIMARY KEY
- log_uuid: TEXT UNIQUE
- user_id: INTEGER
- equipment_id: INTEGER
- record_type: TEXT
- status: TEXT
- title: TEXT
- symptom: TEXT
- work_detail: TEXT
- result: TEXT
- priority: TEXT
- recorded_at: TEXT
- needs_followup: INTEGER
- followup_due: TEXT
- local_updated_at: TEXT
- server_updated_at: TEXT
- sync_state: TEXT
- deleted_flag: INTEGER

### record_type 例
- inspection
- repair
- trouble
- maintenance
- memo

### status 例
- draft
- open
- in_progress
- done
- pending_parts

### sync_state 例
- local_only
- dirty
- synced

## 5.4 work_photos
写真情報を保持する。

- id: INTEGER PRIMARY KEY
- log_uuid: TEXT
- photo_path: TEXT
- caption: TEXT
- taken_at: TEXT
- created_at: TEXT

## 5.5 sessions
ログインセッション管理を行う。

- id: INTEGER PRIMARY KEY
- user_id: INTEGER
- session_token: TEXT
- expires_at: TEXT
- created_at: TEXT
- last_access_at: TEXT

---

# 6. 認証仕様

## 6.1 新規登録
ユーザーは login_id と password を入力して登録できる。

### 入力項目
- login_id
- password
- display_name
- email（任意）

### 制約
- login_id は一意
- password は平文保存禁止
- password_hash のみ DB 保存

## 6.2 ログイン
ユーザーは login_id と password を用いてログインする。

### 成功時
- session_token 発行
- user_id 返却
- display_name 返却

## 6.3 ログアウト
- セッション破棄
- クライアントの保持トークン削除

## 6.4 パスワード変更
- 現在パスワード確認
- 新パスワードへ更新
- 更新後は再ログイン推奨

## 6.5 セッション
- 有効期限を持つ
- API 呼び出し時に送信
- 期限切れ時は再ログイン

---

# 7. 画面仕様

## 7.1 ログイン画面
表示項目
- ログインID
- パスワード
- ログインボタン
- 新規登録リンク

## 7.2 新規登録画面
表示項目
- ログインID
- 表示名
- メール
- パスワード
- パスワード確認
- 登録ボタン

## 7.3 ホーム画面
表示内容
- 今日の記録件数
- 未同期件数
- 状態別件数
- 最近の記録
- 新規記録ボタン
- 同期ボタン
- AdSense 広告枠

## 7.4 一覧画面
検索条件
- 設備名
- 設備コード
- ライン
- 日付
- 種別
- 状態

表示項目
- タイトル
- 設備名
- 日時
- 状態
- 写真有無
- 同期状態
- AdSense 広告枠

## 7.5 詳細画面
表示項目
- 基本情報
- 症状
- 作業内容
- 結果
- 写真
- 更新履歴
- AdSense 広告枠

## 7.6 新規作成 / 編集画面
入力項目
- 種別
- 設備
- タイトル
- 症状
- 作業内容
- 結果
- 状態
- 要フォロー
- 期限
- 写真
- QR 読取ボタン

### 備考
- 入力画面では広告非表示または最小化する
- 入力操作の妨げにならないこと

## 7.7 設備選択画面
- 設備検索
- 最近使った設備
- QR 読取による自動選択

## 7.8 同期管理画面
- 未同期一覧
- 同期成功件数
- 同期失敗件数
- 再送

## 7.9 マイページ
- 表示名
- ログインID
- パスワード変更
- ログアウト

## 7.10 固定ページ
- /privacy-policy/
- /contact/
- /terms/（推奨）
- /about/（推奨）

---

# 8. 操作フロー

## 8.1 新規記録作成
1. 新規記録を開く
2. 設備を選択する、または QR 読取する
3. 内容を入力する
4. ローカルに保存する
5. オンライン時はサーバー同期する
6. オフライン時は未同期として保持する

## 8.2 QR 読取
1. カメラを起動する
2. QR を読み取る
3. equipment.qr_value と照合する
4. 一致した設備を自動選択する
5. 未登録なら候補表示する

## 8.3 同期
1. local_only / dirty レコードを抽出する
2. API へ順次送信する
3. 成功時は synced に変更する
4. 失敗時はエラーを保持する

---

# 9. オフライン仕様

## 9.1 ローカル保存
IndexedDB に以下を保存する。
- 下書き
- 未同期記録
- 最近使用設備
- 設備マスタキャッシュ
- セッション関連の必要最小情報

## 9.2 同期方式
- 新規記録は log_uuid をクライアントで発行
- ローカル変更は dirty とする
- サーバー反映後に synced とする

## 9.3 競合ルール
初期版は最後の保存を優先する。  
将来、複数人編集に対応する場合は競合検知を導入する。

---

# 10. カメラ・写真・QR仕様

## 10.1 カメラ
- スマホカメラを起動できること
- 写真撮影または画像取得ができること
- 撮影後にプレビュー表示できること

## 10.2 写真保存
初期版では以下のどちらかで対応する。

### 案A
- 画像本体はローカルに保持
- DB には本文のみ保存

### 案B
- Sakura 側 upload.cgi を追加
- DB には photo_path を保存

推奨は案B。  
MVPでは写真なしでも成立するが、1枚対応を優先候補とする。

## 10.3 QR
- QR から設備呼び出し
- 対応ブラウザでは BarcodeDetector を優先
- 非対応ブラウザではライブラリで代替
- 必要に応じ画像アップロード読取も検討

---

# 11. API仕様

## 11.1 認証系 API
- register.cgi
- login.cgi
- logout.cgi
- session_check.cgi
- change_password.cgi

## 11.2 業務系 API
- worklog_api.cgi
- equipment_api.cgi
- upload.cgi（将来または拡張）

## 11.3 worklog_api.cgi 想定機能
- 記録一覧取得
- 記録詳細取得
- 新規登録
- 更新
- 状態変更
- 同期

## 11.4 equipment_api.cgi 想定機能
- 設備一覧取得
- 設備検索
- QR 値検索
- 管理者による設備登録 / 更新

---

# 12. セキュリティ要件

以下を必須とする。

- パスワード平文保存禁止
- password_hash のみ保存
- 認証なし更新禁止
- 他人の記録を勝手に取得不可
- セッション期限あり
- HTTPS 利用
- CORS は許可オリジン限定
- 管理機能は role チェック必須
- 入力値バリデーション実施
- SQL 注入対策実施
- ログイン試行に制限を設けることが望ましい

---

# 13. AdSense 要件

## 13.1 必須
Google AdSense を必須とする。

## 13.2 広告表示ページ
- ホーム画面
- 一覧画面
- 詳細画面

## 13.3 広告を避けるページ
- ログイン画面
- 新規登録画面
- 作業入力画面中央
- QR 読取中
- カメラ撮影中

## 13.4 必須関連ページ
- /privacy-policy/
- /contact/

## 13.5 表示方針
- レスポンシブ広告を基本とする
- 操作妨害にならない位置に配置する
- モバイル表示で過度に占有しないこと

---

# 14. フォルダ構成案

## 14.1 GitHub Pages 側
```text
worklog-pwa/
  index.html
  manifest.json
  service-worker.js
  assets/
  js/
    app.js
    auth.js
    api.js
    db-local.js
    qr.js
    camera.js
    sync.js
  pages/
    login.html
    register.html
    list.html
    edit.html
    detail.html
    sync.html
    mypage.html
  privacy-policy/
    index.html
  contact/
    index.html
```

## 14.2 Sakura CGI 側
```text
cgi/
  api/
    register.cgi
    login.cgi
    logout.cgi
    session_check.cgi
    change_password.cgi
    worklog_api.cgi
    equipment_api.cgi
    upload.cgi
  data/
    inspection_app.db
```

---

# 15. 開発フェーズ

## Phase 1
- 画面作成
- ローカル保存
- PWA 化
- AdSense 埋め込み
- 固定ページ作成

## Phase 2
- ユーザー登録
- ログイン
- セッション管理
- 権限制御

## Phase 3
- 作業記録 CRUD
- 設備マスタ参照
- 一覧検索

## Phase 4
- オフライン同期
- 未同期キュー
- 状態管理

## Phase 5
- QR 読取
- カメラ対応
- 写真添付

## Phase 6
- 管理者機能
- 設備編集
- 監査用改善
- 運用調整

---

# 16. MVP 完成条件

以下を満たした時点で MVP 完成とする。

1. ユーザー登録できる
2. ID / パスワードでログインできる
3. ログイン後のみ利用できる
4. 設備を選んで記録を登録できる
5. 自分の記録一覧を見られる
6. 詳細表示できる
7. 編集できる
8. オフラインで下書きできる
9. 同期できる
10. QR で設備を呼び出せる
11. AdSense がホーム・一覧・詳細に入る
12. privacy-policy / contact が存在する

---

# 17. 今後の拡張候補

- 写真複数枚対応
- CSV 出力
- PDF 出力
- 集計ダッシュボード
- 設備ごとの故障傾向分析
- 通知機能
- パスワード再発行
- メール通知
- Android TWA 化
- Play 配布対応

---

# 18. リポジトリ名

推奨リポジトリ名:
- worklog-pwa

候補:
- inspection-pwa
- fieldlog-pwa
- genba-note

本仕様では `worklog-pwa` を正式候補とする。
