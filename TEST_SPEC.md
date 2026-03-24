# TEST_SPEC.md

## 凡例

| 記号 | 意味 |
|---|---|
| `TC` | テストケース番号 |
| `PASS` | 期待結果: 正常終了 |
| `FAIL` | 期待結果: エラー・拒否 |
| `PRE` | 前提条件 |
| `HTTP` | 期待 HTTP ステータスコード |

---

## TC-AUTH: 認証・アカウント管理

### TC-AUTH-REG: 新規登録

| TC | テスト内容 | 前提条件 | 入力 | 期待結果 |
|---|---|---|---|---|
| TC-AUTH-REG-01 | 正常登録 | login_id 未使用 | login_id=`user01`, password=`pass1234`, display_name=`田中` | HTTP 201, `{status:"ok"}`, is_active=1 で登録済み |
| TC-AUTH-REG-02 | パスワード 7 文字（短すぎ） | — | password=`1234567` | HTTP 400, `{status:"error"}` |
| TC-AUTH-REG-03 | パスワード 8 文字（境界値） | — | password=`12345678` | HTTP 201, PASS |
| TC-AUTH-REG-04 | login_id 重複 | `user01` 登録済み | login_id=`user01` | HTTP 409, `{status:"error"}` |
| TC-AUTH-REG-05 | login_id 空 | — | login_id=`""` | HTTP 400 |
| TC-AUTH-REG-06 | display_name 省略 | — | login_id=`user02`, password=`pass1234` (display_name なし) | HTTP 400 |
| TC-AUTH-REG-07 | password_hash は bcrypt で保存される | 登録後 DB 確認 | — | DB の password_hash が `$2b$` で始まる文字列 |
| TC-AUTH-REG-08 | 登録直後 role=user | — | 正常登録 | DB の role=`user` |
| TC-AUTH-REG-09 | email NULL 許可 | — | email フィールドなし | HTTP 201, DB の email=NULL |

### TC-AUTH-LOGIN: ログイン

| TC | テスト内容 | 前提条件 | 入力 | 期待結果 |
|---|---|---|---|---|
| TC-AUTH-LOGIN-01 | 正常ログイン | `user01` 登録済み, is_active=1 | 正しい login_id/password | HTTP 200, `{status:"ok", data:{session_token:...}}` |
| TC-AUTH-LOGIN-02 | session_token の形式 | ログイン後 | — | 約 43 文字の URL-safe 文字列（`secrets.token_urlsafe(32)` 相当） |
| TC-AUTH-LOGIN-03 | session_token は DB に UQ で保存 | ログイン後 DB 確認 | — | sessions テーブルに 1 件追加、session_token UNIQUE |
| TC-AUTH-LOGIN-04 | パスワード誤り（1 回目） | 正常ユーザー | 誤 password | HTTP 401, login_attempts に 1 件追加 |
| TC-AUTH-LOGIN-05 | 連続失敗 5 回でロック | 4 回失敗済み | 誤 password（5 回目） | HTTP 429, ロック状態 |
| TC-AUTH-LOGIN-06 | ロック中は正しいパスワードでも拒否 | ロック状態 | 正しい login_id/password | HTTP 429 |
| TC-AUTH-LOGIN-07 | ロック解除（15 分経過後） | ロック状態, 15 分後 | 正しい login_id/password | HTTP 200, PASS |
| TC-AUTH-LOGIN-08 | IP 単位でのロック | 同 IP から 5 回失敗 | — | HTTP 429（同 IP からの全ユーザーがロック対象） |
| TC-AUTH-LOGIN-09 | login_id 単位でのロック | 同一 login_id に 5 回失敗 | 別 IP から正しい password で再試行 | HTTP 429 |
| TC-AUTH-LOGIN-10 | is_active=0 のユーザーはログイン不可 | user01 を is_active=0 に変更 | 正しい認証情報 | HTTP 403 |
| TC-AUTH-LOGIN-11 | login_id 空 | — | login_id=`""` | HTTP 400 |
| TC-AUTH-LOGIN-12 | ログイン成功後 last_login_at 更新 | ログイン後 DB 確認 | — | users.last_login_at が現在時刻に更新 |

### TC-AUTH-SESSION: セッション確認・スライディング有効期限

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-AUTH-SES-01 | 有効セッション確認 | ログイン済み | session_check.cgi 呼び出し | HTTP 200, `{status:"ok"}` |
| TC-AUTH-SES-02 | 無効トークン | — | 存在しない session_token | HTTP 401 |
| TC-AUTH-SES-03 | 期限切れセッション | expires_at を過去に設定 | session_check.cgi 呼び出し | HTTP 401 |
| TC-AUTH-SES-04 | スライディング更新 | ログイン済み | API 呼び出し | sessions.expires_at と last_access_at が最終操作から 7 日後に更新 |
| TC-AUTH-SES-05 | Authorization ヘッダー不正形式 | — | `Authorization: Token xxx` (Bearer でない) | HTTP 401 |
| TC-AUTH-SES-06 | Authorization ヘッダーなし | — | ヘッダーなしで保護 API 呼び出し | HTTP 401 |

