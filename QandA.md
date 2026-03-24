# QandA.md
# SPEC.md レビュー時の不明点・確認事項

---

## Q1. CGI の実装言語は何を使いますか？

**A:** Python を使う。
ハッシュ処理、JSON API、SQLite 操作、将来の画像アップロードや認証拡張まで考えると扱いやすいから。既存の Sakura CGI 資産に合わせて Python CGI で実装する前提にする。将来 FastCGI 化は検討可。

---

## Q2. パスワードのハッシュアルゴリズムを教えてください。

**A:** bcrypt を採用する。
`password_hash` のみ保存し、平文保存は禁止。salt は bcrypt 側に内包されるので、別カラムは不要。

---

## Q3. セッショントークンの送信方式を教えてください。

**A:** Authorization ヘッダーで Bearer Token を送る。
Cookie ではなくヘッダー方式にする。PWA と API を別オリジンで扱いやすいから。
有効期限は 7日 を初期値にする。
重要操作時は `session_check.cgi` で都度検証する。

---

## Q4. CORS の許可オリジンは確定していますか？

**A:** 初期は以下を許可する。
- `https://garyohosu.github.io`
- `http://localhost`
- `http://127.0.0.1`

実運用上は GitHub Pages 配下の worklog-pwa 公開を前提とする。
実質の公開先: `https://garyohosu.github.io/worklog-pwa/`
CORS 判定はオリジン単位なので、まずは `https://garyohosu.github.io` を許可する。

---

## Q5. 最初の admin ユーザーはどうやって作りますか？

**A:** DB 直接投入で初期 admin を 1 件作る。
MVP では専用管理画面は作らない。
初期セットアップ手順書に以下を含める。
1. users テーブル作成
2. bcrypt ハッシュ済みパスワード生成
3. `role=admin` のユーザー投入

---

## Q6. 設備マスタの初期データはどこから来ますか？

**A:** 初期は CSV 一括投入を想定する。
MVP では「CSV アップロード画面」までは作らず、管理者が変換スクリプトまたは直接投入で登録する。
MVP 後に `equipment_import.cgi` を追加する余地を残す。

---

## Q7. equipment_id は NULL（設備なし）を許可しますか？

**A:** 許可する。
`record_type = memo` の場合など、設備なし記録を作れるようにする。
UI では「設備なし」を選べるようにし、DB では `equipment_id = NULL` を許可する。

---

## Q8. record_type の「trouble」と「repair」の使い分けを教えてください。

**A:** 同一レコードで状態を変化させる想定にする。
- `trouble`: 不具合・異常の記録
- `repair`: 修理作業の記録

MVP の基本運用: 異常発生時に `trouble` で作成し、修理完了まで同一レコード内で `status` を更新する。
`repair` は独立した記録種別としては残すが、運用上は必要時のみ使う。

---

## Q9. 削除機能は必要ですか？

**A:** 必要。ただし論理削除のみ。MVP に含める。
実装:
- `deleted_flag = 1`
- `deleted_at = server current UTC`
- `deleted_by = current_user_id`
- `revision = revision + 1`

削除は tombstone として同期対象に含める。
通常一覧には出さず、admin のみ参照可能にする。

---

## Q10. 詳細画面の「更新履歴」はどのテーブルで実現しますか？

**A:** MVP では履歴テーブルは作らない。
詳細画面の更新履歴は最小表示にする。
- 作成日時（`recorded_at`）
- 最終更新日時（`local_updated_at` を参考表示）
- 同期日時（`server_updated_at`）
- 更新者（`updated_by` から `users.display_name` を引いて表示）

MVP では `work_logs` に `created_by` / `updated_by` を持たせる。
`work_log_history` テーブルは将来拡張とする。

---

## Q11. 写真は MVP に含みますか？

**A:** MVP には含めない。Phase 5 扱いにする。
将来拡張を見越して `work_photos` テーブルは先に作っておいてよい。
最初の完成条件には写真添付を入れない。

---

