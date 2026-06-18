import { useRef, useState, useEffect, useCallback } from 'react';
import { documentApi } from '../../services/api';
import styles from './DocumentModal.module.css';

interface Doc {
  name: string;
  chunks: number;
}

interface Props {
  onClose: () => void;
}

export default function DocumentModal({ onClose }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [deletingDoc, setDeletingDoc] = useState<string | null>(null);

  const loadDocs = useCallback(async () => {
    try {
      setDocs(await documentApi.list());
    } catch {}
  }, []);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    e.target.value = '';
    setUploading(true);
    try {
      const res = await documentApi.upload(files);
      if (res.errors.length > 0) {
        alert(`업로드 실패: ${res.errors.map((e) => e.file).join(', ')}`);
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
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>사내 문서 관리</h2>
          <button className={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        <div className={styles.body}>
          {docs.length === 0 ? (
            <p className={styles.empty}>업로드된 문서가 없습니다</p>
          ) : (
            <ul className={styles.docList}>
              {docs.map((doc) => (
                <li key={doc.name} className={styles.docItem}>
                  <span className={styles.docIcon}>📄</span>
                  <span className={styles.docName} title={doc.name}>{doc.name}</span>

                  <button
                    className={styles.deleteBtn}
                    onClick={() => handleDelete(doc.name)}
                    disabled={deletingDoc === doc.name}
                  >
                    {deletingDoc === doc.name ? '삭제 중...' : '삭제'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className={styles.footer}>
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
      </div>
    </div>
  );
}
