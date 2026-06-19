import { useEffect, useRef } from 'react';
import { useChatStore } from '../../store/chatStore';
import MessageBubble from './MessageBubble';
import styles from './ChatWindow.module.css';

export default function ChatWindow() {
  const { messages, loadingConversationId, currentConversationId } = useChatStore();
  const isLoading = loadingConversationId !== null && loadingConversationId === currentConversationId;
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  if (messages.length === 0) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyIcon}>💬</div>
        <h2 className={styles.emptyTitle}>무엇이든 물어보세요</h2>
        <p className={styles.emptyDesc}>사내 문서를 기반으로 정확한 답변을 드립니다</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.messageList}>
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isLoading && (
          <div className={styles.typingWrapper}>
            <div className={styles.avatar}>AI</div>
            <div className={styles.typing}>
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