## Q12. QR コードの qr_value 形式を教えてください。

**A:** 設備コードそのものを文字列で入れる。
例: `MC-001`、`LINE2-CHK-07`
URL 形式にはしない。理由はシンプルで運用しやすいから。
QR コードの発行・印刷は、初期は管理者が外部ツールや簡易スクリプトで行う想定。MVP では発行機能は作らない。

---

## Q13. 一覧画面にページネーションは必要ですか？

**A:** 必要。MVP では 1ページ50件のページネーションにする。
無限スクロールは採用しない。
理由は現場向けで一覧の見通しを優先したいから。

---

## Q14. フォローアップ期限切れ時の挙動を教えてください。

**A:** MVP では以下まで入れる。
- 一覧で期限切れを視覚表示（色分けまたはアイコン）
- 詳細画面で期限超過表示
- ホームで件数表示

通知は MVP 外。

---

## Q15. ログイン試行制限の具体的な実装方針を教えてください。

**A:** MVP に含める。方針は以下。
- 5回連続失敗で一時ロック
- ロック時間は 15分
- `login_id` 単位 + IP 単位で制限

---

## Q16. API のレスポンス形式を教えてください。

**A:** JSON で統一する。共通形式はこれ。

成功例:
```json
{
  "status": "ok",
  "data": {},
  "message": ""
}
```

失敗例:
```json
{
  "status": "error",
  "message": "Invalid session",
  "errors": []
}
```

一覧系は `data.items`、件数は `data.total` を基本にする。
ページング時は `data.has_next` も返す。

---

## Q17. 複数デバイスからの同時利用は想定していますか？

**A:** 想定する。
MVP では競合判定を revision ベースで行う。
- `work_logs.revision` を持つ
- クライアントは更新時に `base_revision` を送る
- サーバー上の `revision` と一致した時だけ更新する
- 更新成功時は `revision = revision + 1`
- 不一致時は `409 Conflict` を返し、サーバー版を返す

差分取得は `since_token` を使う。
ログイン後や同期時に、サーバー側の最新データをプル取得する。

---

## Q18. terms（利用規約）ページは必須ですか？

**A:** 必須にする。以下の理由から `/terms/` を MVP に含める。
- ID/パスワード登録あり
- AdSense 必須
- 公開サービス型

固定ページ（必須）:
- `/privacy-policy/`
- `/contact/`
- `/terms/`

---

# 追加の確認事項

## Q19. 「最後の保存を優先」は、どの値を比較して判定しますか？

**A:** 競合判定は revision ベースにする。
- `work_logs` に `revision INTEGER NOT NULL DEFAULT 1` を追加する
- クライアントは更新時に `base_revision` を送る
- サーバー上の `revision == base_revision` の時だけ更新を受け付ける
- 更新成功時は `revision = revision + 1`
- 不一致時は `409 Conflict` を返す

使い分けは以下。
- `local_updated_at`: ローカル表示用、参考情報
- `server_updated_at`: サーバー保存日時
- `revision`: 競合判定の唯一の基準

競合時はサーバー版を返し、クライアントはそのレコードを `conflict` 状態でローカル保持する。自動マージはしない。

---

## Q20. 論理削除は同期でどう伝播させますか？

**A:** 削除は tombstone として同期する。

`work_logs` に以下を追加する。
- `deleted_at TEXT NULL`
- `deleted_by INTEGER NULL`

削除 API では物理削除せず、以下を更新する。
- `deleted_flag = 1`
- `deleted_at = server current UTC`
- `deleted_by = current_user_id`
- `revision = revision + 1`

プル同期では削除済みも返す。端末側は `deleted_flag = 1` を受けたらローカルでも削除済みに更新し、通常一覧からは非表示にする。
tombstone は MVP では最低 90 日保持し、その後の物理削除は将来運用で検討する。

---

## Q21. 同期失敗時のエラー情報はどこに保持しますか？

**A:** IndexedDB に `sync_queue` ストアを追加して保持する。

