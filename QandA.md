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
- 再ログイン成功後、自動再送対象は `pending` / `failed` とする。
- `conflict` は自動再送しない。ユーザーが内容を確認して手動解決後にのみ再送する。

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

**A:** `equipment_api.cgi?action=sync_pull&since_token=...` で差分取得する。
設備マスタは `updated_at >= since_token` で返し、`is_active=0` の設備も同期対象に含める。
ログイン時や、同期画面での手動更新時に、サーバー側の最新設備データを取得して IndexedDB を更新する。

---

## Q32. 論理削除レコード（Tombstone）の物理削除は誰が実行しますか？

**A:** MVP では「自動削除機能」は実装せず、運用でカバーする。
将来的に、Sakura サーバー側で月1回程度実行するクリーンアップスクリプト（Python）を作成し、`deleted_at` から 90日以上経過したレコードを物理削除する。

---

# USECASE.md レビュー時の不明点・確認事項

## Q34. admin のユーザー管理でできる操作の範囲を教えてください。

**A:** MVP に含める操作範囲は以下。
- ユーザー一覧表示
- `is_active` の変更（有効化 / 無効化）
- `role` の変更（user → admin 昇格 / admin → user 降格）
- 仮パスワード再設定（管理画面で一時表示。メール送信は MVP 外）

補足ルール:
- 最後の1人の admin を user に降格するのは禁止
- admin 自身を `is_active=0` にするのも禁止
- パスワードリセット時は旧パスワードを無効化し、次回ログイン後に変更を促す

---

## Q35. 集計確認画面の表示内容を教えてください。

**A:** MVP に含める。件数中心の簡易ダッシュボードにする。

MVP で表示する内容:
- 期間別記録件数（今日 / 直近7日 / 直近30日）
- status 別件数（draft / open / in_progress / done / pending_parts）
- record_type 別件数
- フォローアップ期限超過件数
- ユーザー別記録件数
- 設備別記録件数（上位N件）

MVP では含めないもの: グラフの凝った可視化、故障傾向の詳細分析、月次レポート出力、CSV/PDF 出力

---

## Q36. 設備マスタキャッシュの更新タイミングを教えてください。

**A:** 3段階ルールで統一する。

1. **ログイン時**: 自動差分同期（`equipment_api.cgi?action=sync_pull&since_token=...`）
2. **同期ボタン押下時**: 作業記録同期とあわせて設備マスタも差分同期
3. **QR 読取前**: 毎回の通信はしない。ローカルキャッシュを使う
   - 例外: QR 値がローカルに存在しない場合のみ、オンライン時は `action=by_qr` で問い合わせる
   - オフラインで未登録の場合は「設備未登録または未同期」を表示する

---

## Q37. 一般ユーザーは他のユーザーの記録を参照できますか？

**A:** 自分の記録のみ（完全非公開）で固定する。

理由:
- アクセス制御が最も明確
- 誤閲覧の事故を防ぎやすい
- まずは認証・同期・記録機能を安定させることが優先

将来拡張案（Phase 2 以降）:
- B. 同設備の他ユーザー記録を参照可（編集・削除は自分のみ、共有範囲は admin 設定で切り替え）

---

## Q38. Admin（管理者）の認証フローは User と同一ですか？

**A:** 同一。
Admin も専用ログイン画面は持たず、共通のログイン画面から login_id / password でログインする。
セッション管理、ログイン試行制限、Bearer Token、7日有効のスライディングセッションなどの仕様も User と共通とする。
違いは ログイン後に使える機能が role=admin で追加される 点のみ。

---

## Q39. Admin による「削除済み記録」の参照はどのように行いますか？

**A:** 一覧画面のフィルタオプションとして実装する。
MVP では、Admin が一覧画面を開いたときのみ
- 「削除済みを含める」
- 「削除済みのみ表示」
のフィルタを使えるようにする。専用の「ゴミ箱ページ」などは作らない。
通常ユーザーには削除済み記録は表示しない。

---

## Q40. 作業記録一覧での「検索・絞り込み」は User が行える機能ですか？

**A:** 行える。
一覧画面で User も検索・絞り込みを使える。対象条件は仕様どおり、
- 設備名
- 設備コード
- ライン
- 日付
- 種別
- 状態
とする。
ただし、User が参照できるのは 自分の記録だけ なので、検索対象も自分の記録に限定する。

---

## Q41. Guest（未認証ユーザー）に AdSense 広告は表示されますか？

**A:** 表示する。

表示対象：
- トップページ
- 利用案内ページ
- /privacy-policy/
- /contact/
- /terms/

非表示対象：
- ログイン画面
- 新規登録画面
- 作業入力画面中央
- QR 読取中
- カメラ撮影中

補足：
Guest がアクセスできる公開ページには広告を表示し、認証入力や作業入力を妨げる画面では広告を表示しない。つまり、「Guest に広告は出すが、ログイン・登録フォームには出さない」 で固定する。

