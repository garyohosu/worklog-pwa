# SPEC.md

# 1. 概要

## 1.1 プロジェクト名
worklog-pwa

## 1.2 アプリ概要
GitHub Pages 上で配信する PWA として動作する、スマホ向けの作業メモ・点検記録アプリを構築する。
フロントエンドは GitHub Pages 上の静的サイトとして公開し、バックエンドは Sakura レンタルサーバー上の Python CGI と SQLite を利用する。
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
- バックエンド: Sakura レンタルサーバー CGI（**Python CGI**）
- データベース: SQLite
- 広告: Google AdSense

## 2.2 CGI 実装言語
Python を使用する。
ハッシュ処理・JSON API・SQLite 操作・将来の画像アップロードや認証拡張まで扱いやすいため。
将来 FastCGI 化は検討可。

## 2.3 役割分担

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
- 利用規約
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
- upload.cgi（Phase 5 以降）
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
7. 作業記録の一覧表示（50件ページネーション）
8. 作業記録の詳細表示
9. 作業記録の編集
10. 作業記録の状態変更
11. 作業記録の論理削除
12. 設備マスタ参照
13. QR コードで設備呼び出し
14. カメラ利用（Phase 5）
15. オフライン下書き保存
16. 通信復帰後の同期（プル同期含む）
17. ログイン試行制限（5回失敗で15分ロック）
18. Google AdSense 表示
19. privacy-policy / contact / terms ページ配置

## 3.2 非機能要件
- HTTPS 前提
- スマホ表示に最適化
- PWA としてホーム画面追加可能
- キャッシュで最低限のオフライン利用が可能
- パスワード平文保存禁止（bcrypt ハッシュのみ保存）
- ユーザーごとにアクセス制御
- 管理者権限を分離
- API は許可オリジンのみ受け入れる（CORS）
- API レスポンスは JSON 統一

---

# 4. ユーザー種別

## 4.1 user
- 自分の記録の作成
- 自分の記録の参照
- 自分の記録の編集
- 自分の記録の論理削除
- 設備参照
- QR 読取
- 同期実行

## 4.2 admin
- 全記録参照（deleted_flag=1 含む）
- 設備マスタ編集
- ユーザー管理
- 集計確認
- 必要な運用設定変更

### admin 初期登録
MVP では専用管理画面は作らず、DB 直接投入で初期 admin を 1 件作る。
手順:
1. users テーブル作成
2. bcrypt ハッシュ済みパスワード生成
3. `role=admin` のユーザーを DB に直接投入

---

# 5. データ設計

## 5.1 users
ユーザー情報を保持する。

- id: INTEGER PRIMARY KEY
- login_id: TEXT UNIQUE
- password_hash: TEXT（bcrypt ハッシュ）
- display_name: TEXT
- email: TEXT
- role: TEXT（user / admin）
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
- qr_value: TEXT（設備コード文字列。例: `MC-001`）
- is_active: INTEGER
- created_at: TEXT
- updated_at: TEXT

### 設備マスタ初期データ
初期は CSV 一括投入を想定する。MVP では管理者が変換スクリプトまたは直接投入で登録する。
MVP 後に `equipment_import.cgi` を追加する余地を残す。

## 5.3 work_logs
作業・点検・修理記録の本体を保持する。

- id: INTEGER PRIMARY KEY
- log_uuid: TEXT UNIQUE
- user_id: INTEGER（所有ユーザー）
- equipment_id: INTEGER（**NULL 許可**。`record_type=memo` など設備なし記録に対応）
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
- local_updated_at: TEXT（ローカル表示用の参考時刻。競合判定には使わない）
- server_updated_at: TEXT（サーバー保存日時。UTC の ISO 8601）
- revision: INTEGER NOT NULL DEFAULT 1（競合判定の唯一の基準）
- sync_state: TEXT
- created_by: INTEGER
- updated_by: INTEGER
- deleted_flag: INTEGER（論理削除。1=削除済み）
- deleted_at: TEXT
- deleted_by: INTEGER

### record_type 固定値
- inspection
- repair（修理作業の記録）
- trouble（不具合・異常の記録。修理完了まで同一レコードで status を更新する運用を基本とする）
- maintenance
- memo（設備なし記録の代表例）

### status 固定値
- draft
- open
- in_progress
- done
- pending_parts

### sync_state 固定値
- local_only
- dirty
- synced
- failed
- conflict