### TC-AUTH-LOGOUT: ログアウト

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-AUTH-LGT-01 | 正常ログアウト | ログイン済み | logout.cgi 呼び出し | HTTP 200, sessions テーブルから該当レコード削除 |
| TC-AUTH-LGT-02 | ログアウト後に同トークンでアクセス | ログアウト済み | 保護 API 呼び出し | HTTP 401 |

### TC-AUTH-CHPW: パスワード変更

| TC | テスト内容 | 前提条件 | 入力 | 期待結果 |
|---|---|---|---|---|
| TC-AUTH-CHPW-01 | 正常変更 | ログイン済み | old_password=正しい値, new_password=`newpass1` (8 文字以上) | HTTP 200, 新パスワードで再ログイン可 |
| TC-AUTH-CHPW-02 | 旧パスワード誤り | — | old_password=誤り | HTTP 401 |
| TC-AUTH-CHPW-03 | 新パスワード 7 文字 | — | new_password=`abc1234` | HTTP 400 |
| TC-AUTH-CHPW-04 | 変更後に旧パスワードでログイン不可 | 正常変更後 | old_password で login | HTTP 401 |

---

## TC-WLOG: 作業記録管理

### TC-WLOG-CREATE: 新規作成（オンライン）

| TC | テスト内容 | 前提条件 | 入力 | 期待結果 |
|---|---|---|---|---|
| TC-WLOG-C-01 | 正常作成（設備あり） | ログイン済み, equipment_id=1 存在 | record_type=`inspection`, status=`open`, title=`点検記録`, equipment_id=1 | HTTP 201, log_uuid 発行, revision=1, user_id=セッションユーザー |
| TC-WLOG-C-02 | equipment_id=NULL（memo タイプ） | ログイン済み | record_type=`memo`, title=`メモ`, equipment_id なし | HTTP 201, equipment_id=NULL |
| TC-WLOG-C-03 | user_id をリクエストに含めたら拒否 | ログイン済み | payload に user_id=99 | HTTP 400 |
| TC-WLOG-C-04 | created_by をリクエストに含めたら拒否 | ログイン済み | payload に created_by=99 | HTTP 400 |
| TC-WLOG-C-05 | revision をリクエストに含めたら拒否 | ログイン済み | payload に revision=5 | HTTP 400 |
| TC-WLOG-C-06 | title 空 | — | title=`""` | HTTP 400 |
| TC-WLOG-C-07 | record_type 不正値 | — | record_type=`unknown` | HTTP 400 |
| TC-WLOG-C-08 | status 不正値 | — | status=`archived` | HTTP 400 |
| TC-WLOG-C-09 | priority=NULL（省略可） | — | priority フィールドなし | HTTP 201, priority=NULL |
| TC-WLOG-C-10 | priority=`critical` | — | priority=`critical` | HTTP 201, priority=`critical` |
| TC-WLOG-C-11 | priority=`urgent`（不正値） | — | priority=`urgent` | HTTP 400 |
| TC-WLOG-C-12 | needs_followup=1, followup_due 設定 | — | needs_followup=1, followup_due=`2026-12-31` | HTTP 201, 両フィールド保存 |
| TC-WLOG-C-13 | 未認証での作成 | 未ログイン | — | HTTP 401 |

### TC-WLOG-CREATE-OFF: 新規作成（オフライン）

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-WLOG-OFF-01 | オフライン新規作成 | オフライン状態 | 新規作成フォーム送信 | IndexedDB に保存, sync_state=`local_only`, revision=0, server_updated_at=NULL |
| TC-WLOG-OFF-02 | log_uuid クライアント生成 | オフライン新規作成後 | — | IndexedDB の log_uuid が UUID v4 形式 |
| TC-WLOG-OFF-03 | SyncQueue に create 操作が追加 | オフライン新規作成後 | — | SyncQueue に operation=`create`, status=`pending` のレコード追加 |
| TC-WLOG-OFF-04 | sync_push 成功後 sync_state=`synced` | オンライン復帰後 push | — | sync_state=`synced`, revision>=1, server_updated_at 設定 |

### TC-WLOG-LIST: 一覧表示

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-WLOG-LST-01 | User は自分の記録のみ取得 | user01, user02 がそれぞれ記録作成 | user01 でログインして一覧取得 | user01 の記録のみ返却（user02 の記録は含まない） |
| TC-WLOG-LST-02 | Admin は全ユーザーの記録を取得 | admin01, user01, user02 が記録作成 | admin01 で一覧取得 | 全ユーザーの記録が返却 |
| TC-WLOG-LST-03 | 削除済み記録は通常一覧に非表示 | deleted_flag=1 のレコードあり | User/Admin で一覧取得 | deleted_flag=1 のレコードは除外 |
| TC-WLOG-LST-04 | Admin のみ削除済み含めるフィルタ使用可 | 削除済みレコードあり | admin で `include_deleted=true` | 削除済み含む全レコード返却 |
| TC-WLOG-LST-05 | User が削除済みフィルタ使用不可 | — | user01 で `include_deleted=true` | HTTP 403 |
| TC-WLOG-LST-06 | ページネーション 50 件 | 記録が 51 件以上 | 1 ページ目取得 | 50 件返却, 次ページ情報あり |
| TC-WLOG-LST-07 | ページネーション 2 ページ目 | 記録が 51 件 | 2 ページ目取得 | 1 件返却 |

