import type { Message } from '../../types';
import { useAuthStore } from '../../store/authStore';
import styles from './MessageBubble.module.css';

export default function MessageBubble({ message }: { message: Message }) {
  const user = useAuthStore((s) => s.user);
  const isUser = message.role === 'user';

  return (
    <div className={`${styles.wrapper} ${isUser ? styles.userWrapper : styles.assistantWrapper}`}>
      {!isUser && (
        <div className={styles.avatar}>AI</div>
      )}
      <div className={`${styles.bubble} ${isUser ? styles.userBubble : styles.assistantBubble}`}>
        {!isUser && <span className={styles.senderName}>{user?.company_name ?? 'AI'} 어시스턴트</span>}
        <p className={styles.content}>{message.content}</p>
        {!isUser && message.sources && message.sources.length > 0 && (
          <details className={styles.sources}>
            <summary className={styles.sourcesSummary}>출처 문서 {message.sources.length}건</summary>
            <ol className={styles.sourceList}>
              {message.sources.map((s, i) => (
                <li key={i} className={styles.sourceItem}>
                  <div className={styles.sourceMeta}>
                    {s.source} · 시행일 {s.effective_date}
                  </div>
                  <pre className={styles.sourceText}>{s.text}</pre>
                </li>
              ))}
            </ol>
          </details>
        )}
      </div>
      {isUser && (
        <div className={`${styles.avatar} ${styles.userAvatar}`}>
          {user?.name?.[0] ?? 'U'}
        </div>
      )}
    </div>
  );
}
