import { create } from 'zustand';
import type { Message, Conversation } from '../types';

interface ChatStore {
  conversations: Conversation[];
  currentConversationId: string | null;
  loadingConversationId: string | null;
  savedLoadingMessages: Message[];
  messages: Message[];
  setConversations: (convs: Conversation[]) => void;
  addConversation: (conv: Conversation) => void;
  removeConversation: (id: string) => void;
  setCurrentConversation: (id: string | null) => void;
  addMessage: (msg: Message) => void;
  setMessages: (msgs: Message[]) => void;
  setLoading: (v: boolean, conversationId?: string | null) => void;
  startNewConversation: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  conversations: [],
  currentConversationId: null,
  loadingConversationId: null,
  savedLoadingMessages: [],
  messages: [],
  setConversations: (convs) => set({ conversations: convs }),
  addConversation: (conv) => set((s) => ({ conversations: [conv, ...s.conversations] })),
  removeConversation: (id) => set((s) => ({ conversations: s.conversations.filter((c) => c.id !== id) })),
  setCurrentConversation: (id) => set((s) => {
    // 로딩 중인 대화에서 떠날 때 → 현재 메시지 저장
    if (s.loadingConversationId && s.currentConversationId === s.loadingConversationId && id !== s.loadingConversationId) {
      return { currentConversationId: id, savedLoadingMessages: s.messages };
    }
    // 로딩 중인 대화로 돌아올 때 → 저장된 메시지 복원
    if (s.loadingConversationId && id === s.loadingConversationId) {
      return { currentConversationId: id, messages: s.savedLoadingMessages };
    }
    return { currentConversationId: id };
  }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setMessages: (msgs) => set({ messages: msgs }),
  setLoading: (v, conversationId) => set((s) => ({
    loadingConversationId: v ? (conversationId ?? s.currentConversationId) : null,
    savedLoadingMessages: v ? [] : s.savedLoadingMessages,
  })),
  startNewConversation: () => set({ currentConversationId: null, messages: [], loadingConversationId: null, savedLoadingMessages: [] }),
}));