### work_logs 補足
- `user_id` は記録の所有者を表す
- `created_by` / `updated_by` / `deleted_by` は操作ユーザーを表す
- 競合判定は `revision` のみで行う
- `local_updated_at` は UI 表示用の参考値であり、更新可否の判定には使わない
- `server_updated_at` と `deleted_at` は UTC の ISO 8601 で保持する

## 5.4 work_photos
写真情報を保持する。**MVP では利用しないが、テーブルは先に作成する。**

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
- expires_at: TEXT（有効期限: 発行から 7日）
- created_at: TEXT
- last_access_at: TEXT

## 5.6 login_attempts
ログイン試行制限に使用する。

- id: INTEGER PRIMARY KEY
- login_id: TEXT
- ip_address: TEXT
- attempted_at: TEXT
- success: INTEGER

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
- password_hash（bcrypt）のみ DB 保存

## 6.2 ログイン
ユーザーは login_id と password を用いてログインする。

### 成功時
- session_token 発行（有効期限: 7日）
- user_id 返却
- display_name 返却

### ログイン試行制限
- 5回連続失敗で一時ロック（15分）
- `login_id` 単位 + IP 単位で制限
- `login_attempts` テーブルで管理

## 6.3 ログアウト
- セッション破棄
- クライアントの保持トークン削除

## 6.4 パスワード変更
- 現在パスワード確認
- 新パスワードへ更新
- 更新後は再ログイン推奨

## 6.5 セッション
- 有効期限: 7日
- API 呼び出し時に `Authorization: Bearer <token>` ヘッダーで送信
- Cookie は使用しない（別オリジン構成のため）
- 期限切れ時は再ログイン
- オフライン中は下書き作成・編集を継続可能とする
- 再オンライン時は `session_check.cgi` を行い、期限切れなら再ログイン成功後に未同期データを送信する

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
- フォローアップ期限切れ件数
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
- フォローアップ期限切れ表示（色分けまたはアイコン）
- AdSense 広告枠

ページネーション: 1ページ50件

## 7.5 詳細画面
表示項目
- 基本情報
- 症状
- 作業内容
- 結果
- フォローアップ期限（超過時は視覚表示）
- 写真（Phase 5 以降）
- 更新情報（作成日時 / 最終更新日時 / 同期日時 / 更新者）
- AdSense 広告枠

## 7.6 新規作成 / 編集画面
入力項目
- 種別
- 設備（「設備なし」選択可）
- タイトル
- 症状
- 作業内容
- 結果
- 状態
- 要フォロー
- 期限
- 写真（Phase 5 以降）
- QR 読取ボタン

### 備考
- 入力画面では広告非表示または最小化する
- 入力操作の妨げにならないこと

## 7.7 設備選択画面
- 設備検索
- 最近使った設備
- 「設備なし」選択肢
- QR 読取による自動選択

## 7.8 同期管理画面
- 未同期一覧
- pending 件数
- failed 件数
- conflict 件数
- 各アイテムの最終エラー
- 再送

## 7.9 マイページ
- 表示名
- ログインID
- パスワード変更
- ログアウト

## 7.10 固定ページ（必須）
- /privacy-policy/
- /contact/
- /terms/

---

# 8. 操作フロー

## 8.1 新規記録作成
1. 新規記録を開く
2. 設備を選択する（または QR 読取、または「設備なし」を選ぶ）
3. 内容を入力する
4. ローカルに保存する
5. オンライン時はサーバー同期する
6. オフライン時は未同期として保持する

## 8.2 QR 読取
1. カメラを起動する
2. QR を読み取る
3. `equipment.qr_value`（設備コード文字列）と照合する
4. 一致した設備を自動選択する
5. 未登録なら候補表示する

## 8.3 同期
1. `sync_queue` から `pending` / `retrying` の操作を抽出する
2. `sync_push` で順次送信する（プッシュ）
3. 更新・削除時は `base_revision` とサーバー上の `revision` を比較する
4. 成功時は対象キューを `done` にし、対象レコードを `synced` に更新する
5. 競合時は 409 Conflict とサーバー版を受け取り、キューを `conflict` にする
6. `sync_pull` を `since_token` 付きで実行し、削除 tombstone を含む最新データを取り込む
7. 失敗時は `failed` としてエラーを保持する

---

# 9. オフライン仕様

## 9.1 ローカル保存
IndexedDB に以下を保存する。
- 下書き
- 未同期記録
- 最近使用設備
- 設備マスタキャッシュ
- `sync_queue`（未送信操作、失敗情報、競合状態）
- セッション関連の必要最小情報

