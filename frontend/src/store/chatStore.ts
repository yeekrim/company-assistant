import { create } from 'zustand';
import type { Message, Conversation } from '../types';

interface ChatStore {
  conversations: Conversation[];
  currentConversationId: string | null;
  messages: Message[];
  isLoading: boolean;
  setCurrentConversation: (id: string) => void;
  addMessage: (msg: Message) => void;
  setMessages: (msgs: Message[]) => void;
  setLoading: (v: boolean) => void;
  startNewConversation: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  conversations: [],
  currentConversationId: null,
  messages: [],
  isLoading: false,
  setCurrentConversation: (id) => set({ currentConversationId: id }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setMessages: (msgs) => set({ messages: msgs }),
  setLoading: (v) => set({ isLoading: v }),
  startNewConversation: () => set({ currentConversationId: null, messages: [] }),
}));
