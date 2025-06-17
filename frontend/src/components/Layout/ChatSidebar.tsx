import React, { useEffect, useMemo } from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Typography,
  Badge,
  Divider,
  TextField,
  InputAdornment,
  useTheme,
  alpha,
  Chip,
} from '@mui/material';
import {
  Search as SearchIcon,
  Circle as OnlineIcon,
} from '@mui/icons-material';
import { useAppStore } from '../../store/useAppStore';
import { Chat } from '../../types';
import { formatDistanceToNow } from 'date-fns';

const ChatSidebar: React.FC = () => {
  const theme = useTheme();
  const {
    selectedCategory,
    selectedChatId,
    setSelectedChat,
    chats,
    platforms,
    profiles,
  } = useAppStore();

  // Filter chats by selected category
  const filteredChats = useMemo(() => {
    return chats.filter(chat => {
      // For now, we'll categorize based on platform or add category logic later
      if (selectedCategory === 'work') {
        return chat.platform?.name === 'alibaba';
      }
      if (selectedCategory === 'personal') {
        return chat.platform?.name === 'whatsapp' || chat.platform?.name === 'telegram';
      }
      if (selectedCategory === 'hookups') {
        return chat.platform?.name === 'grindr' || chat.platform?.name === 'tinder';
      }
      return true;
    });
  }, [chats, selectedCategory]);

  // Group chats by platform
  const chatGroups = useMemo(() => {
    const groups: { [platform: string]: Chat[] } = {};
    filteredChats.forEach(chat => {
      const platformName = chat.platform?.display_name || chat.platform?.name || 'Unknown';
      if (!groups[platformName]) {
        groups[platformName] = [];
      }
      groups[platformName].push(chat);
    });
    return groups;
  }, [filteredChats]);

  const getChatDisplayName = (chat: Chat) => {
    return chat.profile?.name || chat.profile?.username || `Chat ${chat.id.slice(0, 8)}`;
  };

  const getChatLastMessage = (chat: Chat) => {
    if (chat.last_message?.content) {
      return chat.last_message.content.length > 50
        ? `${chat.last_message.content.slice(0, 50)}...`
        : chat.last_message.content;
    }
    return 'No messages yet';
  };

  const formatLastMessageTime = (chat: Chat) => {
    if (!chat.last_message_at) return '';
    try {
      return formatDistanceToNow(new Date(chat.last_message_at), { addSuffix: true });
    } catch {
      return '';
    }
  };

  const getPlatformColor = (platformName: string) => {
    const colors: { [key: string]: string } = {
      'Alibaba': '#ff6900',
      'Grindr': '#ffce00',
      'WhatsApp': '#25d366',
      'Telegram': '#0088cc',
      'Tinder': '#fd5068',
    };
    return colors[platformName] || theme.palette.primary.main;
  };

  return (
    <Box
      sx={{
        width: 320,
        backgroundColor: theme.palette.background.paper,
        borderRight: `1px solid ${theme.palette.divider}`,
        display: 'flex',
        flexDirection: 'column',
        zIndex: 2,
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          borderBottom: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Typography variant="h6" sx={{ mb: 2, textTransform: 'capitalize' }}>
          {selectedCategory}
        </Typography>
        <TextField
          fullWidth
          size="small"
          placeholder="Search conversations..."
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: '8px',
            },
          }}
        />
      </Box>

      {/* Chat List */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {Object.entries(chatGroups).map(([platformName, platformChats]) => (
          <Box key={platformName}>
            <Box
              sx={{
                px: 2,
                py: 1,
                backgroundColor: alpha(theme.palette.background.default, 0.5),
                borderBottom: `1px solid ${theme.palette.divider}`,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    backgroundColor: getPlatformColor(platformName),
                  }}
                />
                <Typography variant="subtitle2" color="text.secondary">
                  {platformName}
                </Typography>
                <Chip
                  label={platformChats.length}
                  size="small"
                  sx={{
                    height: 16,
                    fontSize: '10px',
                    ml: 'auto',
                  }}
                />
              </Box>
            </Box>

            <List sx={{ py: 0 }}>
              {platformChats.map((chat) => (
                <ListItem key={chat.id} disablePadding>
                  <ListItemButton
                    onClick={() => setSelectedChat(chat.id)}
                    selected={selectedChatId === chat.id}
                    sx={{
                      py: 1.5,
                      px: 2,
                      '&.Mui-selected': {
                        backgroundColor: alpha(theme.palette.primary.main, 0.1),
                        borderRight: `3px solid ${theme.palette.primary.main}`,
                      },
                      '&:hover': {
                        backgroundColor: alpha(theme.palette.action.hover, 0.1),
                      },
                    }}
                  >
                    <ListItemAvatar>
                      <Badge
                        color="success"
                        variant="dot"
                        invisible={!chat.is_active}
                        anchorOrigin={{
                          vertical: 'bottom',
                          horizontal: 'right',
                        }}
                      >
                        <Avatar
                          src={chat.profile?.avatar_url}
                          sx={{
                            width: 40,
                            height: 40,
                            backgroundColor: getPlatformColor(platformName),
                          }}
                        >
                          {getChatDisplayName(chat).charAt(0).toUpperCase()}
                        </Avatar>
                      </Badge>
                    </ListItemAvatar>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography
                            variant="subtitle2"
                            sx={{
                              fontWeight: chat.unread_count > 0 ? 600 : 400,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              flex: 1,
                            }}
                          >
                            {getChatDisplayName(chat)}
                          </Typography>
                          {chat.unread_count > 0 && (
                            <Badge
                              badgeContent={chat.unread_count}
                              color="primary"
                              sx={{
                                '& .MuiBadge-badge': {
                                  fontSize: '10px',
                                  height: '18px',
                                  minWidth: '18px',
                                },
                              }}
                            />
                          )}
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              fontWeight: chat.unread_count > 0 ? 500 : 400,
                            }}
                          >
                            {getChatLastMessage(chat)}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ fontSize: '11px' }}
                          >
                            {formatLastMessageTime(chat)}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          </Box>
        ))}

        {Object.keys(chatGroups).length === 0 && (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '200px',
              color: 'text.secondary',
            }}
          >
            <Typography variant="body2">No conversations found</Typography>
            <Typography variant="caption">
              Start a conversation to see it here
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default ChatSidebar;