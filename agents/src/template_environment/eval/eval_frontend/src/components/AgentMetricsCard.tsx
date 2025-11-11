import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  CardContent,
  CardHeader,
  IconButton,
  Typography,
  Collapse,
  Box,
  Avatar,
  LinearProgress,
  Chip,
  Grid,
  Paper,
  Button,
} from '@mui/material';
import { 
  ExpandMore as ExpandMoreIcon,
  Build as BuildIcon,
  Psychology as PsychologyIcon,
  Star as StarIcon,
  TrendingUp as TrendingUpIcon
} from '@mui/icons-material';
import type { Agent } from '../types';

interface AgentMetricsCardProps {
  agent: Agent;
  evaluationId: number;
}

const avatarImages = ['bear.png', 'chicken.png', 'panda.png', 'rabbit.png'];

const getAvatarImage = (agentId: number) => {
  return `/agents_avatars/${avatarImages[agentId % avatarImages.length]}`;
};

const getHealthBarColor = (value: number, isPercentage: boolean = true) => {
  const normalizedValue = isPercentage ? value : (value / 5) * 100;
  if (normalizedValue >= 80) return 'success';
  if (normalizedValue >= 60) return 'warning';
  if (normalizedValue >= 40) return 'info';
  return 'error';
};

const formatMetricName = (name: string) => {
  return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

const HealthBar = ({ 
  label, 
  value, 
  maxValue = 100, 
  isPercentage = true,
  icon 
}: { 
  label: string; 
  value: number; 
  maxValue?: number;
  isPercentage?: boolean;
  icon?: React.ReactNode;
}) => {
  const normalizedValue = isPercentage ? value : (value / 5) * 100;
  const displayValue = isPercentage ? `${value.toFixed(1)}%` : `${value.toFixed(2)}/5`;
  
  return (
    <Paper sx={{ p: 2, mb: 2, borderRadius: 2, bgcolor: 'background.default' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        {icon && <Box sx={{ mr: 1, color: 'primary.main' }}>{icon}</Box>}
        <Typography variant="body2" sx={{ fontWeight: 600, flex: 1 }}>
          {label}
        </Typography>
        <Chip 
          label={displayValue} 
          size="small" 
          color={getHealthBarColor(value, isPercentage)}
          sx={{ fontWeight: 'bold', minWidth: 60 }}
        />
      </Box>
      <LinearProgress
        variant="determinate"
        value={Math.min(normalizedValue, 100)}
        color={getHealthBarColor(value, isPercentage)}
        sx={{
          height: 8,
          borderRadius: 4,
          bgcolor: 'grey.200',
          '& .MuiLinearProgress-bar': {
            borderRadius: 4,
            background: `linear-gradient(90deg, 
              ${getHealthBarColor(value, isPercentage) === 'success' ? '#4caf50, #8bc34a' : 
                getHealthBarColor(value, isPercentage) === 'warning' ? '#ff9800, #ffc107' :
                getHealthBarColor(value, isPercentage) === 'info' ? '#2196f3, #03a9f4' :
                '#f44336, #e57373'})`
          }
        }}
      />
    </Paper>
  );
};

export const AgentMetricsCard = ({ agent, evaluationId }: AgentMetricsCardProps) => {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();

  // Process tool metrics (convert to 0-100% scale)
  const toolMetrics = Object.entries(agent.tool_metrics)
    .filter(([key]) => !['tools_invoked', 'invalid_tools_invoked'].includes(key))
    .map(([name, value]) => ({
      name: formatMetricName(name),
      value: typeof value === 'number' ? value : 0,
      isPercentage: name.includes('rate') || name.includes('success')
    }));

  // Process stepwise metrics (0-5 scale)
  const stepwiseMetrics = Object.entries(agent.stepwise_metrics).map(([name, value]) => ({
    name: formatMetricName(name),
    value: typeof value === 'number' ? value : 0,
    isPercentage: false
  }));

  const getAgentRank = () => {
    const avgStepwise = Object.values(agent.stepwise_metrics).reduce((a, b) => a + b, 0) / Object.values(agent.stepwise_metrics).length;
    if (avgStepwise >= 4.5) return { rank: 'S', color: '#ffd700' };
    if (avgStepwise >= 4.0) return { rank: 'A', color: '#c0c0c0' };
    if (avgStepwise >= 3.5) return { rank: 'B', color: '#cd7f32' };
    if (avgStepwise >= 3.0) return { rank: 'C', color: '#4caf50' };
    return { rank: 'D', color: '#f44336' };
  };

  const agentRank = getAgentRank();

  return (
    <Card 
      sx={{ 
        mb: 2, 
        borderRadius: 3,
        boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
        transition: 'all 0.3s ease-in-out',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: '0 8px 30px rgba(0,0,0,0.15)'
        }
      }}
    >
      <CardHeader
        avatar={
          <Avatar
            src={getAvatarImage(agent.id)}
            sx={{ 
              width: 56, 
              height: 56,
              border: '3px solid',
              borderColor: agentRank.color,
              boxShadow: `0 0 0 2px ${agentRank.color}33`
            }}
          />
        }
        title={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Button
              variant="text"
              onClick={() => navigate(`/evaluation/${evaluationId}/agent/${agent.name}`)}
              sx={{
                p: 0,
                minWidth: 'auto',
                textTransform: 'none',
                '&:hover': {
                  bgcolor: 'transparent',
                  textDecoration: 'underline'
                }
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 700, color: 'primary.main' }}>
                {agent.name}
              </Typography>
            </Button>
            <Chip
              label={`Rank ${agentRank.rank}`}
              size="small"
              sx={{
                bgcolor: agentRank.color,
                color: 'white',
                fontWeight: 'bold',
                fontSize: '0.75rem'
              }}
            />
          </Box>
        }
        subheader={
          <Typography variant="body2" color="text.secondary">
            Agent ID: {agent.id} • Trace: {agent.trace_id.slice(0, 8)}...
          </Typography>
        }
        action={
          <IconButton
            onClick={() => setExpanded(!expanded)}
            sx={{
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.3s',
              bgcolor: 'primary.main',
              color: 'white',
              '&:hover': { bgcolor: 'primary.dark' }
            }}
          >
            <ExpandMoreIcon />
          </IconButton>
        }
      />
      
      <Collapse in={expanded}>
        <CardContent sx={{ pt: 0 }}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <BuildIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Tool Performance
                </Typography>
              </Box>
              {toolMetrics.map((metric) => (
                <HealthBar
                  key={metric.name}
                  label={metric.name}
                  value={metric.value}
                  isPercentage={metric.isPercentage}
                  icon={<TrendingUpIcon fontSize="small" />}
                />
              ))}
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <PsychologyIcon sx={{ mr: 1, color: 'secondary.main' }} />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Cognitive Metrics
                </Typography>
              </Box>
              {stepwiseMetrics.map((metric) => (
                <HealthBar
                  key={metric.name}
                  label={metric.name}
                  value={metric.value}
                  isPercentage={false}
                  icon={<StarIcon fontSize="small" />}
                />
              ))}
            </Grid>
          </Grid>
          
          {/* Summary Stats */}
          <Paper sx={{ p: 2, mt: 3, bgcolor: 'grey.50', borderRadius: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
              Performance Summary
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={4}>
                <Typography variant="caption" color="text.secondary">
                  Tool Success Rate
                </Typography>
                <Typography variant="h6" color="primary.main">
                  {agent.tool_metrics.tool_success_rate?.toFixed(1) || 0}%
                </Typography>
              </Grid>
              <Grid item xs={4}>
                <Typography variant="caption" color="text.secondary">
                  Avg Cognitive Score
                </Typography>
                <Typography variant="h6" color="secondary.main">
                  {(Object.values(agent.stepwise_metrics).reduce((a, b) => a + b, 0) / Object.values(agent.stepwise_metrics).length).toFixed(2)}/5
                </Typography>
              </Grid>
              <Grid item xs={4}>
                <Typography variant="caption" color="text.secondary">
                  Tool Calls
                </Typography>
                <Typography variant="h6">
                  {agent.tool_metrics.tool_calls || 0}
                </Typography>
              </Grid>
            </Grid>
          </Paper>
        </CardContent>
      </Collapse>
    </Card>
  );
};