### TC-WLOG-EDIT: 編集（競合なし）

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-WLOG-ED-01 | 正常編集（オンライン） | user01 の記録, revision=1 | base_revision=1 で更新 | HTTP 200, revision=2, updated_by=user01 |
| TC-WLOG-ED-02 | Admin が他ユーザーの記録を編集 | user01 の記録 | admin01 で編集 | HTTP 200, updated_by=admin01 |
| TC-WLOG-ED-03 | User が他ユーザーの記録を編集 | user02 の記録 | user01 で編集 | HTTP 403 |
| TC-WLOG-ED-04 | updated_by をリクエストに含めたら拒否 | — | payload に updated_by=99 | HTTP 400 |
| TC-WLOG-ED-05 | オフライン編集 → SyncQueue に update 追加 | オフライン, 既存記録 | 編集フォーム送信 | SyncQueue に operation=`update`, base_revision=現在値, status=`pending` |
| TC-WLOG-ED-06 | sync_state=`dirty` に変更 | オフライン編集後 | — | IndexedDB の sync_state=`dirty` |

### TC-WLOG-CONFLICT: 競合（409）

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-WLOG-CF-01 | base_revision 不一致で 409 | DB revision=2, クライアント base_revision=1 | update 送信 | HTTP 409, `{status:"conflict", server_entity:{...}}` |
| TC-WLOG-CF-02 | 409 後 SyncQueue.status=`conflict` | — | 上記後 | SyncQueue の該当エントリが status=`conflict` |
| TC-WLOG-CF-03 | 409 後 WorkLogLocal.sync_state=`conflict` | — | 上記後 | IndexedDB の sync_state=`conflict` |
| TC-WLOG-CF-04 | conflict は自動再送されない | sync_state=`conflict` | オンライン復帰 | 自動送信なし（手動解決のみ） |
| TC-WLOG-CF-05 | conflict 解決後に正常更新 | conflict 状態の記録 | サーバー側 revision を base_revision に合わせて再送 | HTTP 200, PASS |

### TC-WLOG-STATUS: 状態変更

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-WLOG-ST-01 | status=`draft` → `open` | status=`draft` | status=`open` で更新 | HTTP 200 |
| TC-WLOG-ST-02 | status=`open` → `in_progress` | — | — | HTTP 200 |
| TC-WLOG-ST-03 | status=`in_progress` → `done` | — | — | HTTP 200 |
| TC-WLOG-ST-04 | status=`done` → `pending_parts` | — | — | HTTP 200 |
| TC-WLOG-ST-05 | 不正な status 値 | — | status=`closed` | HTTP 400 |

### TC-WLOG-DELETE: 論理削除（tombstone）

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-WLOG-DEL-01 | 正常論理削除 | user01 の記録, revision=1 | user01 で削除 | HTTP 200, deleted_flag=1, deleted_at=now, deleted_by=user01, revision=2, server_updated_at=now |
| TC-WLOG-DEL-02 | Admin が他ユーザーの記録を削除 | user01 の記録 | admin01 で削除 | HTTP 200, deleted_by=admin01 |
| TC-WLOG-DEL-03 | User が他ユーザーの記録を削除 | user02 の記録 | user01 で削除 | HTTP 403 |
| TC-WLOG-DEL-04 | 物理削除でないことを確認 | 論理削除後 | DB 直接確認 | レコードは残存、deleted_flag=1 |
| TC-WLOG-DEL-05 | 削除後の tombstone が sync_pull で伝播 | 削除済みレコード | 別クライアントが sync_pull | deleted_flag=1 のレコードが WorkLogLocal に upsert |
| TC-WLOG-DEL-06 | オフライン削除 → SyncQueue に delete 追加 | オフライン | 削除操作 | operation=`delete`, base_revision=現在値, status=`pending` |

---

## TC-EQ: 設備・QR

