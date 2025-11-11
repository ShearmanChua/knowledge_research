export interface Agent {
  id: number;
  name: string;
  trace_id: string;
  tool_metrics: Record<string, number>;
  stepwise_metrics: Record<string, number>;
}

export interface Evaluation {
  id: number;
  trace_id: string;
  created_at: string;
  status: string;
  agents: Agent[];
}