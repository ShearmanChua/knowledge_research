import { useEffect, useState } from 'react';
import { Box, Stack, Typography } from '@mui/material';
import { Assessment as AssessmentIcon } from '@mui/icons-material';
import axios from 'axios';
import { EvaluationSidebar } from './EvaluationSidebar';
import { AgentMetricsCard } from './AgentMetricsCard';
import type { Evaluation } from '../types';

export const MainPage = () => {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [selectedEvaluation, setSelectedEvaluation] = useState<Evaluation | null>(null);

  useEffect(() => {
    const fetchEvaluations = async () => {
      try {
        const response = await axios.get<Evaluation[]>('/api/evaluations');
        setEvaluations(response.data);
        // Auto-select first evaluation if none selected
        if (response.data.length > 0 && !selectedEvaluation) {
          setSelectedEvaluation(response.data[0]);
        }
      } catch (error) {
        console.error('Error fetching evaluations:', error);
      }
    };

    fetchEvaluations();
    // Poll for updates every 10 seconds
    const interval = setInterval(fetchEvaluations, 10000);
    return () => clearInterval(interval);
  }, [selectedEvaluation]);

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <EvaluationSidebar
        evaluations={evaluations}
        selectedEvaluation={selectedEvaluation}
        onSelectEvaluation={setSelectedEvaluation}
      />
      <Box component="main" sx={{ flexGrow: 1, p: 3, bgcolor: '#f5f5f5' }}>
        {selectedEvaluation ? (
          <>
            <Box sx={{ mb: 3 }}>
              <Typography 
                variant="h4" 
                sx={{ 
                  fontWeight: 700, 
                  color: 'primary.main',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  mb: 1
                }}
              >
                <AssessmentIcon sx={{ fontSize: 32 }} />
                Evaluation #{selectedEvaluation.id}
              </Typography>
              <Typography variant="body1" color="text.secondary">
                {selectedEvaluation.agents.length} agents • Status: {selectedEvaluation.status} • 
                Created: {new Date(selectedEvaluation.created_at).toLocaleDateString()}
              </Typography>
            </Box>
            
            <Stack spacing={2}>
              {selectedEvaluation.agents.map((agent) => (
                <AgentMetricsCard 
                  key={agent.id} 
                  agent={agent} 
                  evaluationId={selectedEvaluation.id}
                />
              ))}
            </Stack>
          </>
        ) : (
          <Box 
            sx={{ 
              display: 'flex', 
              flexDirection: 'column',
              alignItems: 'center', 
              justifyContent: 'center', 
              height: '100%',
              textAlign: 'center',
              color: 'text.secondary'
            }}
          >
            <AssessmentIcon sx={{ fontSize: 64, mb: 2, opacity: 0.5 }} />
            <Typography variant="h5" sx={{ mb: 1, fontWeight: 600 }}>
              No Evaluation Selected
            </Typography>
            <Typography variant="body1">
              Select an evaluation from the sidebar to view agent metrics
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};