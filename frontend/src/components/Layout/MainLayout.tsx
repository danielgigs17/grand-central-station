import React from 'react';
import { Box, useTheme } from '@mui/material';
import CategorySidebar from './CategorySidebar';
import ChatSidebar from './ChatSidebar';
import ChatInterface from './ChatInterface';
import { useAppStore } from '../../store/useAppStore';

const MainLayout: React.FC = () => {
  const theme = useTheme();
  const { sidebarCollapsed } = useAppStore();

  return (
    <Box
      sx={{
        display: 'flex',
        height: '100vh',
        overflow: 'hidden',
        backgroundColor: theme.palette.background.default,
      }}
    >
      {/* Left sidebar - Categories */}
      <CategorySidebar />
      
      {/* Middle sidebar - Chat list */}
      <ChatSidebar />
      
      {/* Main content - Chat interface */}
      <Box
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <ChatInterface />
      </Box>
    </Box>
  );
};

export default MainLayout;