### TC-EQ-QR: QR スキャン

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-EQ-QR-01 | キャッシュヒット・is_active=1 | EquipmentCache に qr_value=`MC-001` (is_active=1) | QR スキャン | 設備自動選択（API 不要） |
| TC-EQ-QR-02 | キャッシュヒット・is_active=0 | EquipmentCache に qr_value=`MC-002` (is_active=0) | QR スキャン | 「この設備は現在無効です」等のエラー表示 |
| TC-EQ-QR-03 | キャッシュミス・オンライン | キャッシュなし, オンライン | QR スキャン | equipment_api.cgi に by_qr 問い合わせ → 設備取得 |
| TC-EQ-QR-04 | キャッシュミス・オンライン・未登録 | キャッシュなし, DB にも未登録 | QR スキャン | 「設備が見つかりません」表示 |
| TC-EQ-QR-05 | キャッシュミス・オフライン | キャッシュなし, オフライン | QR スキャン | 「設備未登録または未同期」表示 |
| TC-EQ-QR-06 | QR 読取前に毎回 sync_pull はしない | オンライン | QR スキャン時 | `equipment_api.cgi?action=sync_pull` は呼び出さない（キャッシュミス時の `by_qr` は別ケース） |

### TC-EQ-NOSEL: 設備なし選択

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-EQ-NS-01 | equipment_id=NULL で作成可能 | — | 「設備なし」を選択して記録作成 | HTTP 201, equipment_id=NULL |
| TC-EQ-NS-02 | memo タイプは equipment_id=NULL デフォルト | — | record_type=`memo` で作成 | equipment_id=NULL 可 |

### TC-EQ-MASTER: 設備マスタ編集（Admin）

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-EQ-EM-01 | Admin が設備登録 | ログイン済み admin | 新規設備データ送信 | HTTP 201, equipment_code UQ 制約で保存 |
| TC-EQ-EM-02 | User が設備登録不可 | ログイン済み user | 設備登録 API 呼び出し | HTTP 403 |
| TC-EQ-EM-03 | equipment_code 重複 | 既存 equipment_code | 同一コードで登録 | HTTP 409 |
| TC-EQ-EM-04 | equipment_code 空 | — | equipment_code=`""` | HTTP 400 |
| TC-EQ-EM-05 | is_active=0 に設定 | 既存設備 | is_active=0 で更新 | HTTP 200, 以降の QR スキャンで除外 |

### TC-EQ-SYNC: 設備マスタ同期（3 段階ルール）

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-EQ-SYNC-01 | ログイン時に自動差分同期 | 設備マスタに更新あり | ログイン | equipment_api.cgi を自動呼び出し、EquipmentCache に upsert |
| TC-EQ-SYNC-02 | 同期ボタンで差分同期 | — | 同期ボタン押下 | equipment_api.cgi 呼び出し、差分のみ更新 |
| TC-EQ-SYNC-03 | QR 読取前に毎回 sync_pull はしない | — | QR スキャン | `equipment_api.cgi?action=sync_pull` 呼び出しなし（キャッシュミス時の `by_qr` は別ケース） |
| TC-EQ-SYNC-04 | updated_at による差分取得 | EquipmentCache の最終同期日時あり | 差分同期 | since=最終同期 updated_at で差分のみ取得 |

---

## TC-SYNC: オフライン・同期

### TC-SYNC-PUSH: Sync Push

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-SYNC-PUSH-01 | create 操作の push 成功 | SyncQueue に pending の create | sync_push | HTTP 200, results[].status=`ok`, revision>=1 返却 |
| TC-SYNC-PUSH-02 | update 操作の push 成功 | base_revision 一致 | sync_push | HTTP 200, revision+1 返却 |
| TC-SYNC-PUSH-03 | delete 操作の push 成功 | base_revision 一致 | sync_push | HTTP 200, DB の deleted_flag=1, server_updated_at 更新 |
| TC-SYNC-PUSH-04 | 一括送信（複数アイテム） | SyncQueue に 3 件 pending | sync_push | 3 件分の results 配列返却 |
| TC-SYNC-PUSH-05 | push 成功後に sync_pull 実行 | push 成功後 | — | 自動的に sync_pull を実行して「同期完了」 |
| TC-SYNC-PUSH-06 | push 成功後 SyncQueue.status=`done` | — | push 成功後 | 該当 SyncQueue エントリが status=`done` |
| TC-SYNC-PUSH-07 | push 失敗後 SyncQueue.status=`failed` | — | push 失敗後 | status=`failed` |
| TC-SYNC-PUSH-08 | failed は次回接続時に自動再送 | status=`failed` | オンライン復帰 | 自動的に再送試行 |
| TC-SYNC-PUSH-09 | conflict は自動再送されない | status=`conflict` | オンライン復帰 | 自動再送なし |
| TC-SYNC-PUSH-10 | retrying 中に別 push が重複しない | status=`retrying` | — | 重複送信なし |

