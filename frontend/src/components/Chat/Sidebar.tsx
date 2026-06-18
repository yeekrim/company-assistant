import { useRef, useState } from 'react';
import { useAuthStore } from '../../store/authStore';
import { documentApi } from '../../services/api';
import styles from './Sidebar.module.css';

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';
    setUploading(true);
    try {
      await documentApi.upload(file);
      alert(`"${file.name}" 업로드 완료`);
    } catch {
      alert('업로드 실패. 다시 시도해주세요.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.top}>
        <div className={styles.logo}>AI 어시스턴트</div>
        <button className={styles.newChat}>+ 새 대화</button>
      </div>

      <div className={styles.middle}>
        {/* 대화 목록 (추후 구현) */}
        <p className={styles.empty}>대화 내역이 없습니다</p>
      </div>

      <div className={styles.bottom}>
        {user?.role === 'admin' && (
          <div className={styles.uploadSection}>
            <p className={styles.uploadLabel}>사내 문서 관리</p>
            <button
              className={styles.uploadBtn}
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? '업로드 중...' : '📄 문서 업로드'}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
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
