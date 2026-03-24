# CLASS.md

## 凡例

| 記号 | 意味 |
|---|---|
| `PK` | 主キー |
| `FK` | 外部キー（論理） |
| `UQ` | ユニーク |
| `NULL` | NULL 許可 |
| `<<enum>>` | 列挙型 |
| `<<IndexedDB>>` | クライアント側ストア |
| `<<SQLite>>` | サーバー側テーブル |

---

## 1. 列挙型

```mermaid
classDiagram
  class Role {
    <<enum>>
    user
    admin
  }

  class RecordType {
    <<enum>>
    inspection
    repair
    trouble
    maintenance
    memo
  }

  class WorkStatus {
    <<enum>>
    draft
    open
    in_progress
    done
    pending_parts
  }

  class SyncState {
    <<enum>>
    local_only
    dirty
    synced
    failed
    conflict
  }

  class SyncQueueStatus {
    <<enum>>
    pending
    retrying
    failed
    conflict
    done
  }

  class SyncOperation {
    <<enum>>
    create
    update
    delete
  }

  class Priority {
    <<enum>>
    low
    medium
    high
    critical
  }
```

---

## 2. サーバー側クラス図（SQLite）

### 2.1 ユーザー・認証

```mermaid
classDiagram
  class User {
    <<SQLite>>
    +int id PK
    +String login_id UQ
    +String password_hash
    +String display_name
    +String email NULL
    +String role
    +int is_active
    +String created_at
    +String updated_at
    +String last_login_at NULL
  }

  class Session {
    <<SQLite>>
    +int id PK
    +int user_id FK
    +String session_token UQ
    +String expires_at
    +String created_at
    +String last_access_at
  }

  note for Session "session_token: secrets.token_urlsafe(32)\n約43文字のURL-safeランダム文字列\nスライディング有効期限: 最終操作から7日"

  class LoginAttempt {
    <<SQLite>>
    +int id PK
    +String login_id
    +String ip_address
    +String attempted_at
    +int success
  }

  User "1" --> "0..*" Session : user_id
  User "1" ..> "0..*" LoginAttempt : login_id（論理参照）
```

---

### 2.2 業務データ

```mermaid
classDiagram
  class Equipment {
    <<SQLite>>
    +int id PK
    +String equipment_code UQ
    +String equipment_name
    +String location NULL
    +String line_name NULL
    +String model NULL
    +String maker NULL
    +String qr_value NULL
    +int is_active
    +String created_at
    +String updated_at
  }

  class WorkLog {
    <<SQLite>>
    +int id PK
    +String log_uuid UQ
    +int user_id FK
    +int equipment_id FK NULL
    +String record_type
    +String status
    +String title
    +String symptom NULL
    +String work_detail NULL
    +String result NULL
    +String priority NULL
    +String recorded_at
    +int needs_followup
    +String followup_due NULL
    +String server_updated_at
    +int revision
    +int created_by FK
    +int updated_by FK
    +int deleted_flag
    +String deleted_at NULL
    +int deleted_by FK NULL
  }

  note for WorkLog "priority: low/medium/high/critical, NULL可\nserver_updated_at: UTC ISO 8601\nrevision: 競合判定の唯一の基準"

  class WorkPhoto {
    <<SQLite>>
    +int id PK
    +String log_uuid FK
    +String photo_path
    +String caption NULL
    +String taken_at NULL
    +String created_at
  }

  note for WorkPhoto "photo_path: サーバー相対パス\n例: /uploads/photos/2026/03/uuid-01.jpg\nMVP では未使用（Phase 5）。テーブルのみ先行作成"

  Equipment "0..1" --> "0..*" WorkLog : equipment_id（NULL可）
  WorkLog "1" --> "0..*" WorkPhoto : log_uuid
```

---

### 2.3 サーバー全体関係

```mermaid
classDiagram
  class User {
    <<SQLite>>
    +int id PK
    +String login_id UQ
    +String role
    +int is_active
  }

  class Equipment {
    <<SQLite>>
    +int id PK
    +String equipment_code UQ
    +String qr_value NULL
    +int is_active
  }

  class WorkLog {
    <<SQLite>>
    +int id PK
    +String log_uuid UQ
    +int user_id FK
    +int equipment_id FK NULL
    +int created_by FK
    +int updated_by FK
    +int deleted_by FK NULL
    +int revision
    +int deleted_flag
  }

  class WorkPhoto {
    <<SQLite>>
    +int id PK
    +String log_uuid FK
  }

  class Session {
    <<SQLite>>
    +int id PK
    +int user_id FK
    +String session_token UQ
    +String expires_at
  }

  class LoginAttempt {
    <<SQLite>>
    +int id PK
    +String login_id
    +String ip_address
    +int success
  }

  User "1" --> "0..*" WorkLog : user_id（所有者）
  User "1" --> "0..*" WorkLog : created_by（作成者）
  User "1" --> "0..*" WorkLog : updated_by（最終更新者）
  User "1" --> "0..*" WorkLog : deleted_by（削除者）
  Equipment "0..1" --> "0..*" WorkLog : equipment_id
  WorkLog "1" --> "0..*" WorkPhoto : log_uuid
  User "1" --> "0..*" Session : user_id
  User "1" ..> "0..*" LoginAttempt : login_id
```

