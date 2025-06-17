import { useAppStore } from '../store/useAppStore';
import { chatAPI, messageAPI } from './api';

class RealtimeService {
  private pollInterval: NodeJS.Timeout | null = null;
  private lastPollTime: Date = new Date();
  private isPolling: boolean = false;

  start() {
    if (this.pollInterval) return;
    
    console.log('Starting realtime polling...');
    
    // Initial load
    this.loadInitialData();
    
    // Poll every 5 seconds for new messages
    this.pollInterval = setInterval(() => {
      this.pollForUpdates();
    }, 5000);
    
    this.isPolling = true;
  }

  stop() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
    this.isPolling = false;
    console.log('Stopped realtime polling');
  }

  private async loadInitialData() {
    const { setChats, setLoading, setError, setMessages } = useAppStore.getState();
    
    try {
      setLoading('chats', true);
      setError(null);
      
      // Try to load from API first, fall back to mock data
      try {
        const chats = await chatAPI.getChats();
        setChats(chats);
        
        // Load recent messages for each chat
        for (const chat of chats.slice(0, 10)) { // Limit to first 10 chats
          try {
            const messages = await messageAPI.getMessages(chat.id, 50);
            setMessages(chat.id, messages);
          } catch (error) {
            console.error(`Failed to load messages for chat ${chat.id}:`, error);
          }
        }
      } catch (error) {
        console.warn('API not available, using mock data:', error);
        
        // Load mock data
        const { mockChats, mockMessages } = await import('./mockData');
        setChats(mockChats);
        
        // Load mock messages for each chat
        Object.entries(mockMessages).forEach(([chatId, messages]) => {
          setMessages(chatId, messages);
        });
      }
      
    } catch (error) {
      console.error('Failed to load initial data:', error);
      setError('Failed to load conversations');
    } finally {
      setLoading('chats', false);
    }
  }

  private async pollForUpdates() {
    if (!this.isPolling) return;
    
    const { chats, selectedChatId, setMessages, updateChat, addMessage } = useAppStore.getState();
    
    try {
      // Check for new messages in active chats
      const activeChatIds = chats
        .filter(chat => chat.is_active)
        .map(chat => chat.id)
        .slice(0, 5); // Limit to 5 most active chats for performance

      for (const chatId of activeChatIds) {
        try {
          // Get recent messages (last 10)
          const messages = await messageAPI.getMessages(chatId, 10);
          const currentMessages = useAppStore.getState().messages[chatId] || [];
          
          // Find new messages
          const newMessages = messages.filter(msg => 
            !currentMessages.some(existing => existing.id === msg.id)
          );
          
          if (newMessages.length > 0) {
            // Add new messages
            newMessages.forEach(msg => addMessage(chatId, msg));
            
            // Update chat's last message info
            const latestMessage = messages[0];
            if (latestMessage) {
              updateChat(chatId, {
                last_message_at: latestMessage.created_at,
                last_message: latestMessage,
                unread_count: latestMessage.direction === 'INCOMING' ? 
                  (currentMessages.length > 0 ? 1 : newMessages.length) : 0
              });
            }
          }
        } catch (error) {
          console.error(`Failed to poll messages for chat ${chatId}:`, error);
        }
      }

      // If we have a selected chat, also check for new messages there
      if (selectedChatId && !activeChatIds.includes(selectedChatId)) {
        try {
          const messages = await messageAPI.getMessages(selectedChatId, 10);
          const currentMessages = useAppStore.getState().messages[selectedChatId] || [];
          
          const newMessages = messages.filter(msg => 
            !currentMessages.some(existing => existing.id === msg.id)
          );
          
          newMessages.forEach(msg => addMessage(selectedChatId, msg));
        } catch (error) {
          console.error(`Failed to poll messages for selected chat ${selectedChatId}:`, error);
        }
      }

      this.lastPollTime = new Date();
      
    } catch (error) {
      console.error('Error during polling:', error);
    }
  }

  getStatus() {
    return {
      isPolling: this.isPolling,
      lastPollTime: this.lastPollTime,
    };
  }
}

export const realtimeService = new RealtimeService();