### TC-SYNC-PULL: Sync Pull

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-SYNC-PULL-01 | 初回 pull (since_token なし) | — | sync_pull | 全レコード取得, next_since_token 返却 |
| TC-SYNC-PULL-02 | 差分 pull (since_token あり) | 前回 since_token 保存済み | sync_pull | 差分のみ返却 |
| TC-SYNC-PULL-03 | tombstone の伝播 | サーバーで deleted_flag=1 のレコードあり | sync_pull | deleted_flag=1 のレコードが WorkLogLocal に upsert |
| TC-SYNC-PULL-04 | conflict 状態は維持 | WorkLogLocal に conflict レコード | sync_pull で同じ log_uuid の DTO 受信 | sync_state=`conflict` は上書きしない（維持） |
| TC-SYNC-PULL-05 | 通常レコードは synced で upsert | — | sync_pull | sync_state=`synced` で保存 |
| TC-SYNC-PULL-06 | next_since_token を SyncMeta に保存 | pull 成功後 | — | SyncMeta[key=`last_since_token`]=next_since_token |
| TC-SYNC-PULL-07 | User は自分の記録のみ pull | user01, user02 がサーバーに記録 | user01 で sync_pull | user01 の記録のみ返却 |
| TC-SYNC-PULL-08 | Admin は全記録を pull | — | admin01 で sync_pull | 全ユーザーの記録が返却 |

### TC-SYNC-QUEUE: SyncQueue 状態遷移

| TC | テスト内容 | 初期状態 | 操作 | 期待状態 |
|---|---|---|---|---|
| TC-SYNC-Q-01 | オフライン操作 → pending | — | オフライン時に作成/編集/削除 | `pending` |
| TC-SYNC-Q-02 | pending → retrying | `pending` | 送信試行開始 | `retrying` |
| TC-SYNC-Q-03 | retrying → done | `retrying` | 送信成功 | `done` |
| TC-SYNC-Q-04 | retrying → failed | `retrying` | 送信失敗（一時エラー） | `failed` |
| TC-SYNC-Q-05 | retrying → conflict | `retrying` | 409 Conflict | `conflict` |
| TC-SYNC-Q-06 | failed → retrying | `failed` | 自動再送試行 | `retrying` |
| TC-SYNC-Q-07 | conflict → retrying | `conflict` | 手動解決後に再送 | `retrying` |
| TC-SYNC-Q-08 | retry_count インクリメント | 失敗時 | — | retry_count+=1, last_error_code/message/at 更新 |

### TC-SYNC-SESSION: セッション期限切れ中のオフライン

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-SYNC-SES-01 | セッション期限切れ中もオフライン下書き継続可能 | セッション期限切れ, オフライン | 新規作成 | IndexedDB に保存, sync_state=`local_only` |
| TC-SYNC-SES-02 | 再ログイン後に pending/failed のみ自動再送 | 上記後, 再ログイン | — | pending/failed の SyncQueue エントリが自動送信 |
| TC-SYNC-SES-03 | 再ログイン後 conflict は自動再送されない | conflict レコードあり | 再ログイン | conflict は手動解決のみ |

---

## TC-ADMIN: 管理者専用機能

### TC-ADMIN-USER: ユーザー管理

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-ADMIN-U-01 | Admin がユーザー一覧取得 | admin ログイン済み | admin_api.cgi/users | HTTP 200, 全ユーザーリスト |
| TC-ADMIN-U-02 | User がユーザー一覧取得不可 | user ログイン済み | admin_api.cgi/users | HTTP 403 |
| TC-ADMIN-U-03 | is_active=0 に変更（無効化） | user01 is_active=1 | admin が is_active=0 | HTTP 200, user01 以降ログイン不可 |
| TC-ADMIN-U-04 | is_active=1 に変更（有効化） | user01 is_active=0 | admin が is_active=1 | HTTP 200, user01 ログイン再可能 |
| TC-ADMIN-U-05 | Admin が自身を is_active=0 にできない | admin01 | admin01 自身を無効化 | HTTP 400/403, エラーメッセージ |
| TC-ADMIN-U-06 | role を user → admin に昇格 | user01 role=`user` | admin が role=`admin` に変更 | HTTP 200, user01 が管理者権限取得 |
| TC-ADMIN-U-07 | role を admin → user に降格 | admin02 role=`admin` (admin が 2 人) | admin01 が admin02 を role=`user` | HTTP 200 |
| TC-ADMIN-U-08 | 最後の 1 人の admin を降格できない | admin が 1 人だけ | その admin 自身を role=`user` | HTTP 400/403, エラーメッセージ |
| TC-ADMIN-U-09 | 仮パスワード再設定 | admin ログイン済み | 対象ユーザーに仮パスワード発行 | HTTP 200, 新パスワードでログイン可, 旧パスワード無効 |

### TC-ADMIN-DASH: 集計ダッシュボード

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-ADMIN-D-01 | Admin がダッシュボード取得 | admin ログイン済み | admin_api.cgi/stats | HTTP 200, 集計データ含む |
| TC-ADMIN-D-02 | User がダッシュボード取得不可 | user ログイン済み | admin_api.cgi/stats | HTTP 403 |
| TC-ADMIN-D-03 | 期間別件数が含まれる | — | ダッシュボード取得 | 期間別の記録件数データあり |
| TC-ADMIN-D-04 | status 別件数が含まれる | — | — | status 別カウントあり |
| TC-ADMIN-D-05 | record_type 別件数が含まれる | — | — | record_type 別カウントあり |
| TC-ADMIN-D-06 | フォローアップ超過件数が含まれる | followup_due 超過レコードあり | — | 超過件数が含まれる |

