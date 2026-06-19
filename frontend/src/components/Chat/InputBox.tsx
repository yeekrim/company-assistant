import { useState, useRef } from 'react';
import { useChatStore } from '../../store/chatStore';
import { chatApi } from '../../services/api';
import type { Message } from '../../types';
import styles from './InputBox.module.css';

export default function InputBox() {
  const [text, setText] = useState('');
  const { loadingConversationId, currentConversationId, addMessage, setLoading, setCurrentConversation, addConversation } = useChatStore();
  const isLoading = loadingConversationId !== null;
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async () => {
    const content = text.trim();
    if (!content || isLoading) return;

    // 요청 시점의 conversationId 고정
    const requestedConversationId = currentConversationId;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    addMessage(userMsg);
    setText('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    setLoading(true, requestedConversationId);

    try {
      const res = await chatApi.sendMessage(content, requestedConversationId ?? undefined);

      // 응답이 왔을 때 여전히 같은 대화를 보고 있는 경우만 메시지 추가
      const stillOnSameConversation =
        useChatStore.getState().currentConversationId === (res.conversation_id ?? requestedConversationId);

      if (stillOnSameConversation) {
        const assistantMsg: Message = {
          id: res.id,
          role: 'assistant',
          content: res.content,
          created_at: res.created_at,
        };
        addMessage(assistantMsg);
      }

      // 새 대화였으면 conversation_id 세팅 + 사이드바 목록에 추가
      if (!requestedConversationId) {
        setCurrentConversation(res.conversation_id);
        addConversation({
          id: res.conversation_id,
          title: content.slice(0, 30),
          created_at: res.created_at,
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.inputRow}>
        <textarea
          ref={textareaRef}
          className={styles.textarea}
          placeholder="메시지를 입력하세요 (Shift+Enter: 줄바꿈)"
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={isLoading}
        />
        <button
          className={styles.sendBtn}
          onClick={handleSubmit}
          disabled={!text.trim() || isLoading}
        >
          ↑
        </button>
      </div>
      <p className={styles.hint}>Enter로 전송 · Shift+Enter로 줄바꿈</p>
    </div>
  );
}
