# USECASE.md

## アクター定義

| アクター | 説明 |
|---|---|
| Guest | 未認証ユーザー |
| User | 認証済みの一般ユーザー（role=user） |
| Admin | 管理者（role=admin） |

> Admin の認証フロー（ログイン・ログアウト・パスワード変更）は User と共通。専用ログイン画面は持たない。

---

## 1. 認証・アカウント管理

```mermaid
graph LR
  Guest(["👤 Guest"])
  User(["👤 User"])
  Admin(["👤 Admin"])

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
  Admin --> L
  Admin --> LO
  Admin --> CP
  Admin --> SC

  R -. "8文字以上バリデーション\n登録直後 is_active=1（即時利用可）" .-> R
  L -. "5回失敗→15分ロック\nlogin_id単位+IP単位" .-> L
  SC -. "期限切れ→再ログイン要求\nスライディング7日" .-> SC
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
    LSTF("削除済みフィルタ\n「削除済みを含める」\n「削除済みのみ表示」")
    DT("作業記録 詳細表示")
    ED("作業記録 編集")
    ST("状態変更")
    DEL("作業記録 論理削除\ndeleted_flag=1")
    FU("フォローアップ\n期限確認・表示")
  end

  User --> C
  User --> LST
  User --> DT
  User --> ED
  User --> ST
  User --> DEL
  User --> FU

  Admin --> C
  Admin --> LST
  Admin --> LSTF
  Admin --> DT
  Admin --> ED
  Admin --> ST
  Admin --> DEL
  Admin --> FU

  LST --> LSTF
  LSTF -. "Admin のみ利用可\n専用ゴミ箱ページは作らない" .-> LSTF
  LST -. "User=自分の記録のみ\nAdmin=全ユーザーの記録" .-> LST
  C -. "equipment_id=NULL 許可（memoなど）\nuser_id=作成者本人\ncreated_by/updated_by=操作者" .-> C
  ED -. "Admin は全ユーザーの記録を編集可\nupdated_by=Admin 自身" .-> ED
  DEL -. "tombstone同期 revision+1\ndeleted_at/deleted_by記録\nAdmin は全記録を削除可" .-> DEL
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
  Admin --> QR
  Admin --> NS
  Admin --> EM

  QR -. "qr_value（設備コード文字列）と照合\n未登録+オンライン→by_qr問い合わせ\n未登録+オフライン→「設備未登録または未同期」表示" .-> QR
  EM -. "初期はDB直接投入または変換スクリプト\nMVP後に equipment_import.cgi 追加予定\n管理系操作なのでオンライン必須" .-> EM
```

---

## 4. オフライン・同期（作業記録系）

```mermaid
graph LR
  User(["👤 User"])
  Admin(["👤 Admin"])

  subgraph SYNC["オフライン・同期（作業記録系）"]
    OD("オフライン\n下書き保存")
    SP("同期 Push\nローカル→サーバー\nsync_queue送信")
    SL("同期 Pull（記録）\nサーバー→ローカル\nsinceToken差分")
    EMS("設備マスタ同期\nequipment sync_pull")
    CC("競合確認\nconflict状態表示\n同期管理画面")
    RT("失敗レコード 再送")
    SC("セッション確認\n期限切れ→再ログイン要求\n復帰後 未同期データ送信")
  end

  User --> OD
  User --> SP
  User --> SL
  User --> EMS
  User --> CC
  User --> RT

  Admin --> OD
  Admin --> SP
  Admin --> SL
  Admin --> EMS
  Admin --> CC
  Admin --> RT

  SP -. "base_revision送信\n不一致→409 Conflict\n→sync_queue.status=conflict" .-> CC
  SL -. "tombstone(削除済)も取得\nupsertで重複排除" .-> SL
  EMS -. "ログイン時: 自動差分同期\n同期ボタン時: 差分同期\nQR読取前: ローカルキャッシュ使用" .-> EMS
  SP --> SC
  SL --> SC
  OD -. "オフライン中は同期しない\nセッション期限切れでも\n下書き継続可能" .-> OD
```

---

## 5. 管理者専用機能（オンライン必須）

```mermaid
graph LR
  Admin(["👤 Admin"])

  subgraph ADMUSECASE["管理者専用機能（オンライン必須）"]
    UM("ユーザー管理")
    UML("ユーザー一覧表示")
    UMA("is_active 変更\n有効化 / 無効化")
    UMR("role 変更\nuser⇔admin 昇降格")
    UMP("仮パスワード再設定\n管理画面で一時表示")
    EM("設備マスタ編集\n登録・更新")
    AGG("集計ダッシュボード")
  end

  Admin --> UM
  UM --> UML
  UM --> UMA
  UM --> UMR
  UM --> UMP

  Admin --> EM
  Admin --> AGG

  UMA -. "自身を is_active=0 にするのは禁止" .-> UMA
  UMR -. "最後の1人の admin を\nuser に降格するのは禁止" .-> UMR
  UMP -. "旧パスワード無効化\n次回ログイン後に変更推奨\nメール送信は MVP 外" .-> UMP
  AGG -. "期間別件数/status別/record_type別\nフォローアップ超過件数\nユーザー別・設備別(上位N件)\nグラフ高度化・CSV出力はMVP外" .-> AGG
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
    A4["オフライン・同期\n（作業記録系）"]
    A5["管理者専用機能\n（オンライン必須）"]
    A6["公開ページ\nトップ・/guide/・固定ページ"]
  end

  Guest --> A1
  Guest --> A6
  User --> A1
  User --> A2
  User --> A3
  User --> A4
  Admin --> A1
  Admin --> A2
  Admin --> A3
  Admin --> A4
  Admin --> A5

  A2 -. "User=自分の記録のみ\nAdmin=全記録（作成・編集・削除含む）\nuser_id=所有者 / updated_by=操作者" .-> A2
  A4 -. "sync_queue(IndexedDB)\npending/retrying/failed/conflict/done\n設備マスタ同期は3段階ルール" .-> A4
  A6 -. "AdSense 表示\nログイン・登録フォームには非表示" .-> A6
```

---

## 7. 公開ページ・PWA・AdSense

```mermaid
graph LR
  Guest(["👤 Guest"])
  Anyone(["👤 誰でも\n(Guest/User/Admin)"])

  subgraph PUB["公開ページ・PWA・AdSense"]
    TOP("トップページ\nindex.html\nサービス紹介・導線")
    GUIDE("/guide/\n利用案内ページ")
    PP("/privacy-policy/")
    CO("/contact/")
    TM("/terms/")
    INST("ホーム画面に追加\nPWA インストール")
    ADS_PUB("AdSense\n公開ページ")
    ADS_APP("AdSense\nホーム・一覧・詳細")
  end

  Guest --> TOP
  Guest --> GUIDE
  Guest --> PP
  Guest --> CO
  Guest --> TM
  Anyone --> INST
  Guest --> ADS_PUB
  Anyone --> ADS_APP

  TOP -. "ログイン済みでも自動リダイレクトなし\nヘッダーに「ホームへ」リンク表示" .-> TOP
  ADS_PUB -. "表示: トップ・/guide/・固定ページ\n非表示: ログイン・登録フォーム" .-> ADS_PUB
  ADS_APP -. "非表示: 作業入力中・QR読取中・カメラ撮影中" .-> ADS_APP
```