---

## TC-ENUM: 列挙型バリデーション

### TC-ENUM-RECTYPE: RecordType

| TC | 値 | 期待結果 |
|---|---|---|
| TC-ENUM-RT-01 | `inspection` | PASS |
| TC-ENUM-RT-02 | `repair` | PASS |
| TC-ENUM-RT-03 | `trouble` | PASS |
| TC-ENUM-RT-04 | `maintenance` | PASS |
| TC-ENUM-RT-05 | `memo` | PASS |
| TC-ENUM-RT-06 | `other` | FAIL (HTTP 400) |
| TC-ENUM-RT-07 | `Inspection` (大文字) | FAIL (HTTP 400) |
| TC-ENUM-RT-08 | `""` (空文字) | FAIL (HTTP 400) |
| TC-ENUM-RT-09 | NULL / 省略 | FAIL (HTTP 400) |

### TC-ENUM-STATUS: WorkStatus

| TC | 値 | 期待結果 |
|---|---|---|
| TC-ENUM-ST-01 | `draft` | PASS |
| TC-ENUM-ST-02 | `open` | PASS |
| TC-ENUM-ST-03 | `in_progress` | PASS |
| TC-ENUM-ST-04 | `done` | PASS |
| TC-ENUM-ST-05 | `pending_parts` | PASS |
| TC-ENUM-ST-06 | `closed` | FAIL (HTTP 400) |
| TC-ENUM-ST-07 | `in-progress` (ハイフン) | FAIL (HTTP 400) |

### TC-ENUM-PRIORITY: Priority（NULL 許可）

| TC | 値 | 期待結果 |
|---|---|---|
| TC-ENUM-PRI-01 | `low` | PASS |
| TC-ENUM-PRI-02 | `medium` | PASS |
| TC-ENUM-PRI-03 | `high` | PASS |
| TC-ENUM-PRI-04 | `critical` | PASS |
| TC-ENUM-PRI-05 | NULL / 省略 | PASS（NULL 許可） |
| TC-ENUM-PRI-06 | `urgent` | FAIL (HTTP 400) |
| TC-ENUM-PRI-07 | `normal` | FAIL (HTTP 400) |

### TC-ENUM-ROLE: Role

| TC | 値 | 期待結果 |
|---|---|---|
| TC-ENUM-ROLE-01 | `user` | PASS |
| TC-ENUM-ROLE-02 | `admin` | PASS |
| TC-ENUM-ROLE-03 | `superadmin` | FAIL |
| TC-ENUM-ROLE-04 | `guest` | FAIL |

### TC-ENUM-SYNCSTATE: SyncState（クライアント内部）

| TC | テスト内容 | 期待状態 |
|---|---|---|
| TC-ENUM-SS-01 | オフライン新規作成直後 | `local_only` |
| TC-ENUM-SS-02 | オンライン作成/push 成功後 | `synced` |
| TC-ENUM-SS-03 | オフライン編集後 | `dirty` |
| TC-ENUM-SS-04 | push 失敗後 | `failed` |
| TC-ENUM-SS-05 | 409 Conflict 後 | `conflict` |

---

## TC-PAYLOAD: ペイロードバリデーション

### TC-PAYLOAD-PUSH: SyncPushFields 禁止フィールド

| TC | テスト内容 | 入力 | 期待結果 |
|---|---|---|---|
| TC-PLD-01 | user_id をペイロードに含む | `fields: {user_id: 99, title: "test"}` | HTTP 400 |
| TC-PLD-02 | created_by をペイロードに含む | `fields: {created_by: 99, ...}` | HTTP 400 |
| TC-PLD-03 | updated_by をペイロードに含む | `fields: {updated_by: 99, ...}` | HTTP 400 |
| TC-PLD-04 | deleted_flag をペイロードに含む | `fields: {deleted_flag: 1, ...}` | HTTP 400 |
| TC-PLD-05 | deleted_at をペイロードに含む | `fields: {deleted_at: "2026-01-01", ...}` | HTTP 400 |
| TC-PLD-06 | server_updated_at をペイロードに含む | `fields: {server_updated_at: "...", ...}` | HTTP 400 |
| TC-PLD-07 | revision をペイロードに含む | `fields: {revision: 99, ...}` | HTTP 400 |
| TC-PLD-08 | sync_state をペイロードに含む | `fields: {sync_state: "synced", ...}` | HTTP 400 |

### TC-PAYLOAD-CREATE: create ペイロード構造

| TC | テスト内容 | 入力 | 期待結果 |
|---|---|---|---|
| TC-PLD-C-01 | 正常 create ペイロード | `{operation:"create", entity:{log_uuid:"...", fields:{...}}}` | HTTP 200/201 |
| TC-PLD-C-02 | log_uuid 省略 | log_uuid フィールドなし | HTTP 400 |
| TC-PLD-C-03 | fields 省略 | fields フィールドなし | HTTP 400 |
| TC-PLD-C-04 | operation=`create` で base_revision 含む | base_revision フィールドあり | HTTP 400 |

