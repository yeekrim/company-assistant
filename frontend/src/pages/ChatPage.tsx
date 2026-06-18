import Sidebar from '../components/Chat/Sidebar';
import styles from './ChatPage.module.css';

export default function ChatPage() {
  return (
    <div className={styles.layout}>
      <Sidebar />
      <main className={styles.main}>
        <div className={styles.placeholder}>
          <p>채팅 화면 구현 예정</p>
        </div>
      </main>
    </div>
  );
}
