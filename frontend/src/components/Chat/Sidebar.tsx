import { useRef, useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '../../store/authStore';
import { documentApi } from '../../services/api';
import styles from './Sidebar.module.css';

interface Doc {
  name: string;
  chunks: number;
}

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [deletingDoc, setDeletingDoc] = useState<string | null>(null);

  const loadDocs = useCallback(async () => {
    if (user?.role !== 'admin') return;
    try {
      const list = await documentApi.list();
      setDocs(list);
    } catch {
      // ChromaDB 연결 실패 등 무시
    }
  }, [user?.role]);

  useEffect(() => {
    loadDocs();
  }, [loadDocs]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    e.target.value = '';
    setUploading(true);
    try {
      const res = await documentApi.upload(files);
      if (res.errors.length > 0) {
        const errNames = res.errors.map((e) => e.file).join(', ');
        alert(`업로드 실패: ${errNames}`);
      } else {
        alert(`${res.uploaded.length}개 파일 업로드 완료`);
      }
      await loadDocs();
    } catch {
      alert('업로드 실패. 다시 시도해주세요.');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docName: string) => {
    if (!confirm(`"${docName}" 문서를 삭제할까요?`)) return;
    setDeletingDoc(docName);
    try {
      await documentApi.delete(docName);
      setDocs((prev) => prev.filter((d) => d.name !== docName));
    } catch {
      alert('삭제 실패. 다시 시도해주세요.');
    } finally {
      setDeletingDoc(null);
    }
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.top}>
        <div className={styles.logo}>AI 어시스턴트</div>
        <button className={styles.newChat}>+ 새 대화</button>
      </div>

      <div className={styles.middle}>
        <p className={styles.empty}>대화 내역이 없습니다</p>
      </div>

      <div className={styles.bottom}>
        {user?.role === 'admin' && (
          <div className={styles.uploadSection}>
            <p className={styles.uploadLabel}>사내 문서 관리</p>

            {docs.length > 0 && (
              <ul className={styles.docList}>
                {docs.map((doc) => (
                  <li key={doc.name} className={styles.docItem}>
                    <span className={styles.docName} title={doc.name}>
                      📄 {doc.name}
                    </span>
                    <button
                      className={styles.deleteBtn}
                      onClick={() => handleDelete(doc.name)}
                      disabled={deletingDoc === doc.name}
                      title="삭제"
                    >
                      {deletingDoc === doc.name ? '…' : '✕'}
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <button
              className={styles.uploadBtn}
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? '업로드 중...' : '📤 문서 업로드'}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              multiple
              style={{ display: 'none' }}
              onChange={handleUpload}
            />
          </div>
        )}

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
  );
}
