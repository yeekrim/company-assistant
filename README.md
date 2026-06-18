# Company Assistant

RAG(Retrieval-Augmented Generation) 기반 사내 AI 챗봇

## 기술 스택

| 영역 | 기술 |
|------|------|
| 프론트엔드 | React, TypeScript, Vite |
| 백엔드 | FastAPI (예정) |
| 상태 관리 | Zustand |
| HTTP 클라이언트 | Axios |
| 라우팅 | React Router v6 |
| 벡터 DB | Chroma / Qdrant (예정) |
| LLM | Claude API (예정) |

## 프로젝트 구조

```
company-assistant/
├── frontend/               # React 앱
│   └── src/
│       ├── components/     # 공통 컴포넌트
│       ├── pages/          # 페이지 (Login, Chat)
│       ├── store/          # Zustand 상태 관리
│       ├── services/       # API 통신
│       └── types/          # TypeScript 타입 정의
└── backend/                # FastAPI 앱 (예정)
```

## 시작하기

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 http://localhost:5173 접속

## 구현 현황

- [x] 로그인 화면
- [x] JWT 인증 상태 관리 (localStorage 영속)
- [x] Protected Route (비인증 시 로그인 리다이렉트)
- [ ] 채팅 UI
- [ ] 문서 업로드
- [ ] FastAPI 백엔드
- [ ] RAG 파이프라인
