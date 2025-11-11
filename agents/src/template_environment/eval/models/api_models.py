from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class EvaluationStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RunEvaluationRequest(BaseModel):
    trace_id: str = Field(..., description="Unique identifier for the trace", example="trace_abc123")
    project_name: str = Field(..., description="Name of the project", example="my_project")


class RunEvaluationResponse(BaseModel):
    evaluation_id: str = Field(..., description="Unique identifier for the evaluation", example="1")
    evaluation_status: EvaluationStatus = Field(..., description="Current status of the evaluation", example="IN_PROGRESS")


class AgentStepResponse(BaseModel):
    id: int = Field(..., description="Unique identifier for the agent step", example=1)
    step_index: int = Field(..., description="Index of the step in the sequence", example=1)
    system_prompt: str = Field(..., description="System prompt used for this step", example="You are a helpful assistant")
    user_prompt: str = Field(..., description="User prompt for this step", example="Find information about Python")
    strategy: str = Field(..., description="Strategy used for this step", example="search_and_retrieve")
    previous_responses: Optional[str] = Field(None, description="Previous responses in the conversation", example=None)
    current_response: str = Field(..., description="Current response from the agent", example="I'll search for Python information")
    chat_index: int = Field(..., description="Index in the chat history", example=1)
    step_score: Optional[Dict[str, Any]] = Field(None, description="Detailed step scoring", example={"relevance": 0.8, "accuracy": 0.9})
    step_score_aggregated: Optional[float] = Field(None, description="Aggregated step score", example=0.85)
    step_quality: Optional[str] = Field(None, description="Quality assessment of the step", example="good")


class AgentTraceResponse(BaseModel):
    invocation_id: str = Field(..., description="Unique identifier for the trace invocation", example="invocation_1")
    agent_type: str = Field(..., description="Type of the agent", example="RAG")
    invocation_msg: str = Field(..., description="Message that invoked this agent", example="Please help me find information about Python")
    invocated_by: str = Field(..., description="Who invoked this agent", example="user")
    available_tools: str = Field(..., description="Tools available to the agent", example="search, retrieve, summarize")
    chat_history: List[Dict[str, Any]] = Field(..., description="Chat history for this trace", example=[{"role": "user", "content": "Hello"}])
    agent_steps: List[AgentStepResponse] = Field(..., description="Steps taken by the agent in this trace")


class AgentTracesResponse(BaseModel):
    evaluation_id: int = Field(..., description="ID of the evaluation", example=1)
    agent_name: str = Field(..., description="Name of the agent", example="RAG_Agent")
    agent_id: int = Field(..., description="ID of the agent", example=1)
    traces: List[AgentTraceResponse] = Field(..., description="List of agent traces")


class AgentResponse(BaseModel):
    id: int = Field(..., description="Unique identifier for the agent", example=1)
    name: str = Field(..., description="Name of the agent", example="RAG_Agent")
    trace_id: str = Field(..., description="Trace ID associated with the agent", example="agent_trace_456")
    tool_metrics: Optional[Dict[str, Any]] = Field(None, description="Tool usage metrics", example={"tool_usage": 5, "tool_success_rate": 0.8})
    stepwise_metrics: Optional[Dict[str, Any]] = Field(None, description="Step-wise performance metrics", example={"avg_step_score": 0.75})


class EvaluationResponse(BaseModel):
    id: int = Field(..., description="Unique identifier for the evaluation", example=1)
    trace_id: str = Field(..., description="Trace ID for the evaluation", example="trace_abc123")
    created_at: datetime = Field(..., description="When the evaluation was created", example="2024-01-15T10:30:00Z")
    status: str = Field(..., description="Current status of the evaluation", example="COMPLETED")
    agents: List[AgentResponse] = Field(..., description="List of agents in this evaluation")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message", example="Evaluation not found")