項目は以下。
- `queue_id`
- `entity_type`（`work_log`）
- `entity_id`（`log_uuid`）
- `operation`（`create` / `update` / `delete`）
- `payload`
- `status`（`pending` / `retrying` / `failed` / `conflict` / `done`）
- `retry_count`
- `last_error_code`
- `last_error_message`
- `last_error_at`
- `last_attempt_at`
- `created_at`

ルールは以下。
- 同期失敗時は `failed`
- 再送中は `retrying`
- 競合時は `conflict`
- 成功時は `done`

同期管理画面では `pending` / `failed` / `conflict` 件数、各アイテムの最終エラー、再送ボタンを表示する。

---

## Q22. API の操作単位をどう切り分けますか？

**A:** HTTP メソッドと `action` を固定する。

認証系:
- `POST /api/register.cgi`
- `POST /api/login.cgi`
- `POST /api/logout.cgi`
- `GET /api/session_check.cgi`
- `POST /api/change_password.cgi`

設備系:
- `GET /api/equipment_api.cgi`
  - `action=list`
  - `action=search&q=...`
  - `action=by_qr&qr_value=MC-001`
- `POST /api/equipment_api.cgi`（admin の新規登録）
- `PUT /api/equipment_api.cgi`（admin の更新）

作業記録系:
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
  - 実体は論理削除

アップロード系（Phase 5 以降）:
- `POST /api/upload.cgi`

ページングは `page` / `page_size`、レスポンスは `total` / `has_next` を返す。
`sync_pull` の差分取得は `since_token`、競合判定は `revision` を使う。

---

## Q23. `record_type` / `status` / `sync_state` の値は「例」ではなく固定値ですか？

**A:** MVP では固定値にする。

`record_type`
- `inspection`
- `repair`
- `trouble`
- `maintenance`
- `memo`

`status`
- `draft`
- `open`
- `in_progress`
- `done`
- `pending_parts`

`sync_state`
- `local_only`
- `dirty`
- `synced`
- `failed`
- `conflict`

---

## Q24. 詳細画面の「更新者」はどこから取得しますか？

**A:** `work_logs` に以下を追加する。
- `created_by INTEGER NOT NULL`
- `updated_by INTEGER NOT NULL`

ルールは以下。
- 新規作成時: `created_by = current_user_id`、`updated_by = current_user_id`
- 更新時: `updated_by = current_user_id`
- 削除時: `deleted_by = current_user_id`

詳細画面の「更新者」は `updated_by` から `users.display_name` を引いて表示する。
`user_id` は所有者に近い意味で使い、更新者とは分ける。

---

## Q25. CORS の許可オリジンを最終的に何にしますか？

**A:** 許可オリジンは以下で統一する。
- `https://garyohosu.github.io`
- `http://localhost`
- `http://127.0.0.1`

`SPEC.md` 側の `localhost` という裸の表記はやめて、上記 3 つの文字列に揃える。

---

## Q26. オフライン中にセッション期限が切れた場合、下書き入力は継続可能ですか？

**A:** 下書き作成・編集は可能。同期のみ制限する。

挙動の詳細は以下：
- オフライン中は下書き作成・編集を継続できる（IndexedDBに保存）。
- 同期要求時（オンライン復帰時など）に `session_check.cgi` を実行。
- 期限切れ（401等）なら同期を中断し、UI上で `auth_expired` 状態を表示。
- 再ログイン成功後、`sync_queue` に残っている `pending` / `failed` / `conflict` を再送対象として処理を再開する。

---

## Q27. `sync_push` で複数件送信した際のエラーハンドリングはどうしますか？

**A:** 個別アイテムごとの成否を返す。

レスポンス形式を以下のように固定する：
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
クライアント側は、この `status` に基づいて `sync_queue` の各アイテムの状態（`done` / `conflict` / `failed`）を更新する。

---

## Q33. `sync_pull` の `since_token` による差分取得で、同一秒内の更新漏れを防ぐにはどうしますか？

