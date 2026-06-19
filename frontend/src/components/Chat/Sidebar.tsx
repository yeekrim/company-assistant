import { useState, useEffect } from 'react';
import { useAuthStore } from '../../store/authStore';
import { useChatStore } from '../../store/chatStore';
import { chatApi } from '../../services/api';
import DocumentModal from './DocumentModal';
import styles from './Sidebar.module.css';

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const {
    conversations, currentConversationId, loadingConversationId,
    setConversations, setCurrentConversation, setMessages,
    startNewConversation, removeConversation,
  } = useChatStore();

  const [loadingConv, setLoadingConv] = useState<string | null>(null);
  const [deletingConv, setDeletingConv] = useState<string | null>(null);
  const [showDocModal, setShowDocModal] = useState(false);

  useEffect(() => {
    chatApi.listConversations().then(setConversations).catch(() => {});
  }, [setConversations]);

  const handleSelectConversation = async (id: string) => {
    if (id === currentConversationId || loadingConv) return;

    // 로딩 중인 대화로 돌아올 때는 DB 재조회 없이 현재 메시지 유지
    if (id === loadingConversationId) {
      setCurrentConversation(id);
      return;
    }

    setLoadingConv(id);
    try {
      const msgs = await chatApi.getMessages(id);
      setCurrentConversation(id);
      setMessages(msgs.map((m) => ({ ...m, role: m.role as 'user' | 'assistant' })));
    } catch {
      alert('대화를 불러오지 못했습니다.');
    } finally {
      setLoadingConv(null);
    }
  };

  const handleDeleteConversation = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setDeletingConv(id);
    try {
      await chatApi.deleteConversation(id);
      removeConversation(id);
      if (currentConversationId === id) startNewConversation();
    } catch {
      alert('삭제 실패. 다시 시도해주세요.');
    } finally {
      setDeletingConv(null);
    }
  };

  return (
    <>
      <aside className={styles.sidebar}>
        <div className={styles.top}>
          <div className={styles.logo}>{user?.company_name ?? 'AI'} 어시스턴트</div>
          <button className={styles.newChat} onClick={startNewConversation}>+ 새 대화</button>
        </div>

        <div className={styles.middle}>
          {conversations.length === 0 ? (
            <p className={styles.empty}>대화 내역이 없습니다</p>
          ) : (
            <ul className={styles.convList}>
              {conversations.map((conv) => (
                <li
                  key={conv.id}
                  className={`${styles.convItem} ${conv.id === currentConversationId ? styles.convItemActive : ''}`}
                  onClick={() => handleSelectConversation(conv.id)}
                >
                  <span className={styles.convTitle}>
                    {loadingConv === conv.id ? '불러오는 중...' : conv.title}
                  </span>
                  <button
                    className={styles.convDeleteBtn}
                    onClick={(e) => handleDeleteConversation(e, conv.id)}
                    disabled={deletingConv === conv.id}
                    title="대화 삭제"
                  >
                    {deletingConv === conv.id ? '…' : '✕'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {user?.role === 'admin' && (
          <button className={styles.docMgrBtn} onClick={() => setShowDocModal(true)}>
            📄 사내 문서 관리
          </button>
        )}

        <div className={styles.bottom}>
          <div className={styles.userInfo}>
            <div className={styles.userMeta}>
              <span className={styles.userName}>{user?.name}</span>
              {user?.role === 'admin' && <span className={styles.adminBadge}>관리자</span>}
            </div>
            <span className={styles.userEmail}>{user?.email}</span>
            <button className={styles.logoutBtn} onClick={logout}>로그아웃</button>
          </div>
        </div>
      </aside>

      {showDocModal && <DocumentModal onClose={() => setShowDocModal(false)} />}
    </>
  );
}
