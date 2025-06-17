export interface Platform {
  id: string;
  name: string;
  display_name: string;
  icon_url?: string;
  is_active: boolean;
}

export interface Profile {
  id: string;
  platform_id: string;
  name: string;
  username?: string;
  avatar_url?: string;
  bio?: string;
  location?: string;
  is_active: boolean;
}

export interface Chat {
  id: string;
  account_id: string;
  profile_id: string;
  platform_chat_id: string;
  category?: ChatCategory;
  is_active: boolean;
  is_archived: boolean;
  is_starred: boolean;
  is_muted: boolean;
  unread_count: number;
  last_message_at?: string;
  created_at: string;
  updated_at: string;
  profile?: Profile;
  platform?: Platform;
  last_message?: Message;
}

export interface Message {
  id: string;
  chat_id: string;
  platform_message_id?: string;
  direction: MessageDirection;
  status?: MessageStatus;
  content?: string;
  content_type?: string;
  is_deleted: boolean;
  ai_generated: boolean;
  platform_timestamp?: string;
  delivered_at?: string;
  read_at?: string;
  created_at: string;
  is_reply: boolean;
  reply_to_content?: string;
  sender_name?: string;
}

export type MessageDirection = 'INCOMING' | 'OUTGOING';
export type MessageStatus = 'PENDING' | 'SENT' | 'DELIVERED' | 'READ' | 'FAILED';

export type ChatCategory = 'work' | 'personal' | 'hookups';

export interface CategoryGroup {
  id: ChatCategory;
  name: string;
  icon: string;
  color: string;
}

export interface AppState {
  // Navigation
  selectedCategory: ChatCategory;
  selectedChatId: string | null;
  sidebarCollapsed: boolean;
  
  // Data
  chats: Chat[];
  messages: { [chatId: string]: Message[] };
  profiles: Profile[];
  platforms: Platform[];
  
  // Loading states
  loading: {
    chats: boolean;
    messages: boolean;
    sending: boolean;
  };
  
  // Error states
  error: string | null;
}