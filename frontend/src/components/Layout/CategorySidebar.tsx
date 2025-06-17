import React from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  Tooltip,
  useTheme,
  alpha,
} from '@mui/material';
import {
  Work as WorkIcon,
  Person as PersonIcon,
  Favorite as HookupsIcon,
} from '@mui/icons-material';
import { useAppStore } from '../../store/useAppStore';
import { ChatCategory, CategoryGroup } from '../../types';

const categories: CategoryGroup[] = [
  {
    id: 'work',
    name: 'Work',
    icon: 'work',
    color: '#1976d2',
  },
  {
    id: 'personal',
    name: 'Personal',
    icon: 'person',
    color: '#388e3c',
  },
  {
    id: 'hookups',
    name: 'Hookups',
    icon: 'favorite',
    color: '#d32f2f',
  },
];

const getIcon = (iconName: string) => {
  switch (iconName) {
    case 'work':
      return <WorkIcon />;
    case 'person':
      return <PersonIcon />;
    case 'favorite':
      return <HookupsIcon />;
    default:
      return <WorkIcon />;
  }
};

const CategorySidebar: React.FC = () => {
  const theme = useTheme();
  const { selectedCategory, setSelectedCategory } = useAppStore();

  return (
    <Box
      sx={{
        width: 72,
        backgroundColor: theme.palette.mode === 'dark' ? '#1a1a1a' : '#f5f5f5',
        borderRight: `1px solid ${theme.palette.divider}`,
        display: 'flex',
        flexDirection: 'column',
        zIndex: 3,
      }}
    >
      <Box
        sx={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderBottom: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box
          sx={{
            width: 32,
            height: 32,
            borderRadius: '8px',
            backgroundColor: theme.palette.primary.main,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontWeight: 'bold',
            fontSize: '14px',
          }}
        >
          GC
        </Box>
      </Box>

      <List sx={{ p: 1, flex: 1 }}>
        {categories.map((category) => (
          <ListItem key={category.id} disablePadding sx={{ mb: 1 }}>
            <Tooltip title={category.name} placement="right">
              <ListItemButton
                onClick={() => setSelectedCategory(category.id)}
                sx={{
                  minHeight: 48,
                  justifyContent: 'center',
                  px: 2.5,
                  borderRadius: '8px',
                  backgroundColor:
                    selectedCategory === category.id
                      ? alpha(category.color, 0.1)
                      : 'transparent',
                  '&:hover': {
                    backgroundColor: alpha(category.color, 0.1),
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: 0,
                    justifyContent: 'center',
                    color:
                      selectedCategory === category.id
                        ? category.color
                        : theme.palette.text.secondary,
                  }}
                >
                  {getIcon(category.icon)}
                </ListItemIcon>
              </ListItemButton>
            </Tooltip>
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

export default CategorySidebar;