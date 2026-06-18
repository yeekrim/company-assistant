import Sidebar from '../components/Chat/Sidebar';
import ChatWindow from '../components/Chat/ChatWindow';
import InputBox from '../components/Chat/InputBox';
import styles from './ChatPage.module.css';

export default function ChatPage() {
  return (
    <div className={styles.layout}>
      <Sidebar />
      <main className={styles.main}>
        <ChatWindow />
        <InputBox />
      </main>
    </div>
  );
}