---

# USECASE.md レビュー時の不明点・確認事項

## Q42. Admin は作業記録の「作成・編集・削除」を実行できますか？

**A:** できる。B（全記録の参照・編集・削除が可能）を採用する。

Admin に許可する作業記録操作:
- 新規作成: 可
- 詳細表示: 可
- 状態変更: 可
- 編集: 可（全ユーザーの記録が対象）
- 論理削除: 可（全ユーザーの記録が対象）

補足ルール:
- Admin が新規作成した記録は `user_id` = Admin 自身、`created_by` / `updated_by` も Admin 自身
- Admin が他ユーザー記録を編集・削除した場合も、`updated_by` / `deleted_by` は Admin 自身にする
- 「誰の記録か」= `user_id`、「最後に操作した人」= `updated_by` として分けて保持する

---

## Q43. Admin は QR 読取・「設備なし」選択を実行できますか？

**A:** できる。Q42 で Admin に作業記録作成を許可するため、設備選択系も User と同等に利用可。

Admin に許可する設備関連操作:
- 設備一覧参照
- 設備検索
- QR 読取（User と同じ動作ルール）
- 「設備なし」選択（equipment_id=NULL 許可）
- 設備マスタ編集（Admin 専用）

QR の動作ルールは User と共通:
1. まずローカルキャッシュ参照
2. 未登録でオンラインなら `by_qr` で問い合わせ
3. 未登録でオフラインなら「設備未登録または未同期」を表示

---

## Q44. Admin もオフライン下書き・同期機能を使いますか？

**A:** 使う。作業記録機能に関しては Admin も User と同じオフライン機能を利用可とする。

Admin が使えるオフライン機能（作業記録系）:
- 下書き保存
- sync_queue への積み込み
- sync push / sync pull
- conflict 表示
- 再送

オンライン必須の管理操作:
- ユーザー管理（一覧・is_active・role 変更・パスワードリセット）
- 集計ダッシュボード
- 設備マスタ編集

整理: 作業記録系 = Admin もオフライン対応あり / 管理系 = オンライン必須

---

## Q45. トップページ（index.html）と「利用案内ページ」の内容を教えてください。

**A:** どちらも MVP に含める。

### index.html（公開トップページ）
未認証ユーザー向けのサービス紹介ページ。AdSense 表示対象。

表示内容:
- アプリ名・サービス概要
- 主な特徴（スマホで記録 / PWA / オフライン下書き / QR 設備呼び出し）
- 利用開始導線（ログイン / 新規登録）
- 公開固定ページへのリンク（/privacy-policy/ / /contact/ / /terms/ / /guide/）
- AdSense 広告枠

ログイン済み時の挙動: 自動リダイレクトはしない。トップページをそのまま表示し、ヘッダーに「ホームへ」リンクを出す。（公開トップを常に広告対象ページとして安定運用するため）

### /guide/（利用案内ページ）
独立したページ。パスは `/guide/` を正式採用。AdSense 表示対象。

表示内容:
- このアプリでできること
- 利用の流れ（登録→ログイン→記録作成→オフライン保存→同期）
- QR 読取の使い方
- 設備なし記録の使い方
- 同期エラー時の見方
- Admin と User の違い（簡潔）
- AdSense 広告枠

---

# SEQUENCE.md レビュー時の不明点・確認事項

## Q46. ログイン試行制限で使う `ip_address` は、ブラウザ送信値を使いますか？

**A:** 使わない。`ip_address` は API 側が接続元から確定する。

仕様決定:
- ブラウザから `ip` は送らない
- `login.cgi` は `login_id` と `password` だけを受け取る
- `login_attempts.ip_address` は API 側で取得する
- 逆プロキシ配下でない前提では接続元 IP をそのまま使う
- 将来リバースプロキシを置く場合のみ、信頼できるプロキシ配下に限って `X-Forwarded-For` を解釈する

`POST /api/login.cgi {login_id, password, ip}` という記述は廃止し、`POST /api/login.cgi {login_id, password}` に統一する。

---

## Q47. 作業記録の新規作成 API で `user_id` はクライアントから送りますか？

**A:** 送らない。`user_id` はセッションから API 側で確定する。

仕様決定:
- `action=create` ではクライアントは `user_id` を送らない
- API は Bearer Token から `current_user_id` を取得して `user_id` に設定する
- Admin が新規作成する場合も `user_id = current_user_id` を API 側で自動設定する
- クライアントが `user_id` を送ってきた場合は無視ではなくエラーにする

これにより、他人名義レコードの混入を防ぎ、実装バグも早期に検出できる。

---

## Q48. `sync_push` の `delete` 操作は物理削除ですか、論理削除ですか？

**A:** 論理削除。`sync_push` の `operation=delete` は tombstone 更新を意味する。