### TC-PAYLOAD-UPDATE: update ペイロード構造

| TC | テスト内容 | 入力 | 期待結果 |
|---|---|---|---|
| TC-PLD-U-01 | 正常 update ペイロード | `{operation:"update", entity:{log_uuid:"...", base_revision:1, fields:{...}}}` | HTTP 200 |
| TC-PLD-U-02 | base_revision 省略 | base_revision フィールドなし | HTTP 400 |
| TC-PLD-U-03 | base_revision=0 | base_revision=0 | HTTP 400（revision=0 はクライアント未同期状態） |

### TC-PAYLOAD-DELETE: delete ペイロード構造

| TC | テスト内容 | 入力 | 期待結果 |
|---|---|---|---|
| TC-PLD-D-01 | 正常 delete ペイロード | `{operation:"delete", entity:{log_uuid:"...", base_revision:1}}` | HTTP 200 |
| TC-PLD-D-02 | base_revision 省略 | base_revision フィールドなし | HTTP 400 |
| TC-PLD-D-03 | fields 含む（不要） | fields フィールドあり | HTTP 400 |

---

## TC-SEC: セキュリティ

### TC-SEC-CORS: CORS

| TC | テスト内容 | Origin | 期待結果 |
|---|---|---|---|
| TC-SEC-CORS-01 | 許可オリジンからのリクエスト | `https://garyohosu.github.io` | CORS ヘッダーあり, HTTP 200 |
| TC-SEC-CORS-02 | localhost からのリクエスト | `http://localhost` | CORS ヘッダーあり |
| TC-SEC-CORS-03 | 127.0.0.1 からのリクエスト | `http://127.0.0.1` | CORS ヘッダーあり |
| TC-SEC-CORS-04 | 不正オリジンからのリクエスト | `https://evil.example.com` | CORS ヘッダーなし / HTTP 403 |
| TC-SEC-CORS-05 | Origin ヘッダーなし | Origin なし | HTTP 403 |

### TC-SEC-INJECT: インジェクション対策

| TC | テスト内容 | 入力 | 期待結果 |
|---|---|---|---|
| TC-SEC-INJ-01 | SQL インジェクション（login_id） | `login_id = "' OR 1=1 --"` | HTTP 400/401, DB エラーなし |
| TC-SEC-INJ-02 | SQL インジェクション（title） | `title = "'; DROP TABLE work_logs; --"` | HTTP 400, DB テーブル無事 |
| TC-SEC-INJ-03 | XSS（title） | `title = "<script>alert(1)</script>"` | 保存はされる。API は JSON 文字列として返し、画面表示時にスクリプトが実行されない |
| TC-SEC-INJ-04 | パスワードは bcrypt で保存 | 正常登録後 DB 確認 | `$2b$` プレフィックスの hash |

### TC-SEC-AUTHZ: アクセス制御

| TC | テスト内容 | 前提条件 | 操作 | 期待結果 |
|---|---|---|---|---|
| TC-SEC-AZ-01 | User が他ユーザーの記録を取得不可 | user01, user02 が記録作成 | user01 が user02 の log_uuid で詳細取得 | HTTP 403 |
| TC-SEC-AZ-02 | User が admin_api にアクセス不可 | user ログイン済み | admin_api.cgi 呼び出し | HTTP 403 |
| TC-SEC-AZ-03 | 未認証で保護 API アクセス不可 | 未ログイン | worklog_api.cgi 呼び出し | HTTP 401 |
| TC-SEC-AZ-04 | 他ユーザーの session_token で認証不可 | user01, user02 の session_token | user02 のトークンを使って user01 の記録取得 | HTTP 403 |

---

## TC-DB: DB 制約（サーバー）

### TC-DB-UNIQUE: ユニーク制約

| TC | テーブル | カラム | 期待結果 |
|---|---|---|---|
| TC-DB-UQ-01 | users | login_id | 重複登録で UNIQUE エラー → HTTP 409 |
| TC-DB-UQ-02 | sessions | session_token | 重複トークンで UNIQUE エラー（token 再生成で回避） |
| TC-DB-UQ-03 | equipment | equipment_code | 重複コードで UNIQUE エラー → HTTP 409 |
| TC-DB-UQ-04 | work_logs | log_uuid | 重複 UUID で UNIQUE エラー → HTTP 409 |

### TC-DB-FK: 外部キー（論理参照）

| TC | テスト内容 | 期待結果 |
|---|---|---|
| TC-DB-FK-01 | 存在しない equipment_id でログ作成 | HTTP 400 or 404 |
| TC-DB-FK-02 | 存在しない user_id でログ作成（API 経由は不可能だが直接 DB は確認） | DB 制約または API バリデーションで拒否 |
| TC-DB-FK-03 | work_photos.log_uuid が存在しない log_uuid を参照 | DB 制約エラー |

