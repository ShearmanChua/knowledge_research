import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Grid,
  Paper,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Chip,
  Divider,
  IconButton,
  Avatar,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Build as BuildIcon,
  Chat as ChatIcon,
  Error as ErrorIcon,
  CheckCircle as CheckCircleIcon,
  Timeline as TimelineIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import axios from 'axios';
import type { Agent } from '../types';

interface ToolInvoked {
  number_of_times_invoked: number;
  success_rate: number;
  average_latency: number;
  tool_entropy: number;
}

interface TraceMessage {
  role: string;
  content: string;
  timestamp?: string;
}

interface TraceInvocation {
  invocation_id: string;
  invocation_msg: string;
  chat_history: TraceMessage[];
}

const avatarImages = ['bear.png', 'chicken.png', 'panda.png', 'rabbit.png'];

const getAvatarImage = (agentId: number) => {
  return `/agents_avatars/${avatarImages[agentId % avatarImages.length]}`;
};

const getAgentRank = (stepwiseMetrics: Record<string, number>) => {
  const avgStepwise = Object.values(stepwiseMetrics).reduce((a, b) => a + b, 0) / Object.values(stepwiseMetrics).length;
  if (avgStepwise >= 4.5) return { rank: 'S', color: '#ffd700' };
  if (avgStepwise >= 4.0) return { rank: 'A', color: '#c0c0c0' };
  if (avgStepwise >= 3.5) return { rank: 'B', color: '#cd7f32' };
  if (avgStepwise >= 3.0) return { rank: 'C', color: '#4caf50' };
  return { rank: 'D', color: '#f44336' };
};

