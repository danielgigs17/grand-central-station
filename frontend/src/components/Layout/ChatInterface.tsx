import React, { useEffect, useRef, useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  IconButton,
  Paper,
  Avatar,
  useTheme,
  alpha,
  InputAdornment,
  Divider,
} from '@mui/material';
import {
  Send as SendIcon,
  AttachFile as AttachIcon,
  EmojiEmotions as EmojiIcon,
  MoreVert as MoreIcon,
} from '@mui/icons-material';
import { useAppStore } from '../../store/useAppStore';
import { Message, MessageDirection } from '../../types';
import { formatDistanceToNow, format, isToday, isYesterday } from 'date-fns';

const ChatInterface: React.FC = () => {
  const theme = useTheme();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [messageInput, setMessageInput] = useState('');
  
  const {
    selectedChatId,
    chats,
    messages,
    loading,
    addMessage,
  } = useAppStore();

  const selectedChat = chats.find(chat => chat.id === selectedChatId);
  const chatMessages = selectedChatId ? messages[selectedChatId] || [] : [];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  const handleSendMessage = async () => {
    if (!messageInput.trim() || !selectedChatId) return;

    const newMessage: Message = {
      id: `temp-${Date.now()}`,
      chat_id: selectedChatId,
      direction: 'OUTGOING' as MessageDirection,
      content: messageInput.trim(),
      created_at: new Date().toISOString(),
      is_deleted: false,
      ai_generated: false,
      is_reply: false,
    };

    addMessage(selectedChatId, newMessage);
    setMessageInput('');

    // TODO: Send to API
    // try {
    //   await messageAPI.sendMessage(selectedChatId, messageInput.trim());
    // } catch (error) {
    //   console.error('Failed to send message:', error);
    // }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatMessageTime = (message: Message) => {
    const date = new Date(message.created_at);
    if (isToday(date)) {
      return format(date, 'HH:mm');
    } else if (isYesterday(date)) {
      return `Yesterday ${format(date, 'HH:mm')}`;
    } else {
      return format(date, 'MMM d, HH:mm');
    }
  };

  const getMessageGroupDate = (message: Message) => {
    const date = new Date(message.created_at);
    if (isToday(date)) {
      return 'Today';
    } else if (isYesterday(date)) {
      return 'Yesterday';
    } else {
      return format(date, 'MMMM d, yyyy');
    }
  };

  const shouldShowDateDivider = (message: Message, index: number) => {
    if (index === 0) return true;
    const currentDate = new Date(message.created_at).toDateString();
    const previousDate = new Date(chatMessages[index - 1].created_at).toDateString();
    return currentDate !== previousDate;
  };

  const shouldGroupMessage = (message: Message, index: number) => {
    if (index === 0) return false;
    const previousMessage = chatMessages[index - 1];
    const timeDiff = new Date(message.created_at).getTime() - new Date(previousMessage.created_at).getTime();
    return (
      previousMessage.direction === message.direction &&
      timeDiff < 5 * 60 * 1000 && // 5 minutes
      previousMessage.sender_name === message.sender_name
    );
  };

  if (!selectedChat) {
    return (
      <Box
        sx={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: theme.palette.background.default,
        }}
      >
        <Box sx={{ textAlign: 'center', color: 'text.secondary' }}>
          <Typography variant="h6" gutterBottom>
            Welcome to Grand Central Station
          </Typography>
          <Typography variant="body2">
            Select a conversation to start messaging
          </Typography>
        </Box>
      </Box>
    );
  }

  const getChatDisplayName = () => {
    return selectedChat.profile?.name || selectedChat.profile?.username || `Chat ${selectedChat.id.slice(0, 8)}`;
  };

  const getPlatformName = () => {
    return selectedChat.platform?.display_name || selectedChat.platform?.name || 'Unknown Platform';
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Chat Header */}
      <Paper
        elevation={1}
        sx={{
          p: 2,
          borderRadius: 0,
          borderBottom: `1px solid ${theme.palette.divider}`,
          backgroundColor: theme.palette.background.paper,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar
            src={selectedChat.profile?.avatar_url}
            sx={{ width: 40, height: 40 }}
          >
            {getChatDisplayName().charAt(0).toUpperCase()}
          </Avatar>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {getChatDisplayName()}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {getPlatformName()} • {selectedChat.is_active ? 'Active' : 'Inactive'}
            </Typography>
          </Box>
          <IconButton>
            <MoreIcon />
          </IconButton>
        </Box>
      </Paper>

      {/* Messages Area */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 1,
          backgroundColor: theme.palette.background.default,
        }}
      >
        {chatMessages.map((message, index) => (
          <Box key={message.id}>
            {/* Date Divider */}
            {shouldShowDateDivider(message, index) && (
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  my: 2,
                  mx: 2,
                }}
              >
                <Divider sx={{ flex: 1 }} />
                <Typography
                  variant="caption"
                  sx={{
                    px: 2,
                    py: 0.5,
                    backgroundColor: theme.palette.background.paper,
                    borderRadius: '12px',
                    color: 'text.secondary',
                  }}
                >
                  {getMessageGroupDate(message)}
                </Typography>
                <Divider sx={{ flex: 1 }} />
              </Box>
            )}

            {/* Message */}
            <Box
              sx={{
                display: 'flex',
                flexDirection: message.direction === 'OUTGOING' ? 'row-reverse' : 'row',
                mb: shouldGroupMessage(message, index) ? 0.5 : 2,
                mx: 2,
              }}
            >
              {!shouldGroupMessage(message, index) && message.direction === 'INCOMING' && (
                <Avatar
                  sx={{
                    width: 32,
                    height: 32,
                    mr: 1,
                    alignSelf: 'flex-end',
                  }}
                >
                  {(message.sender_name || getChatDisplayName()).charAt(0).toUpperCase()}
                </Avatar>
              )}

              <Box
                sx={{
                  maxWidth: '70%',
                  ml: shouldGroupMessage(message, index) && message.direction === 'INCOMING' ? '41px' : 0,
                  mr: shouldGroupMessage(message, index) && message.direction === 'OUTGOING' ? '41px' : 0,
                }}
              >
                {!shouldGroupMessage(message, index) && message.direction === 'INCOMING' && (
                  <Typography
                    variant="caption"
                    sx={{
                      color: 'text.secondary',
                      mb: 0.5,
                      display: 'block',
                    }}
                  >
                    {message.sender_name || getChatDisplayName()}
                  </Typography>
                )}

                <Paper
                  sx={{
                    p: 1.5,
                    backgroundColor:
                      message.direction === 'OUTGOING'
                        ? theme.palette.primary.main
                        : theme.palette.background.paper,
                    color:
                      message.direction === 'OUTGOING'
                        ? theme.palette.primary.contrastText
                        : theme.palette.text.primary,
                    borderRadius: '18px',
                    borderBottomRightRadius:
                      message.direction === 'OUTGOING' && !shouldGroupMessage(message, index) ? '4px' : '18px',
                    borderBottomLeftRadius:
                      message.direction === 'INCOMING' && !shouldGroupMessage(message, index) ? '4px' : '18px',
                    boxShadow: theme.shadows[1],
                  }}
                >
                  {message.is_reply && message.reply_to_content && (
                    <Box
                      sx={{
                        p: 1,
                        mb: 1,
                        borderRadius: '8px',
                        backgroundColor: alpha(theme.palette.background.default, 0.5),
                        borderLeft: `3px solid ${theme.palette.primary.main}`,
                      }}
                    >
                      <Typography variant="caption" color="text.secondary">
                        {message.reply_to_content.length > 100
                          ? `${message.reply_to_content.slice(0, 100)}...`
                          : message.reply_to_content}
                      </Typography>
                    </Box>
                  )}

                  <Typography variant="body1" sx={{ wordBreak: 'break-word' }}>
                    {message.content}
                  </Typography>

                  <Typography
                    variant="caption"
                    sx={{
                      display: 'block',
                      textAlign: 'right',
                      mt: 0.5,
                      opacity: 0.7,
                    }}
                  >
                    {formatMessageTime(message)}
                  </Typography>
                </Paper>
              </Box>
            </Box>
          </Box>
        ))}
        <div ref={messagesEndRef} />
      </Box>

      {/* Message Input */}
      <Paper
        elevation={3}
        sx={{
          p: 2,
          borderRadius: 0,
          backgroundColor: theme.palette.background.paper,
        }}
      >
        <TextField
          fullWidth
          multiline
          maxRows={4}
          value={messageInput}
          onChange={(e) => setMessageInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={`Message ${getChatDisplayName()}...`}
          variant="outlined"
          disabled={loading.sending}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <IconButton size="small" edge="start">
                  <AttachIcon />
                </IconButton>
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <IconButton size="small">
                  <EmojiIcon />
                </IconButton>
                <IconButton
                  onClick={handleSendMessage}
                  disabled={!messageInput.trim() || loading.sending}
                  color="primary"
                >
                  <SendIcon />
                </IconButton>
              </InputAdornment>
            ),
            sx: {
              borderRadius: '24px',
              '& .MuiOutlinedInput-notchedOutline': {
                borderColor: alpha(theme.palette.primary.main, 0.2),
              },
              '&:hover .MuiOutlinedInput-notchedOutline': {
                borderColor: theme.palette.primary.main,
              },
            },
          }}
        />
      </Paper>
    </Box>
  );
};

export default ChatInterface;