### TC-DB-NULL: NULL 制約

| TC | テーブル | カラム | NULL の可否 |
|---|---|---|---|
| TC-DB-NULL-01 | users | email | NULL 許可 |
| TC-DB-NULL-02 | users | last_login_at | NULL 許可 |
| TC-DB-NULL-03 | work_logs | equipment_id | NULL 許可 |
| TC-DB-NULL-04 | work_logs | priority | NULL 許可 |
| TC-DB-NULL-05 | work_logs | symptom | NULL 許可 |
| TC-DB-NULL-06 | work_logs | work_detail | NULL 許可 |
| TC-DB-NULL-07 | work_logs | result | NULL 許可 |
| TC-DB-NULL-08 | work_logs | title | NOT NULL（空文字も不可） |
| TC-DB-NULL-09 | work_logs | record_type | NOT NULL |
| TC-DB-NULL-10 | work_logs | status | NOT NULL |
| TC-DB-NULL-11 | work_logs | revision | NOT NULL |

---

## TC-IDB: クライアント IndexedDB

### TC-IDB-WLOGLOCAL: WorkLogLocal

| TC | テスト内容 | 期待結果 |
|---|---|---|
| TC-IDB-WL-01 | オフライン新規作成: 初期値確認 | revision=0, server_updated_at=NULL, sync_state=`local_only` |
| TC-IDB-WL-02 | sync_push 成功後の更新 | revision>=1, server_updated_at 設定, sync_state=`synced` |
| TC-IDB-WL-03 | sync_pull の upsert で既存レコード更新 | log_uuid 一致で上書き |
| TC-IDB-WL-04 | local_updated_at はクライアント専用（push ペイロードに含めない） | SyncPushFields に local_updated_at なし |
| TC-IDB-WL-05 | sync_state はクライアント専用（push ペイロードに含めない） | SyncPushFields に sync_state なし |

### TC-IDB-SYNCQUEUE: SyncQueue

| TC | テスト内容 | 期待結果 |
|---|---|---|
| TC-IDB-SQ-01 | create ペイロード: log_uuid + fields | payload に log_uuid と fields のみ（user_id 等禁止項目なし） |
| TC-IDB-SQ-02 | update ペイロード: log_uuid + base_revision + fields | 3 フィールド確認 |
| TC-IDB-SQ-03 | delete ペイロード: log_uuid + base_revision のみ | fields なし |
| TC-IDB-SQ-04 | queue_id は一意 | 複数エントリで重複なし |

### TC-IDB-SYNCMETA: SyncMeta

| TC | テスト内容 | 期待結果 |
|---|---|---|
| TC-IDB-SM-01 | since_token が保存される | sync_pull 後に SyncMeta に next_since_token が保存 |
| TC-IDB-SM-02 | key-value 形式で取得可能 | key=`last_since_token` でバリュー取得 |

---

## TC-API: API レスポンス形式

| TC | テスト内容 | 期待結果 |
|---|---|---|
| TC-API-FMT-01 | 成功レスポンス形式 | `{status:"ok", data:{...}}` |
| TC-API-FMT-02 | エラーレスポンス形式 | `{status:"error", message:"...", errors:[...]}` |
| TC-API-FMT-03 | sync_push レスポンス形式 | `{status:"ok", results:[{log_uuid, status, revision, ...}]}` |
| TC-API-FMT-04 | sync_pull レスポンス形式 | `{status:"ok", data:{items:[...], next_since_token:"..."}}` |
| TC-API-FMT-05 | Content-Type: application/json | 全 API レスポンスで確認 |

---

## TC-PWA: PWA・公開ページ

| TC | テスト内容 | 期待結果 |
|---|---|---|
| TC-PWA-01 | manifest.json が有効 | name, start_url, icons, display 等必須フィールドあり |
| TC-PWA-02 | Service Worker が登録される | navigator.serviceWorker.controller が有効 |
| TC-PWA-03 | オフライン時にアプリが起動する | Service Worker のキャッシュから起動 |
| TC-PWA-04 | ホーム画面追加（A2HS）が可能 | インストールプロンプトが表示される |
| TC-PWA-05 | AdSense: ログイン画面では非表示 | 広告ユニットの DOM 要素が存在しない |
| TC-PWA-06 | AdSense: 作業入力中は非表示 | — |
| TC-PWA-07 | AdSense: QR 読取中は非表示 | — |
| TC-PWA-08 | AdSense: トップページに表示 | 広告ユニットの DOM 要素が存在する |
| TC-PWA-09 | AdSense: /guide/ に表示 | — |
| TC-PWA-10 | /terms/, /privacy-policy/, /contact/ ページが存在する | HTTP 200 で取得可能 |
| TC-PWA-11 | index.html（トップ）はログイン済みでも自動リダイレクトしない | ログイン済みで index.html にアクセス → そのまま表示 |
