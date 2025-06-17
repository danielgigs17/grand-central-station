import axios from 'axios';
import { Chat, Message, Profile, Platform } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for debugging
api.interceptors.request.use((config) => {
  console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const chatAPI = {
  getChats: async (): Promise<Chat[]> => {
    const response = await api.get('/chats/');
    return response.data;
  },
  
  getChat: async (chatId: string): Promise<Chat> => {
    const response = await api.get(`/chats/${chatId}`);
    return response.data;
  },
  
  updateChat: async (chatId: string, updates: Partial<Chat>): Promise<Chat> => {
    const response = await api.patch(`/chats/${chatId}`, updates);
    return response.data;
  },
};

export const messageAPI = {
  getMessages: async (chatId: string, limit = 50, offset = 0): Promise<Message[]> => {
    const response = await api.get(`/chats/${chatId}/messages/`, {
      params: { limit, offset }
    });
    return response.data;
  },
  
  sendMessage: async (chatId: string, content: string): Promise<Message> => {
    const response = await api.post(`/chats/${chatId}/messages/`, {
      content,
      direction: 'OUTGOING'
    });
    return response.data;
  },
  
  markAsRead: async (messageId: string): Promise<void> => {
    await api.patch(`/messages/${messageId}/read`);
  },
};

export const profileAPI = {
  getProfiles: async (): Promise<Profile[]> => {
    const response = await api.get('/profiles/');
    return response.data;
  },
};

export const platformAPI = {
  getPlatforms: async (): Promise<Platform[]> => {
    const response = await api.get('/platforms/');
    return response.data;
  },
};

export default api;