### 9.1.1 sync_queue ストア
- queue_id
- entity_type（`work_log`）
- entity_id（`log_uuid`）
- operation（`create` / `update` / `delete`）
- payload
- status（`pending` / `retrying` / `failed` / `conflict` / `done`）
- retry_count
- last_error_code
- last_error_message
- last_error_at
- last_attempt_at
- created_at

## 9.2 同期方式
- 新規記録は log_uuid をクライアントで発行
- 更新・削除時は、クライアントが見ていた `base_revision` を送る
- サーバー保存成功時は `server_updated_at` を現在 UTC に更新し、`revision = revision + 1` とする
- ローカル変更は `dirty` とする
- サーバー反映後に `synced` とする
- `sync_pull` は `since_token`（サーバー側変更日時の UTC 文字列）を使って差分取得する
- `sync_pull` のレスポンスは `next_since_token` を返す
- ログイン後・同期時にサーバー側最新データをプル取得する
- プル同期では削除済みレコードも tombstone として返す

## 9.3 競合ルール
初期版は **revision 一致時のみ更新** とする。

- クライアントは更新時に `base_revision` を送る
- サーバー上の `revision == base_revision` の場合のみ更新を受け付ける
- 更新成功時は `revision = revision + 1` とする
- 不一致時は HTTP 409 Conflict を返し、サーバー版のレコードを返す
- クライアントは競合レコードをローカルで保持し、`sync_queue.status = conflict` として同期管理画面に表示する
- 自動マージは行わない

## 9.4 論理削除同期
- 削除 API は物理削除しない
- 削除時は `deleted_flag = 1`、`deleted_at = server current UTC`、`deleted_by = current_user_id`、`revision = revision + 1` とする
- プル同期では削除済みレコードも返す
- クライアントは `deleted_flag = 1` を受けたらローカルでも削除済みに更新し、通常一覧からは非表示にする
- admin 表示や監査用途では削除済みも参照可能とする
- tombstone は最低 90 日保持し、その後の物理削除は将来運用で検討する

## 9.5 オフライン中のセッション期限切れ
- オフライン中は下書き作成・編集を継続可能とする
- オフライン中は同期しない
- 再オンライン時に `session_check.cgi` を行う
- セッション期限切れなら再ログインを要求する
- 再ログイン成功後に未同期データを送信する

---

# 10. カメラ・写真・QR仕様

## 10.1 カメラ
- スマホカメラを起動できること
- 写真撮影または画像取得ができること
- 撮影後にプレビュー表示できること
- **Phase 5 以降の実装**

## 10.2 写真保存
**MVP には含めない。Phase 5 扱い。**
`work_photos` テーブルは先に作成する。

### 案B（推奨）
- Sakura 側 `upload.cgi` を追加
- DB には `photo_path` を保存

## 10.3 QR
- QR から設備呼び出し
- `qr_value` の形式は設備コード文字列（例: `MC-001`）
- 対応ブラウザでは BarcodeDetector を優先
- 非対応ブラウザではライブラリで代替
- QR コード発行機能は MVP 外（管理者が外部ツールで印刷）

---

# 11. API仕様

## 11.1 認証系 API
- `POST /api/register.cgi`
- `POST /api/login.cgi`
- `POST /api/logout.cgi`
- `GET /api/session_check.cgi`
- `POST /api/change_password.cgi`

## 11.2 equipment_api.cgi
- `GET /api/equipment_api.cgi`
  - `action=list`
  - `action=search&q=...`
  - `action=by_qr&qr_value=MC-001`
- `POST /api/equipment_api.cgi`
  - admin による新規登録
- `PUT /api/equipment_api.cgi`
  - admin による更新

## 11.3 worklog_api.cgi
- `GET /api/worklog_api.cgi`
  - `action=list&page=1&page_size=50`
  - `action=detail&log_uuid=...`
  - `action=sync_pull&since_token=...`
- `POST /api/worklog_api.cgi`
  - `action=create`
  - `action=sync_push`
- `PUT /api/worklog_api.cgi`
  - `action=update`
  - `action=status`
- `DELETE /api/worklog_api.cgi`
  - `action=delete&log_uuid=...`
  - 実体は論理削除とする

## 11.4 upload.cgi（Phase 5 以降）
- `POST /api/upload.cgi`

## 11.5 ページング
- リスト系は `page` と `page_size` を受け付ける
- レスポンスは `total` と `has_next` を返す

