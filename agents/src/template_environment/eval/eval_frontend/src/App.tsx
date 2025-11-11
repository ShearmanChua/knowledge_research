import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { CssBaseline } from '@mui/material';
import { MainPage } from './components/MainPage';
import { AgentDetailPage } from './components/AgentDetailPage';

function App() {
  return (
    <Router>
      <CssBaseline />
      <Routes>
        <Route path="/" element={<MainPage />} />
        <Route path="/evaluation/:evaluationId/agent/:agentName" element={<AgentDetailPage />} />
      </Routes>
    </Router>
  );
}

export default App;
