# Company Assistant

RAG(Retrieval-Augmented Generation) 기반 사내 AI 챗봇. 회사별로 문서를 업로드하면 직원들이 해당 문서를 기반으로 AI와 대화할 수 있습니다.

---

## 유저 플로우

### 관리자 (Admin)

```
로그인
  └─ 사이드바에 "사내 문서 관리" 버튼 표시
       └─ 문서 관리 모달 열기
            ├─ PDF / DOCX / TXT 업로드 (다중 파일 가능)
            │    └─ 텍스트 추출 → 청킹 → 임베딩 → ChromaDB 저장
            └─ 업로드된 문서 목록 확인 / 삭제
  └─ 새 대화 시작 또는 기존 대화 선택
       └─ 질문 입력
            └─ RAG 파이프라인 실행 → 답변 수신
```

### 직원 (Employee)

```
로그인
  └─ 사이드바에 기존 대화 목록 표시
  └─ 새 대화 시작
       └─ 질문 입력
            ├─ 쿼리 임베딩 → ChromaDB 유사도 검색 (Top-10)
            ├─ 이전 대화 히스토리 유사도 필터링 (최근 6턴 중 0.7 이상)
            └─ NVIDIA NIM (Llama 3.1 70B) → 한국어 답변 생성
  └─ 기존 대화 클릭 → 이전 메시지 불러오기
  └─ 대화 hover → X 버튼으로 삭제
  └─ 로그아웃 → 채팅 상태 초기화
```

### 대화 전환 시

```
대화 A에서 질문 전송 (답변 생성 중)
  └─ 대화 B로 전환
       ├─ 대화 A 로딩 말풍선 숨김 (대화 B에는 표시 안 됨)
       └─ 대화 B 메시지 정상 표시
  └─ 대화 A로 복귀
       ├─ 저장된 메시지 복원 (DB 재조회 없음)
       ├─ 로딩 말풍선 재표시
       └─ 답변 도착 시 메시지 추가
```

---

## 시스템 아키텍처

![Architecture](docs/architecture.svg)

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| 프론트엔드 | React 19, TypeScript, Vite 8 |
| 상태 관리 | Zustand |
| HTTP 클라이언트 | Axios |
| 라우팅 | React Router v6 |
| 백엔드 | FastAPI, SQLAlchemy (async) |
| DB | PostgreSQL 16 |
| 벡터 DB | ChromaDB |
| 임베딩 모델 | sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) |
| LLM | NVIDIA NIM (Llama 3.1 70B Instruct, 클라우드) |
| 인증 | JWT (python-jose) |
| 인프라 | Docker Compose |

---

## 프로젝트 구조

```
company-assistant/
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Chat/
│       │   │   ├── Sidebar.tsx        # 대화목록, 문서관리, 프로필
│       │   │   ├── ChatWindow.tsx     # 메시지 목록
│       │   │   ├── MessageBubble.tsx  # 메시지 말풍선
│       │   │   ├── InputBox.tsx       # 메시지 입력창
│       │   │   └── DocumentModal.tsx  # 문서 관리 모달
│       │   └── Layout/
│       │       └── ProtectedRoute.tsx
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   └── ChatPage.tsx
│       ├── store/
│       │   ├── authStore.ts           # 인증 상태 (persist)
│       │   └── chatStore.ts           # 채팅 상태
│       ├── services/
│       │   └── api.ts                 # authApi / chatApi / documentApi
│       └── types/
│           └── index.ts
│
└── backend/
    ├── app/
    │   ├── api/
    │   │   ├── auth.py                # POST /api/auth/login
    │   │   ├── chat.py                # POST /api/chat, GET /api/chat/conversations
    │   │   └── documents.py           # POST/GET/DELETE /api/documents
    │   ├── core/
    │   │   ├── config.py
    │   │   ├── database.py
    │   │   └── security.py            # JWT, bcrypt
    │   ├── models/
    │   │   ├── db_models.py           # Company, User, Conversation, Message
    │   │   └── schemas.py
    │   ├── rag/
    │   │   ├── chunker.py             # 텍스트 추출 및 청킹
    │   │   ├── embedder.py            # sentence-transformers
    │   │   ├── retriever.py           # ChromaDB 검색/저장/삭제
    │   │   ├── generator.py           # NVIDIA NIM LLM 호출
    │   │   └── pipeline.py            # RAG 전체 파이프라인
    │   ├── services/
    │   │   └── document_service.py
    │   └── main.py
    ├── seed.py                        # 초기 데이터 시딩
    ├── requirements.txt
    └── .env
```

---

## 시작하기

### 사전 요구사항

- Docker Desktop
- Python 3.12
- Node.js 20+
- NVIDIA NIM API 키 (build.nvidia.com 에서 발급)

### 1. 인프라 실행

```bash
docker-compose up -d
```

PostgreSQL (5432), ChromaDB (8001) 실행

### 2. 환경 변수 설정

`backend/.env` 파일에 아래 항목 추가:

```
NVIDIA_API_KEY=your_api_key_here
```

### 3. 백엔드

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# DB 초기화 및 시딩
python seed.py

# 서버 실행
uvicorn app.main:app --reload
```

### 4. 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 http://localhost:5173 접속

---

## 구현 현황

### 백엔드
- [x] JWT 인증 (로그인 / 토큰 발급)
- [x] 회사별 다중 테넌트 구조 (Company / User)
- [x] 역할 기반 접근 제어 (admin / employee)
- [x] 문서 업로드 API (PDF / DOCX / TXT)
- [x] RAG 파이프라인 (청킹 → 임베딩 → 검색 → 생성)
- [x] PDF 표 추출 개선 (헤더 포함 구조화 텍스트 변환)
- [x] 채팅 API (대화 생성 / 메시지 저장)
- [x] 대화 목록 / 메시지 조회 API
- [x] 대화 삭제 API
- [x] 문서 목록 / 삭제 API
- [x] LLM 모델 최적화 (llama3.2 → gemma3:4b → NVIDIA NIM Llama 3.1 70B Instruct)
- [x] 프롬프트 강화 (할루시네이션 방지 / 언어 혼용 방지 / 톤 설정)
- [x] 대화 히스토리 반영 (최근 6턴 중 유사도 0.7 이상 턴만 필터링하여 컨텍스트 구성)
- [x] RAG 검색 범위 확장 (top_k 5 → 10)

### 프론트엔드
- [x] 로그인 화면
- [x] Protected Route
- [x] 사이드바 (대화 목록 / 새 대화 / 대화 삭제)
- [x] 채팅 UI (말풍선 / 자동 스크롤 / 타이핑 애니메이션)
- [x] 실제 백엔드 API 연결
- [x] 관리자 전용 문서 관리 모달 (업로드 / 삭제)
- [x] 회사 이름 표시 ({회사명} 어시스턴트)
- [x] 로그아웃 시 채팅 상태 초기화
- [x] 대화별 로딩 상태 관리 (대화 전환 중 말풍선 / 메시지 보존)
