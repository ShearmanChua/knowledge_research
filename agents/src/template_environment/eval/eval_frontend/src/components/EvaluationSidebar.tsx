import { useState } from 'react';
import { 
  List, 
  ListItem, 
  ListItemButton, 
  ListItemText, 
  Paper, 
  Typography, 
  IconButton, 
  Box,
  Chip
} from '@mui/material';
import { 
  ChevronLeft as ChevronLeftIcon, 
  ChevronRight as ChevronRightIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';
import type { Evaluation } from '../types';

interface EvaluationSidebarProps {
  evaluations: Evaluation[];
  selectedEvaluation: Evaluation | null;
  onSelectEvaluation: (evaluation: Evaluation) => void;
}

export const EvaluationSidebar = ({
  evaluations,
  selectedEvaluation,
  onSelectEvaluation,
}: EvaluationSidebarProps) => {
  const [collapsed, setCollapsed] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return 'success';
      case 'running': return 'warning';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  return (
    <Paper 
      sx={{ 
        width: collapsed ? 60 : 300, 
        height: '100vh', 
        overflowY: 'auto',
        transition: 'width 0.3s ease-in-out',
        borderRadius: 0,
        boxShadow: '2px 0 8px rgba(0,0,0,0.1)'
      }}
    >
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: collapsed ? 'center' : 'space-between',
        p: 2,
        borderBottom: '1px solid #e0e0e0'
      }}>
        {!collapsed && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AssessmentIcon color="primary" />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Evaluations
            </Typography>
          </Box>
        )}
        <IconButton 
          onClick={() => setCollapsed(!collapsed)}
          size="small"
          sx={{ 
            bgcolor: 'primary.main', 
            color: 'white',
            '&:hover': { bgcolor: 'primary.dark' }
          }}
        >
          {collapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />}
        </IconButton>
      </Box>
      
      <List sx={{ p: collapsed ? 1 : 2 }}>
        {evaluations.map((evaluation) => (
          <ListItem key={evaluation.id} disablePadding sx={{ mb: 1 }}>
            <ListItemButton
              selected={selectedEvaluation?.id === evaluation.id}
              onClick={() => onSelectEvaluation(evaluation)}
              sx={{
                borderRadius: 2,
                mb: 1,
                minHeight: collapsed ? 48 : 'auto',
                justifyContent: collapsed ? 'center' : 'flex-start',
                '&.Mui-selected': {
                  bgcolor: 'primary.light',
                  color: 'primary.contrastText',
                  '&:hover': {
                    bgcolor: 'primary.main',
                  }
                },
                '&:hover': {
                  bgcolor: 'action.hover',
                  transform: 'translateX(4px)',
                  transition: 'all 0.2s ease-in-out'
                }
              }}
            >
              {collapsed ? (
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                  {evaluation.id}
                </Typography>
              ) : (
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                        Evaluation #{evaluation.id}
                      </Typography>
                      <Chip 
                        label={evaluation.status} 
                        size="small" 
                        color={getStatusColor(evaluation.status)}
                        sx={{ fontSize: '0.75rem' }}
                      />
                    </Box>
                  }
                  secondary={
                    <Typography variant="caption" color="text.secondary">
                      {evaluation.agents.length} agents
                    </Typography>
                  }
                />
              )}
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Paper>
  );
};