## 11.6 同期 payload

### 更新 API
クライアントは更新時に `base_revision` を送る。

```json
{
  "log_uuid": "xxxx",
  "base_revision": 7,
  "patch": {
    "status": "done",
    "result": "交換後正常"
  }
}
```

### sync_push request
```json
{
  "items": [
    {
      "operation": "update",
      "entity": {
        "log_uuid": "xxxx",
        "base_revision": 7,
        "fields": {
          "status": "done"
        }
      }
    }
  ]
}
```

### sync_push response
個別アイテムごとの成否を返す。
```json
{
  "status": "ok",
  "data": {
    "results": [
      { "log_uuid": "A001", "status": "ok", "revision": 3 },
      { "log_uuid": "A002", "status": "conflict", "server_revision": 5 },
      { "log_uuid": "A003", "status": "error", "message": "validation error" }
    ]
  }
}
```

### sync_pull request
`GET /api/worklog_api.cgi?action=sync_pull&since_token=2026-03-24T00:00:00Z`

### sync_pull response
```json
{
  "status": "ok",
  "data": {
    "items": [],
    "next_since_token": "2026-03-24T10:15:00Z"
  }
}
```

### 差分取得ロジック（since_token）
- サーバーは `server_updated_at >= since_token`（以上）の条件で検索する。
- `next_since_token` は、返却アイテム群の `server_updated_at` の最大値とする（空なら `since_token` を維持）。
- クライアントは同一秒内の重複取得を許容し、`log_uuid` に基づく upsert で重複排除を行う。
- 競合判定は `revision`、差分取得は `since_token` に役割を分ける。

## 11.7 API レスポンス形式
JSON で統一する。

### 成功時
```json
{
  "status": "ok",
  "data": {},
  "message": ""
}
```

### 失敗時
```json
{
  "status": "error",
  "message": "Invalid session",
  "errors": []
}
```

### 一覧系
```json
{
  "status": "ok",
  "data": {
    "items": [],
    "total": 0,
    "has_next": false
  }
}
```

### 競合時
HTTP ステータスは `409 Conflict` とする。

```json
{
  "status": "error",
  "message": "Conflict",
  "data": {
    "server_entity": {}
  },
  "errors": []
}
```

## 11.8 認証ヘッダー
```
Authorization: Bearer <session_token>
```

---

# 12. セキュリティ要件

以下を必須とする。

- パスワード平文保存禁止（bcrypt ハッシュのみ保存、8文字以上必須）
- 認証なし更新禁止
- 他人の記録を勝手に取得不可
- セッション期限あり（7日、最終操作から延長されるスライディング方式）
- HTTPS 利用
- CORS は許可オリジン限定（`https://garyohosu.github.io` / `http://localhost` / `http://127.0.0.1`）
- 管理機能は role チェック必須
- 入力値バリデーション実施
- SQL 注入対策実施
- ログイン試行制限（5回連続失敗で15分ロック。login_id 単位 + IP 単位）

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
- /terms/

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
  terms/
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
- 固定ページ作成（privacy-policy / contact / terms）

## Phase 2
- ユーザー登録
- ログイン（試行制限含む）
- セッション管理（Bearer Token）
- 権限制御

## Phase 3
- 作業記録 CRUD（論理削除含む）
- 設備マスタ参照
- 一覧検索（50件ページネーション）
- フォローアップ期限切れ表示

## Phase 4
- オフライン同期（プッシュ / プル）
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
2. ID / パスワードでログインできる（試行制限あり）
3. ログイン後のみ利用できる
4. 設備を選んで記録を登録できる（設備なし選択も可）
5. 自分の記録一覧を見られる（50件ページネーション）
6. 詳細表示できる
7. 編集できる
8. 論理削除できる
9. オフラインで下書きできる
10. 同期できる（プッシュ / プル）
11. QR で設備を呼び出せる
12. フォローアップ期限切れを一覧・詳細・ホームで確認できる
13. AdSense がホーム・一覧・詳細に入る
14. privacy-policy / contact / terms が存在する

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
- 設備マスタ CSV インポート（equipment_import.cgi）
- 更新履歴テーブル（work_log_history）
- QR コード発行機能

---

# 18. リポジトリ名

推奨リポジトリ名:
- worklog-pwa

候補:
- inspection-pwa
- fieldlog-pwa
- genba-note

本仕様では `worklog-pwa` を正式候補とする。