仕様決定:
- `operation=delete` のサーバー処理は物理削除ではない
- `deleted_flag = 1`
- `deleted_at = server current UTC`
- `deleted_by = current_user_id`
- `revision = revision + 1`
- `server_updated_at = now`

補足:
- `sync_push` 結果でも tombstone を返す
- `sync_pull` でも tombstone を返す
- 別端末は `deleted_flag=1` を受けてローカル更新する

`INSERT / UPDATE / DELETE` という表現はやめて、`delete = tombstone 更新` と明記する。

---

## Q49. 設備マスタで `is_active=0` になった設備は差分同期でどう扱いますか？

**A:** 差分同期で返す。`is_active=0` の設備も `sync_pull` の対象に含める。

仕様決定:
- `equipment_api.cgi?action=sync_pull` は `updated_at >= since_token` の設備を返す
- `is_active=1` だけには絞らない
- 無効化は tombstone ではなく状態変更として扱う

クライアント動作:
- `is_active=0` を受けたら設備選択候補から除外する
- `is_active=0` を受けたら QR 自動選択から除外する
- 既存記録の設備表示は維持する
- QR 読取で一致しても「この設備は無効です」と表示し、自動選択しない

設備の失効は差分同期で反映し、新規入力候補からだけ外す。

---

## Q50. 「同期完了」は `sync_push` の成功だけでよいですか？ それとも直後に `sync_pull` まで必須ですか？

**A:** `sync_pull` まで必須。同期待機の 1 セットは `session_check` → `sync_push` → `sync_pull` とする。

仕様決定:
- `sync_push` だけでは「送れた」だけで、同期完了とはみなさない
- `sync_pull` まで終わって、他端末更新・tombstone・サーバー最新差分を反映した時点で「同期完了」とする
- 再ログイン後の再同期も `sync_push` の後に `sync_pull` まで行う

UI 文言:
- `sync_push` 成功直後: 「送信完了」
- `sync_pull` 完了後: 「同期完了」

MVP では最終表示をまとめて「同期完了」としてよいが、内部状態としては pull 完了を必須とする。

---

## Q51. `session_token` の保存先は `localStorage` で確定ですか？

**A:** 確定する。`localStorage` を正式採用する。

理由:
- PWA での実装が単純
- Bearer Token と相性がよい
- 今回は Cookie ベースではない
- オフライン復帰時にも扱いやすい

保存先ルール:
- `session_token` は `localStorage`
- `since_token`、設備キャッシュ、作業記録、`sync_queue` は IndexedDB
- ログアウト時は `localStorage` から削除する
- `401` / 期限切れ時も UI 上で削除または再ログイン導線を出す

将来、セキュリティ要件が変わった場合は再検討可とする。

---

## Q52. セッション期限切れ後の再送対象は `pending` のみですか？

**A:** 自動再開対象は `pending` と `failed`。`conflict` は自動再送しない。

理由:
- `pending`: まだ未送信なので再開してよい
- `failed`: 通信断や一時エラーの可能性があるので再試行対象でよい
- `conflict`: ユーザーが内容を確認して解決しない限り、自動再送すると危ない

仕様決定:
- 自動再送対象: `pending` / `failed`
- 自動再送しない: `conflict`

同期管理画面では `conflict` を別枠で表示し、ユーザーが以下を選んで処理する。
- サーバー版採用
- 再編集
- 手動再送

---

# CLASS.md レビュー時の不明点・確認事項

## Q53. `work_logs.priority` の有効な固定値を教えてください。

SPEC §5.3 に `priority: TEXT` と定義されていますが、有効な値の列挙がありません。
一覧・詳細画面での表示や絞り込み条件に影響します。

候補:
- `low` / `medium` / `high` / `critical`
- `normal` / `urgent`
- NULL のみ（優先度未使用）
- MVP では未使用・将来拡張

---

## Q54. `session_token` の生成方式（形式・長さ）を教えてください。

CLASS.md では型を `String UQ` としていますが、
実装時にトークンの生成方式が必要です。

候補:
- `secrets.token_urlsafe(32)` など Python 標準ライブラリのランダム文字列
- UUID v4
- 長さの目安（32文字以上？64文字？）

---

## Q55. `work_photos.photo_path` の保存形式を教えてください。

CLASS.md では `String photo_path` としていますが、
保存値の形式が未定義です。

候補:
- サーバー相対パス（例: `/uploads/photos/uuid.jpg`）
- サーバーのフル URL
- ファイル名のみ（ベースURLはクライアントで補完）

---

## Q56. `sync_queue.payload` の JSON スキーマを教えてください。

CLASS.md では `String payload` としていますが、
`operation` ごとに異なる構造になるかを確認します。

現状の想定:
```json
// create
{"log_uuid": "...", "fields": {...全フィールド}}

// update
{"log_uuid": "...", "base_revision": 3, "fields": {...変更フィールドのみ}}

// delete
{"log_uuid": "...", "base_revision": 3}
```

この構造で確定してよいですか？

---