---

## 3. クライアント側クラス図（IndexedDB）

```mermaid
classDiagram
  class WorkLogLocal {
    <<IndexedDB>>
    +String log_uuid PK
    +int user_id
    +int equipment_id NULL
    +String record_type
    +String status
    +String title
    +String symptom NULL
    +String work_detail NULL
    +String result NULL
    +String priority NULL
    +String recorded_at
    +int needs_followup
    +String followup_due NULL
    +String local_updated_at NULL
    +String server_updated_at NULL
    +int revision
    +String sync_state
    +int created_by
    +int updated_by
    +int deleted_flag
    +String deleted_at NULL
    +int deleted_by NULL
  }

  note for WorkLogLocal "local_updated_at / sync_state はクライアント専用\nオフライン新規直後は revision=0, server_updated_at=NULL, sync_state=local_only\ncreate 成功後は revision>=1, sync_state=synced"

  class EquipmentCache {
    <<IndexedDB>>
    +int id PK
    +String equipment_code UQ
    +String equipment_name
    +String location NULL
    +String line_name NULL
    +String model NULL
    +String maker NULL
    +String qr_value NULL
    +int is_active
    +String updated_at
  }

  class SyncQueue {
    <<IndexedDB>>
    +String queue_id PK
    +String entity_type
    +String entity_id
    +String operation
    +String payload
    +String status
    +int retry_count
    +String last_error_code NULL
    +String last_error_message NULL
    +String last_error_at NULL
    +String last_attempt_at NULL
    +String created_at
  }

  note for SyncQueue "payload: JSON文字列\ncreate: log_uuid + fields\nupdate: log_uuid + base_revision + fields\ndelete: log_uuid + base_revision\nuser_id/revision 等はAPI側が管理\nsync_state はクライアント専用で payload に含めない"

  class SyncMeta {
    <<IndexedDB>>
    +String key PK
    +String value
  }

  SyncQueue "0..*" --> "1" WorkLogLocal : entity_id = log_uuid
  SyncQueue --> SyncOperation : operation
  SyncQueue --> SyncQueueStatus : status
  WorkLogLocal --> SyncState : sync_state
  WorkLogLocal --> RecordType : record_type
  WorkLogLocal --> WorkStatus : status
```

---

## 4. サーバー ↔ クライアント 対応関係

```mermaid
classDiagram
  class WorkLog {
    <<SQLite（サーバー）>>
    +String log_uuid
    +int revision
    +String server_updated_at
  }

  class WorkLogDTO {
    <<API DTO（サーバー返却）>>
    +String log_uuid
    +int user_id
    +int equipment_id NULL
    +String record_type
    +String status
    +String title
    +String symptom NULL
    +String work_detail NULL
    +String result NULL
    +String priority NULL
    +String recorded_at
    +int needs_followup
    +String followup_due NULL
    +int revision
    +String server_updated_at
    +int created_by
    +int updated_by
    +int deleted_flag
    +String deleted_at NULL
    +int deleted_by NULL
  }

  class WorkLogLocal {
    <<IndexedDB（クライアント）>>
    +String log_uuid
    +int revision
    +String server_updated_at NULL
    +String local_updated_at NULL
    +String sync_state
  }

  class EquipmentDB {
    <<SQLite（サーバー）>>
    +int id
    +String equipment_code
    +String updated_at
    +int is_active
  }

  class EquipmentCache {
    <<IndexedDB（クライアント）>>
    +int id
    +String equipment_code
    +String updated_at
    +int is_active
  }

  WorkLog "レスポンス" --> WorkLogDTO : API返却へ変換
  WorkLogDTO "保存" --> WorkLogLocal : sync_pull 後に変換して upsert
  EquipmentDB "同期" <--> EquipmentCache : equipment sync_pull（updated_at で差分）

  note for WorkLogDTO "server_updated_at / revision / deleted_flag はサーバー事実\nlocal_updated_at / sync_state は持たない"
  note for WorkLogLocal "sync_pull で受けた DTO を保存\n既存 conflict は維持、通常は synced"
```

