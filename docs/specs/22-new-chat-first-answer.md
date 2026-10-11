# #22 새 대화 첫 질문의 답변과 로딩 표시가 나오지 않음

## 문제
새 대화에서 첫 질문을 보내면 로딩 표시가 나오지 않고, 응답이 와도 답변이 화면에 추가되지 않는다.

## 원인
- `InputBox`가 `setLoading(true, null)`을 호출 → `loadingConversationId = null ?? currentConversationId(null)` = `null` → 로딩 표시 없음, 입력창도 잠기지 않음(중복 전송 가능)
- 응답 후 `currentConversationId(null) === res.conversation_id` 비교가 거짓 → 답변을 추가하지 않음
- 이어서 현재 대화가 새 id로 바뀌어, 같은 대화를 클릭해도 다시 불러오지 않음

## 재현 근거
chatStore 로직을 그대로 실행해 첫 질문 흐름을 재현 → 응답 후 messages가 `['user']`만 남음. (실제 브라우저 재현은 미확인)

## 범위
- 포함: `frontend/src/store/chatStore.ts`, `frontend/src/components/Chat/InputBox.tsx` — 새 대화 요청을 식별할 수 있게 로딩 상태 처리, 응답 시 답변 추가
- 제외: 대화 전환 로직 재설계

## 검증
- 같은 store 재현 스크립트로 첫 질문·대화 전환 시나리오 확인
- `npm run lint`, `npm run build`
