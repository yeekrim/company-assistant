# Company Assistant

[한국어](README.ko.md)

社内文書をもとに答える RAG（Retrieval-Augmented Generation）チャットボットです。会社ごとに文書をアップロードすると、その会社の社員だけがその文書をもとに AI と会話できます。

フロントエンド（React／TypeScript）からバックエンド（FastAPI）、DB、認証まで一人で作りました。

---

## できること

- **会社ごとのデータ分離**：ユーザー・会話・ベクトル検索・表データをすべて会社単位で分け、他社の文書は検索されません
- **権限による画面と API の出し分け**：管理者だけが文書のアップロード・削除・施行日の変更をできます（JWT 認証）
- **文書のアップロードと検索**：PDF／DOCX／TXT を文章単位に分割してベクトル化し、質問に近い部分を探して回答します
- **表の構造化保存**：PDF の表を会社ごとの DuckDB に行・列のまま保存します。`0` で始まるコード値や重複した列名も壊さずに残します
- **施行日に合わせた回答**：同じ規程の新旧版を施行日つきで登録すると、「2020年には〜」のような過去の時点の質問にはその時点で有効だった版から答えます
- **会話履歴**：直近 6 件のメッセージのうち質問と類似度 0.7 以上のものだけを文脈に入れ、関係ない過去の会話で回答がぶれないようにしています
- **会話の切り替え**：回答の生成中に別の会話へ移っても、メッセージとローディング表示が混ざりません

---

## 技術スタック

| 領域 | 技術 |
|------|------|
| フロントエンド | React 19, TypeScript, Vite, Zustand, Axios, React Router |
| バックエンド | FastAPI, SQLAlchemy（async） |
| DB | PostgreSQL 16（ユーザー・会話）、ChromaDB（ベクトル）、DuckDB（表データ） |
| 埋め込みモデル | sentence-transformers（paraphrase-multilingual-MiniLM-L12-v2） |
| LLM | NVIDIA NIM（Nemotron 3 Super 120B A12B） |
| 認証 | JWT（python-jose）, bcrypt |
| インフラ | Docker Compose |

---

## 検索・回答の評価

感覚ではなく数値で改善を判断するため、評価用のハーネスを `experiments/` に置いています。

- **検索評価（`experiments/retrieval_eval`）**：実際の公共機関の規程や業務推進費の文書で正解ラベルを作り、nDCG で検索方式を比べます
- **施行日機能の評価**：同じ規程の新旧 3 版で 12 問（現在の質問 6、過去の時点の質問 6）を聞いたところ、正答数は施行日なし 4/12 → 施行日あり 6/12 でした。過去の時点の質問はまだ 2/6 にとどまっていて、改善の余地があります
- **表計算の質問（`experiments/sql_harness`）**：表を SQL で引いて答える方式をいくつか試し、正答率・応答時間・トークン数を比べています。今のところ既存の方式を上回るものがなく、本体には入れていません

---

## 実行方法

### 必要なもの

- Docker Desktop
- Python 3.12
- Node.js 20+
- NVIDIA NIM の API キー（build.nvidia.com で発行）

### 1. DB を起動

```bash
cp .env.example .env          # POSTGRES_PASSWORD を設定
docker compose up -d          # PostgreSQL (5432), ChromaDB (8001)
```

### 2. バックエンド

```bash
cd backend
cp .env.example .env          # DATABASE_URL, SECRET_KEY, NVIDIA_API_KEY を設定
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python seed.py                # デモ用の会社・ユーザーを作成
uvicorn app.main:app --reload
```

`seed.py` は 2 社分のデモユーザーを作ります。ログイン ID は `社員番号@ドメイン`（例：管理者 `admin@virtual.co.kr`、社員 `018100002@virtual.co.kr`）、パスワードはすべて `pass1234` です。

### 3. フロントエンド

```bash
cd frontend
npm install
npm run dev
```

ブラウザで http://localhost:5173 を開きます。

### テスト

```bash
cd backend
pytest
```

---

## ディレクトリ構成

```
company-assistant/
├── frontend/src/
│   ├── components/Chat/     # サイドバー、チャット画面、文書管理モーダル
│   ├── pages/               # ログイン、チャット
│   ├── store/               # 認証・チャットの状態（Zustand）
│   └── services/api.ts      # API クライアント
├── backend/
│   ├── app/
│   │   ├── api/             # auth / chat / documents
│   │   ├── core/            # 設定、DB 接続、JWT
│   │   ├── models/          # Company, User, Conversation, Message
│   │   ├── rag/             # 分割・埋め込み・検索・生成・施行日処理
│   │   ├── tables/          # 表の抽出と DuckDB への保存
│   │   └── services/
│   ├── tests/
│   └── seed.py
└── experiments/             # 検索・回答の評価ハーネス
```