---

## 5. sync_push / sync_pull ペイロード構造

```mermaid
classDiagram
  class SyncPushItem {
    +String operation
    +SyncPushEntity entity
  }

  class SyncPushEntityCreate {
    +String log_uuid
    +SyncPushFields fields
  }

  class SyncPushEntityUpdate {
    +String log_uuid
    +int base_revision
    +SyncPushFields fields
  }

  class SyncPushEntityDelete {
    +String log_uuid
    +int base_revision
  }

  class SyncPushFields {
    +int equipment_id NULL
    +String record_type
    +String status
    +String title
    +String symptom NULL
    +String work_detail NULL
    +String result NULL
    +String priority NULL
    +String recorded_at
    +int needs_followup
    +String followup_due NULL
  }

  class SyncPushResult {
    +String log_uuid
    +String status
    +int revision NULL
    +int server_revision NULL
    +Object server_entity NULL
    +String message NULL
  }

  class SyncPullResponse {
    +String status
    +SyncPullData data
  }

  class WorkLogDTO {
    +String log_uuid
    +int revision
    +String server_updated_at
    +int deleted_flag
  }

  class SyncPullData {
    +WorkLogDTO[] items
    +String next_since_token
  }

  SyncPushItem --> SyncPushEntityCreate : operation=create
  SyncPushItem --> SyncPushEntityUpdate : operation=update
  SyncPushItem --> SyncPushEntityDelete : operation=delete
  SyncPushEntityCreate "1" --> "1" SyncPushFields : fields
  SyncPushEntityUpdate "1" --> "1" SyncPushFields : fields（変更項目のみ）
  SyncPullResponse "1" --> "1" SyncPullData : data
  SyncPullData "1" --> "0..*" WorkLogDTO : items

  note for SyncPushFields "禁止項目（API側が管理）:\nuser_id / created_by / updated_by\ndeleted_* / server_updated_at\nrevision\nsync_state はクライアント専用"
  note for SyncPushEntityUpdate "base_revision 必須\nAPI側でrevision check\n成功時 revision = revision + 1"
  note for SyncPushEntityDelete "物理削除ではない\nAPI側でtombstone更新:\ndeleted_flag=1, deleted_at=now\ndeleted_by=current_user_id\nrevision=revision+1\nserver_updated_at=now"
  note for SyncPullData "items は WorkLogDTO\nクライアントで WorkLogLocal に変換して保存"
```

---

## 6. 型まとめ

### WorkLog.record_type
```mermaid
classDiagram
  class RecordType {
    <<enum>>
    inspection : 点検
    repair : 修理
    trouble : 不具合
    maintenance : 保守
    memo : メモ（設備なし可）
  }
```

### WorkLog.status
```mermaid
classDiagram
  class WorkStatus {
    <<enum>>
    draft : 下書き
    open : 未対応
    in_progress : 対応中
    done : 完了
    pending_parts : 部品待ち
  }
```

### WorkLog.sync_state（クライアント）
```mermaid
classDiagram
  class SyncState {
    <<enum>>
    local_only : 未送信（新規オフライン）
    dirty : 変更あり・未反映
    synced : サーバーと一致
    failed : 送信失敗
    conflict : 競合（手動解決必要）
  }
```

### SyncQueue.status / operation
```mermaid
classDiagram
  class SyncQueueStatus {
    <<enum>>
    pending : 未送信
    retrying : 再送中
    failed : 失敗（自動再送対象）
    conflict : 競合（手動解決のみ）
    done : 完了
  }

  class SyncOperation {
    <<enum>>
    create : 新規作成（INSERT）
    update : 更新（UPDATE + revision check）
    delete : 論理削除（tombstone 更新）
  }
```

### WorkLog.priority
```mermaid
classDiagram
  class Priority {
    <<enum>>
    low : 低
    medium : 中
    high : 高
    critical : 緊急
  }
```

> NULL 許可（「未設定」を意味する）。MVP では入力必須にしない。
> 一覧の絞り込み対象には含めない。詳細画面では表示可。

### Session.session_token 生成方式
- `secrets.token_urlsafe(32)`（Python 標準ライブラリ）
- 約 43 文字の URL-safe ランダム文字列
- DB 上は `TEXT UNIQUE`

### WorkPhoto.photo_path 保存形式
- サーバー相対パスで保存（例: `/uploads/photos/2026/03/uuid-01.jpg`）
- フル URL は保存しない
- クライアントは API ベース URL に連結して表示する