**A:** サーバー側で `>=`（以上）判定を行い、次トークンに最大値を採用する。

実装ルール：
1. サーバーは `server_updated_at >= since_token` の条件で検索する。
2. レスポンスに含める `next_since_token` は、今回返したアイテム群の中の `server_updated_at` の最大値とする（アイテムが空なら `since_token` をそのまま返す）。
3. クライアントは `since_token` を重複取得のリスクを許容して `>=` で送り、`log_uuid` に基づいてローカルで重複排除（upsert）を行う。
これにより、同一秒内に複数の更新が発生しても取りこぼしを防ぐ。

---

## Q28. ユーザー新規登録時のデフォルト状態と承認フローを教えてください。

**A:** 登録直後から `is_active = 1`（有効）とし、即時利用可能とする。
MVP では公開型のセルフ登録を想定する。不正ユーザー対策は `login_attempts` によるロックと、将来的な admin による `is_active = 0` 化で対応する。

---

## Q29. パスワードの強度制限（バリデーション）はありますか？

**A:** MVP では「8文字以上」を必須とする。
文字種（英数字混在など）の強制は行わないが、実装上は推奨するメッセージを表示する。

---

## Q30. セッションの有効期限はアクセスごとに延長されますか？

**A:** アクセスごとに `expires_at` を更新する「スライディングセッション」方式にする。
最後に操作してから 7日間 有効とする。ただし、セキュリティのため `sessions` テーブルの `last_access_at` 更新は、パフォーマンスに配慮して一定時間（例: 1時間）以内の再アクセス時はスキップするなどの調整は検討可。

---

## Q31. クライアント側の設備マスタキャッシュはどうやって更新しますか？

**A:** `equipment_api.cgi` に `action=sync_pull` を追加するか、`last_updated_at` を条件にした差分取得を実装する。
ログイン時や、同期画面での手動更新時に、サーバー側の最新設備データを取得して IndexedDB を更新する。

---

## Q32. 論理削除レコード（Tombstone）の物理削除は誰が実行しますか？

**A:** MVP では「自動削除機能」は実装せず、運用でカバーする。
将来的に、Sakura サーバー側で月1回程度実行するクリーンアップスクリプト（Python）を作成し、`deleted_at` から 90日以上経過したレコードを物理削除する。

---

# USECASE.md レビュー時の不明点・確認事項

## Q34. admin のユーザー管理でできる操作の範囲を教えてください。

SPEC には「ユーザー管理」とありますが、具体的な操作範囲が未定義です。

候補:
- `is_active = 0` によるアカウント停止・復活
- `role` 変更（user → admin 昇格、admin → user 降格）
- admin によるパスワードリセット（仮パスワード発行）
- ユーザー一覧表示

---

## Q35. 集計確認画面の表示内容を教えてください。

admin 専用の集計確認画面について、何を表示するか未定義です。

候補:
- 期間別・ユーザー別の記録件数
- 設備別の故障件数・修理件数
- status 別件数
- フォローアップ未対応件数

MVP に含めますか？それとも Phase 6 以降ですか？

---

## Q36. 設備マスタキャッシュの更新タイミングを教えてください。

Q31 で「ログイン時や同期画面での手動更新時」と回答いただきましたが、
USECASE として整理するにあたり、以下を確認します。

1. ログイン時に自動取得しますか？（初回ロードが遅くなる可能性あり）
2. 同期ボタン押下時にまとめて取得しますか？
3. QR 読取前に都度チェックしますか？

---

## Q37. 一般ユーザーは他のユーザーの記録を参照できますか？

SPEC には「自分の記録の参照」とあります。
現場で複数人が同じ設備の記録を参照したい場合を考えると、他ユーザーの記録の「参照のみ」を許可するかどうかを確認します。

選択肢:
- A. 自分の記録のみ（完全非公開）
- B. 同設備の他ユーザー記録を参照可（編集・削除は自分のみ）
- C. 全ユーザーの記録を参照可（編集・削除は自分のみ）