export const AgentDetailPage = () => {
  const { evaluationId, agentName } = useParams<{ evaluationId: string; agentName: string }>();
  const navigate = useNavigate();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [traces, setTraces] = useState<TraceInvocation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAgentData = async () => {
      try {
        // Fetch evaluation data to get agent details
        const evalResponse = await axios.get(`/api/evaluations/${evaluationId}`);
        const evaluation = evalResponse.data;
        const foundAgent = evaluation.agents.find((a: Agent) => a.name === agentName);
        
        if (foundAgent) {
          setAgent(foundAgent);
        }

        // Fetch trace data
        const traceResponse = await axios.get(`/api/evaluations/${evaluationId}/agents/${agentName}/traces`);
        const traceData = traceResponse.data;
        
        // Extract trace invocations with their chat histories
        const traceInvocations: TraceInvocation[] = [];
        if (traceData && traceData.traces) {
          traceData.traces.forEach((trace: any) => {
            const chatMessages: TraceMessage[] = [];
            if (trace.chat_history && Array.isArray(trace.chat_history)) {
              trace.chat_history.forEach((message: any) => {
                let content = message['message.content'] || message.content || message.message;
                
                // Handle tool calls if no regular content
                if (!content && message['message.tool_calls']) {
                  const toolCalls = message['message.tool_calls'];
                  if (Array.isArray(toolCalls) && toolCalls.length > 0) {
                    content = toolCalls.map((call: any) => {
                      const functionName = call['tool_call.function.name'] || 'unknown_function';
                      const args = call['tool_call.function.arguments'] || '{}';
                      return `🔧 Tool Call: ${functionName}\nArguments: ${args}`;
                    }).join('\n\n');
                  }
                }
                
                chatMessages.push({
                  role: message['message.role'] || message.role || 'unknown',
                  content: content || 'No content',
                  timestamp: message.timestamp
                });
              });
            }
            
            traceInvocations.push({
              invocation_id: trace.invocation_id || 'unknown',
              invocation_msg: trace.invocation_msg || 'No invocation message',
              chat_history: chatMessages
            });
          });
        }
        setTraces(traceInvocations);
      } catch (error) {
        console.error('Error fetching agent data:', error);
      } finally {
        setLoading(false);
      }
    };

    if (evaluationId && agentName) {
      fetchAgentData();
    }
  }, [evaluationId, agentName]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Typography>Loading agent details...</Typography>
      </Box>
    );
  }

  if (!agent) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Typography>Agent not found</Typography>
      </Box>
    );
  }

  const agentRank = getAgentRank(agent.stepwise_metrics);
  const toolsInvoked = agent.tool_metrics.tools_invoked as Record<string, ToolInvoked> || {};
  const invalidToolsInvoked = agent.tool_metrics.invalid_tools_invoked as Record<string, any> || {};

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f8fafc', p: 3 }}>
      {/* Header with back button */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <IconButton 
          onClick={() => navigate('/')}
          sx={{ 
            bgcolor: 'primary.main', 
            color: 'white',
            '&:hover': { bgcolor: 'primary.dark' }
          }}
        >
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>
          Agent Details: {agent.name}
        </Typography>
      </Box>

      {/* Agent Card - 1/5 of page */}
      <Box sx={{ height: '20vh', mb: 3 }}>
        <Card sx={{ 
          height: '100%', 
          borderRadius: 3,
          boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
        }}>
          <CardContent sx={{ height: '100%', display: 'flex', alignItems: 'center', gap: 3 }}>
            <Avatar
              src={getAvatarImage(agent.id)}
              sx={{ 
                width: 80, 
                height: 80,
                border: '3px solid',
                borderColor: agentRank.color,
                boxShadow: `0 0 0 2px ${agentRank.color}33`
              }}
            />
            <Box sx={{ flex: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                <Typography variant="h4" sx={{ fontWeight: 700 }}>
                  {agent.name}
                </Typography>
                <Chip
                  label={`Rank ${agentRank.rank}`}
                  sx={{
                    bgcolor: agentRank.color,
                    color: 'white',
                    fontWeight: 'bold',
                  }}
                />
              </Box>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                Agent ID: {agent.id} • Trace: {agent.trace_id}
              </Typography>
              <Grid container spacing={3}>
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
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Bottom containers - stacked vertically */}
      <Grid container spacing={3}>
        {/* Tool Performance */}
        <Grid item xs={12}>
          <Paper sx={{ 
            minHeight: '300px', 
            p: 3, 
            borderRadius: 3,
            boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
            overflow: 'auto'
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <BuildIcon sx={{ mr: 2, color: 'primary.main', fontSize: 28 }} />
              <Typography variant="h5" sx={{ fontWeight: 600 }}>
                Tool Performance
              </Typography>
            </Box>

            {/* Valid Tools */}
            <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              <CheckCircleIcon color="success" />
              Valid Tools Invoked
            </Typography>
            {Object.keys(toolsInvoked).length > 0 ? (
              <List sx={{ mb: 3 }}>
                {Object.entries(toolsInvoked).map(([toolName, toolData]) => (
                <ListItem key={toolName} sx={{ px: 0, mb: 2 }}>
                  <Paper sx={{ 
                    width: '100%', 
                    p: 3, 
                    bgcolor: 'success.light', 
                    borderRadius: 2,
                    border: '1px solid',
                    borderColor: 'success.main',
                    '&:hover': { 
                      boxShadow: '0 4px 12px rgba(76, 175, 80, 0.3)',
                      transform: 'translateY(-1px)'
                    },
                    transition: 'all 0.2s ease-in-out'
                  }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: 'bold', fontSize: '1.1rem', color: 'success.dark' }}>
                        {toolName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </Typography>
                      <Chip 
                        label={`${Math.min(toolData.success_rate * 100, 100).toFixed(1)}%`}
                        size="medium"
                        sx={{ 
                          bgcolor: 'success.main', 
                          color: 'white', 
                          fontWeight: 'bold',
                          fontSize: '0.9rem'
                        }}
                      />
                    </Box>
                    <Grid container spacing={3}>
                      <Grid item xs={4}>
                        <Box sx={{ textAlign: 'center', p: 1, bgcolor: 'rgba(255,255,255,0.7)', borderRadius: 1 }}>
                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'success.dark' }}>
                            Times Used
                          </Typography>
                          <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'success.dark' }}>
                            {toolData.number_of_times_invoked}
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={4}>
                        <Box sx={{ textAlign: 'center', p: 1, bgcolor: 'rgba(255,255,255,0.7)', borderRadius: 1 }}>
                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'success.dark' }}>
                            Avg Response Time
                          </Typography>
                          <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'success.dark' }}>
                            {toolData.average_latency.toFixed(3)}s
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={4}>
                        <Box sx={{ textAlign: 'center', p: 1, bgcolor: 'rgba(255,255,255,0.7)', borderRadius: 1 }}>
                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'success.dark' }}>
                            Complexity Score
                          </Typography>
                          <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'success.dark' }}>
                            {toolData.tool_entropy.toFixed(2)}
                          </Typography>
                        </Box>
                      </Grid>
                    </Grid>
                  </Paper>
                </ListItem>
              ))}
              </List>
            ) : (
              <Box sx={{ 
                display: 'flex', 
                flexDirection: 'column',
                alignItems: 'center', 
                justifyContent: 'center', 
                height: '200px',
                textAlign: 'center',
                color: 'text.secondary',
                mb: 3
              }}>
                <BuildIcon sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
                <Typography variant="h6" sx={{ mb: 1 }}>
                  No Valid Tools Used
                </Typography>
                <Typography variant="body2">
                  This agent did not invoke any valid tools
                </Typography>
              </Box>
            )}

            {/* Invalid Tools */}
            {Object.keys(invalidToolsInvoked).length > 0 && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <ErrorIcon color="error" />
                  Invalid Tools Invoked
                </Typography>
                <List>
                  {Object.entries(invalidToolsInvoked).map(([toolName, toolData]) => (
                    <ListItem key={toolName} sx={{ 
                      bgcolor: 'error.light', 
                      mb: 1, 
                      borderRadius: 2,
                      '&:hover': { bgcolor: 'error.main', color: 'white' }
                    }}>
                      <ListItemText
                        primary={
                          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                            {toolName}
                          </Typography>
                        }
                        secondary={
                          <Typography variant="caption">
                            {JSON.stringify(toolData)}
                          </Typography>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </>
            )}
          </Paper>
        </Grid>

        {/* Chat History */}
        <Grid item xs={12}>
          <Paper sx={{ 
            minHeight: '400px', 
            p: 3, 
            borderRadius: 3,
            boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
            overflow: 'auto'
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <ChatIcon sx={{ mr: 2, color: 'secondary.main', fontSize: 28 }} />
              <Typography variant="h5" sx={{ fontWeight: 600 }}>
                Chat History
              </Typography>
            </Box>

            {traces.length > 0 ? (
              <Box>
                {traces.map((trace, index) => (
                  <Accordion key={trace.invocation_id} sx={{ mb: 2, borderRadius: 2 }}>
                    <AccordionSummary
                      expandIcon={<ExpandMoreIcon />}
                      sx={{
                        bgcolor: 'primary.light',
                        borderRadius: 2,
                        '&:hover': { bgcolor: 'primary.main', color: 'white' },
                        transition: 'all 0.2s ease-in-out'
                      }}
                    >
                      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: '100%' }}>
                        <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                          Trace #{index + 1}
                        </Typography>
                        <Typography variant="caption" sx={{ opacity: 0.8, fontFamily: 'monospace' }}>
                          ID: {trace.invocation_id}
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 1, fontStyle: 'italic' }}>
                          {trace.invocation_msg}
                        </Typography>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails sx={{ p: 0 }}>
                      <List sx={{ width: '100%' }}>
                        {trace.chat_history.map((message, msgIndex) => (
                          <ListItem key={msgIndex} sx={{ 
                            mb: 1, 
                            bgcolor: message.role === 'user' ? 'primary.light' : 
                                     message.role === 'assistant' ? 'secondary.light' :
                                     message.role === 'system' ? 'info.light' :
                                     message.role === 'tool' ? 'warning.light' : 'grey.100',
                            borderRadius: 2,
                            flexDirection: 'column',
                            alignItems: 'flex-start',
                            border: '1px solid',
                            borderColor: message.role === 'user' ? 'primary.main' : 
                                        message.role === 'assistant' ? 'secondary.main' :
                                        message.role === 'system' ? 'info.main' :
                                        message.role === 'tool' ? 'warning.main' : 'grey.300'
                          }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, width: '100%' }}>
                              <Chip 
                                label={message.role.toUpperCase()} 
                                size="small" 
                                color={message.role === 'user' ? 'primary' : 
                                       message.role === 'assistant' ? 'secondary' :
                                       message.role === 'system' ? 'info' :
                                       message.role === 'tool' ? 'warning' : 'default'}
                                sx={{ fontWeight: 'bold', fontSize: '0.7rem' }}
                              />
                              {message.timestamp && (
                                <Typography variant="caption" color="text.secondary">
                                  {new Date(message.timestamp).toLocaleTimeString()}
                                </Typography>
                              )}
                            </Box>
                            <Typography variant="body2" sx={{ 
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                              maxHeight: '300px',
                              overflow: 'auto',
                              width: '100%',
                              p: 1,
                              bgcolor: 'rgba(255,255,255,0.7)',
                              borderRadius: 1
                            }}>
                              {message.content}
                            </Typography>
                          </ListItem>
                        ))}
                      </List>
                    </AccordionDetails>
                  </Accordion>
                ))}
              </Box>
            ) : (
              <Box sx={{ 
                display: 'flex', 
                flexDirection: 'column',
                alignItems: 'center', 
                justifyContent: 'center', 
                height: '50%',
                textAlign: 'center',
                color: 'text.secondary'
              }}>
                <TimelineIcon sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
                <Typography variant="h6" sx={{ mb: 1 }}>
                  No Chat History Available
                </Typography>
                <Typography variant="body2">
                  No trace messages found for this agent
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};