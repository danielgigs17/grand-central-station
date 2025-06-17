import { create } from 'zustand';
import { AppState, Chat, Message, ChatCategory, Profile, Platform } from '../types';

interface AppStore extends AppState {
  // Actions
  setSelectedCategory: (category: ChatCategory) => void;
  setSelectedChat: (chatId: string | null) => void;
  toggleSidebar: () => void;
  
  // Data actions
  setChats: (chats: Chat[]) => void;
  addChat: (chat: Chat) => void;
  updateChat: (chatId: string, updates: Partial<Chat>) => void;
  
  setMessages: (chatId: string, messages: Message[]) => void;
  addMessage: (chatId: string, message: Message) => void;
  
  setProfiles: (profiles: Profile[]) => void;
  setPlatforms: (platforms: Platform[]) => void;
  
  // Loading actions
  setLoading: (key: keyof AppState['loading'], value: boolean) => void;
  setError: (error: string | null) => void;
}

export const useAppStore = create<AppStore>((set, get) => ({
  // Initial state
  selectedCategory: 'work',
  selectedChatId: null,
  sidebarCollapsed: false,
  
  chats: [],
  messages: {},
  profiles: [],
  platforms: [],
  
  loading: {
    chats: false,
    messages: false,
    sending: false,
  },
  
  error: null,
  
  // Actions
  setSelectedCategory: (category) => set({ selectedCategory: category, selectedChatId: null }),
  
  setSelectedChat: (chatId) => set({ selectedChatId: chatId }),
  
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  
  // Data actions
  setChats: (chats) => set({ chats }),
  
  addChat: (chat) => set((state) => ({
    chats: [chat, ...state.chats]
  })),
  
  updateChat: (chatId, updates) => set((state) => ({
    chats: state.chats.map(chat => 
      chat.id === chatId ? { ...chat, ...updates } : chat
    )
  })),
  
  setMessages: (chatId, messages) => set((state) => ({
    messages: {
      ...state.messages,
      [chatId]: messages
    }
  })),
  
  addMessage: (chatId, message) => set((state) => ({
    messages: {
      ...state.messages,
      [chatId]: [...(state.messages[chatId] || []), message]
    }
  })),
  
  setProfiles: (profiles) => set({ profiles }),
  setPlatforms: (platforms) => set({ platforms }),
  
  // Loading actions
  setLoading: (key, value) => set((state) => ({
    loading: {
      ...state.loading,
      [key]: value
    }
  })),
  
  setError: (error) => set({ error }),
}));