import { useRef, useState, useEffect } from 'react';
import { documentApi } from '../../services/api';
import styles from './DocumentModal.module.css';

interface Doc {
  name: string;
  chunks: number;
  effective_date: number; // YYYYMMDD, 모르면 0
}

interface PendingFile {
  file: File;
  date: string; // YYYY-MM-DD
}

interface Props {
  onClose: () => void;
}

// 20230105 → '2023-01-05', 0 → ''
function toInputDate(value: number): string {
  if (!value) return '';
  const s = String(value);
  return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
}

export default function DocumentModal({ onClose }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [pending, setPending] = useState<PendingFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [deletingDoc, setDeletingDoc] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ name: string; date: string } | null>(null);
  const [savingDate, setSavingDate] = useState(false);
  const [loadError, setLoadError] = useState(false);

  const loadDocs = async () => {
    try {
      setDocs(await documentApi.list());
      setLoadError(false);
    } catch {
      setLoadError(true);
    }
  };

  // 처음 열 때 목록 불러오기. setState는 응답 콜백 안에서만 하고, 모달이 닫히면 결과를 버린다
  useEffect(() => {
    let cancelled = false;
    documentApi.list()
      .then((list) => { if (!cancelled) setDocs(list); })
      .catch(() => { if (!cancelled) setLoadError(true); });
    return () => { cancelled = true; };
  }, []);

  // 파일을 고르면 바로 올리지 않고, 파일마다 시행일을 입력받은 뒤 올린다
  const handleSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    e.target.value = '';
    if (!files.length) return;
    setPending(files.map((file) => ({ file, date: '' })));
  };

  const setPendingDate = (index: number, date: string) => {
    setPending((prev) => prev.map((p, i) => (i === index ? { ...p, date } : p)));
  };

  const handleUpload = async () => {
    setUploading(true);
    try {
      const res = await documentApi.upload(pending.map((p) => p.file), pending.map((p) => p.date));
      if (res.errors.length > 0) {
        alert(`업로드 실패:\n${res.errors.map((e) => `${e.file}: ${e.error}`).join('\n')}`);
      }
      setPending([]);
      await loadDocs();
    } catch {
      alert('업로드 실패. 다시 시도해주세요.');
    } finally {
      setUploading(false);
    }
  };

  const handleSaveDate = async () => {
    if (!editing) return;
    setSavingDate(true);
    try {
      await documentApi.setEffectiveDate(editing.name, editing.date);
      setEditing(null);
      await loadDocs();
    } catch {
      alert('시행일 저장 실패. 다시 시도해주세요.');
    } finally {
      setSavingDate(false);
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

  const allDated = pending.every((p) => p.date);

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>사내 문서 관리</h2>
          <button className={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        <div className={styles.body}>
          {loadError && docs.length === 0 ? (
            <p className={styles.empty}>문서 목록을 불러오지 못했습니다</p>
          ) : docs.length === 0 ? (
            <p className={styles.empty}>업로드된 문서가 없습니다</p>
          ) : (
            <ul className={styles.docList}>
              {docs.map((doc) => (
                <li key={doc.name} className={styles.docItem}>
                  <span className={styles.docIcon}>📄</span>
                  <span className={styles.docName} title={doc.name}>{doc.name}</span>

                  {editing?.name === doc.name ? (
                    <span className={styles.dateEditor}>
                      <input
                        type="date"
                        className={styles.dateInput}
                        value={editing.date}
                        onChange={(e) => setEditing({ name: doc.name, date: e.target.value })}
                        aria-label={`${doc.name} 시행일`}
                      />
                      <button
                        className={styles.dateSaveBtn}
                        onClick={handleSaveDate}
                        disabled={savingDate || !editing.date}
                      >
                        저장
                      </button>
                      <button className={styles.dateCancelBtn} onClick={() => setEditing(null)} disabled={savingDate}>
                        취소
                      </button>
                    </span>
                  ) : (
                    <button
                      className={doc.effective_date ? styles.dateBtn : styles.dateBtnMissing}
                      onClick={() => setEditing({ name: doc.name, date: toInputDate(doc.effective_date) })}
                      title="시행일 수정"
                    >
                      {doc.effective_date ? `시행 ${toInputDate(doc.effective_date)}` : '시행일 입력'}
                    </button>
                  )}

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
          {pending.length > 0 ? (
            <>
              <p className={styles.pendingHint}>각 문서의 시행일을 입력하세요. 규정이 서로 다르면 질문 시점에 시행 중인 최신 문서를 따릅니다.</p>
              <ul className={styles.pendingList}>
                {pending.map((p, i) => (
                  <li key={`${p.file.name}-${i}`} className={styles.pendingItem}>
                    <span className={styles.docName} title={p.file.name}>{p.file.name}</span>
                    <input
                      type="date"
                      className={styles.dateInput}
                      value={p.date}
                      onChange={(e) => setPendingDate(i, e.target.value)}
                      aria-label={`${p.file.name} 시행일`}
                      required
                    />
                  </li>
                ))}
              </ul>
              <div className={styles.pendingActions}>
                <button className={styles.cancelBtn} onClick={() => setPending([])} disabled={uploading}>
                  취소
                </button>
                <button className={styles.uploadBtn} onClick={handleUpload} disabled={uploading || !allDated}>
                  {uploading ? '업로드 중...' : `📤 ${pending.length}개 업로드`}
                </button>
              </div>
            </>
          ) : (
            <button
              className={styles.uploadBtn}
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              📤 문서 업로드
            </button>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            multiple
            style={{ display: 'none' }}
            onChange={handleSelect}
          />
        </div>
      </div>
    </div>
  );
}
