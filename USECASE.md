# USECASE.md

## アクター定義

| アクター | 説明 |
|---|---|
| Guest | 未認証ユーザー |
| User | 認証済みの一般ユーザー（role=user） |
| Admin | 管理者（role=admin） |

---

## 1. 認証・アカウント管理

```mermaid
graph LR
  Guest(["👤 Guest"])
  User(["👤 User"])

  subgraph AUTH["認証・アカウント管理"]
    R("新規登録")
    L("ログイン")
    LO("ログアウト")
    CP("パスワード変更")
    SC("セッション確認")
  end

  Guest --> R
  Guest --> L
  User --> LO
  User --> CP
  User --> SC

  R -. 「8文字以上」バリデーション .-> R
  L -. "5回失敗→15分ロック" .-> L
  SC -. "期限切れ→再ログイン要求" .-> SC
```

---

## 2. 作業記録管理

```mermaid
graph LR
  User(["👤 User"])
  Admin(["👤 Admin"])

  subgraph WL["作業記録管理"]
    C("作業記録 新規作成")
    LST("作業記録 一覧表示\n50件ページネーション")
    DT("作業記録 詳細表示")
    ED("作業記録 編集")
    ST("状態変更")
    DEL("作業記録 論理削除")
    FU("フォローアップ期限確認")
    ADEL("削除済み記録参照")
  end

  User --> C
  User --> LST
  User --> DT
  User --> ED
  User --> ST
  User --> DEL
  User --> FU

  Admin --> LST
  Admin --> DT
  Admin --> ST
  Admin --> ADEL

  C -. "equipment_id=NULL 許可\n(memoなど)" .-> C
  DEL -. "deleted_flag=1\ntombstone同期" .-> DEL
  ADEL -. "admin のみ参照可" .-> ADEL
```

---

## 3. 設備・QR

```mermaid
graph LR
  User(["👤 User"])
  Admin(["👤 Admin"])

  subgraph EQ["設備・QR"]
    EL("設備一覧参照")
    ES("設備検索")
    QR("QR読取\n設備自動選択")
    NS("設備なし選択")
    EM("設備マスタ編集\n登録・更新")
  end

  User --> EL
  User --> ES
  User --> QR
  User --> NS

  Admin --> EL
  Admin --> ES
  Admin --> EM

  QR -. "qr_value（設備コード文字列）\nと照合" .-> QR
  QR -. "未登録なら候補表示" .-> QR
  EM -. "初期はDB直接投入\nまたは変換スクリプト" .-> EM
```

---

## 4. オフライン・同期

```mermaid
graph LR
  User(["👤 User"])

  subgraph SYNC["オフライン・同期"]
    OD("オフライン\n下書き保存")
    SP("同期実行 Push\nローカル→サーバー")
    SL("同期実行 Pull\nサーバー→ローカル\nsinceToken差分")
    CC("競合確認\nconflict状態表示")
    RT("失敗レコード 再送")
    SC("セッション確認\n期限切れ時 再ログイン要求")
  end

  User --> OD
  User --> SP
  User --> SL
  User --> CC
  User --> RT

  SP -. "base_revision 送信\n不一致→409 Conflict" .-> CC
  SL -. "tombstone(削除済)も取得" .-> SL
  SP --> SC
  SL --> SC
  OD -. "オフライン中は\n同期しない" .-> OD
```

---

## 5. 管理者専用機能

```mermaid
graph LR
  Admin(["👤 Admin"])

  subgraph ADMUSECASE["管理者専用機能"]
    AR("全記録参照")
    UM("ユーザー管理")
    EM("設備マスタ編集")
    AGG("集計確認")
    ADEL("削除済み記録参照\n監査用")
  end

  Admin --> AR
  Admin --> UM
  Admin --> EM
  Admin --> AGG
  Admin --> ADEL

  UM -. "is_active 変更\nなど" .-> UM
  ADEL -. "tombstone 90日保持" .-> ADEL
```

---

## 6. システム全体（アクター×機能エリア）

```mermaid
graph TB
  Guest(["👤 Guest"])
  User(["👤 User"])
  Admin(["👤 Admin"])

  subgraph SYS["worklog-pwa"]
    A1["認証・アカウント管理"]
    A2["作業記録管理"]
    A3["設備・QR"]
    A4["オフライン・同期"]
    A5["管理者専用機能"]
  end

  Guest --> A1
  User --> A1
  User --> A2
  User --> A3
  User --> A4
  Admin --> A1
  Admin --> A2
  Admin --> A3
  Admin --> A5

  A2 -. "記録所有者＝User\n操作者はcreated_by/updated_byで管理" .-> A2
  A4 -. "sync_queue (IndexedDB)\npending/retrying/failed/conflict/done" .-> A4
```

---

## 7. PWA・固定ページ（非機能）

```mermaid
graph LR
  Anyone(["👤 誰でも"])

  subgraph PWA["PWA・固定ページ"]
    PP("/privacy-policy/")
    CO("/contact/")
    TM("/terms/")
    INST("ホーム画面に追加\nPWA インストール")
    ADS("AdSense 広告表示\nホーム・一覧・詳細")
  end

  Anyone --> PP
  Anyone --> CO
  Anyone --> TM
  Anyone --> INST
  Anyone --> ADS

  ADS -. "入力画面・QR読取・\nカメラ撮影中は非表示" .-> ADS
```
