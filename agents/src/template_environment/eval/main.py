from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Any, List
import uvicorn

from utils.sql_utils import Evaluation, Agent, AgentTrace, get_db
from utils.trace_utils import get_px_trace_spans
from models.api_models import (
    RunEvaluationRequest,
    RunEvaluationResponse,
    AgentTracesResponse,
    EvaluationResponse,
    ErrorResponse,
)
from services.evaluation_service import EvaluationService

app = FastAPI(title="Agent Evaluation API")
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
evaluation_service = EvaluationService()


@app.post("/run_evaluations", response_model=RunEvaluationResponse)
async def create_evaluation(
    request: RunEvaluationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Create a new evaluation for a trace ID and run it in the background.
    """

    # Check if evaluation already exists
    db_eval = (
        db.query(Evaluation).filter(Evaluation.trace_id == request.trace_id).first()
    )
    if db_eval:
        return {
            "evaluation_id": str(db_eval.id),
            "evaluation_status": db_eval.status,
        }

    # Create new evaluation
    db_eval = Evaluation(trace_id=request.trace_id)
    db.add(db_eval)
    db.commit()
    db.refresh(db_eval)

    # Fetch trace spans
    trace_df = get_px_trace_spans(request.trace_id, request.project_name)

    # Run evaluation in background
    # Pass a new DB session to avoid threading issues
    def background_task_wrapper(evaluation_id: int, trace_df: Any):
        with next(get_db()) as bg_db:
            evaluation_service.run_evaluation(evaluation_id, trace_df, bg_db)

    background_tasks.add_task(background_task_wrapper, db_eval.id, trace_df)

    return {
        "evaluation_id": str(db_eval.id),
        "evaluation_status": db_eval.status,
    }

@app.get(
    "/evaluations",
    response_model=List[EvaluationResponse],
    responses={
        200: {
            "description": "List of all evaluations",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "trace_id": "trace_abc123",
                            "created_at": "2024-01-15T10:30:00Z",
                            "status": "COMPLETED",
                            "agents": [
                                {
                                    "id": 1,
                                    "name": "RAG_Agent",
                                    "trace_id": "agent_trace_456",
                                    "tool_metrics": {
                                        "tool_usage": 5,
                                        "tool_success_rate": 0.8
                                    },
                                    "stepwise_metrics": {
                                        "avg_step_score": 0.75
                                    }
                                }
                            ]
                        }
                    ]
                }
            }
        },
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    tags=["Evaluations"],
    summary="Get all evaluations"
)
async def get_evaluations(db: Session = Depends(get_db)):
    """
    Retrieve all evaluations with their associated agents and metrics.
    
    Returns a list of evaluations ordered by creation date (most recent first).
    Each evaluation includes:
    - Basic evaluation information (ID, trace ID, status, creation date)
    - List of associated agents with their metrics
    - Tool usage and step-wise performance metrics for each agent
    """
    evaluations = (
        db.query(Evaluation)
        .order_by(Evaluation.created_at.desc())
        .all()
    )
    
    result = []
    for eval in evaluations:
        eval_data = {
            "id": eval.id,
            "trace_id": eval.trace_id,
            "created_at": eval.created_at,
            "status": eval.status,
            "agents": []
        }
        
        for agent in eval.agents:
            agent_data = {
                "id": agent.id,
                "name": agent.name,
                "trace_id": agent.trace_id,
                "tool_metrics": agent.tool_metrics,
                "stepwise_metrics": agent.stepwise_metrics
            }
            eval_data["agents"].append(agent_data)
            
        result.append(eval_data)
    
    return result

@app.get(
    "/evaluations/{evaluation_id}",
    response_model=EvaluationResponse,
    responses={
        200: {
            "description": "Detailed evaluation information",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "trace_id": "trace_abc123",
                        "created_at": "2024-01-15T10:30:00Z",
                        "status": "COMPLETED",
                        "agents": [
                            {
                                "id": 1,
                                "name": "RAG_Agent",
                                "trace_id": "agent_trace_456",
                                "tool_metrics": {
                                    "tool_usage": 5,
                                    "tool_success_rate": 0.8
                                },
                                "stepwise_metrics": {
                                    "avg_step_score": 0.75
                                }
                            }
                        ]
                    }
                }
            }
        },
        404: {"model": ErrorResponse, "description": "Evaluation not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    tags=["Evaluations"],
    summary="Get evaluation details"
)
async def get_evaluation_details(evaluation_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific evaluation.
    
    Returns comprehensive information about an evaluation including:
    - Evaluation metadata (ID, trace ID, status, creation date)
    - All associated agents and their performance metrics
    - Tool usage statistics and step-wise evaluation scores
    
    Args:
        evaluation_id: The unique identifier of the evaluation to retrieve
    
    Raises:
        HTTPException: 404 if the evaluation is not found
    """
    evaluation = (
        db.query(Evaluation)
        .filter(Evaluation.id == evaluation_id)
        .first()
    )
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    result = {
        "id": evaluation.id,
        "trace_id": evaluation.trace_id,
        "created_at": evaluation.created_at,
        "status": evaluation.status,
        "agents": []
    }
    
    for agent in evaluation.agents:
        agent_data = {
            "id": agent.id,
            "name": agent.name,
            "trace_id": agent.trace_id,
            "tool_metrics": agent.tool_metrics,
            "stepwise_metrics": agent.stepwise_metrics
        }
        result["agents"].append(agent_data)
    
    return result


@app.get(
    "/evaluations/{evaluation_id}/agents/{agent_name}/traces",
    response_model=AgentTracesResponse,
    responses={
        200: {
            "description": "Agent traces retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "evaluation_id": 1,
                        "agent_name": "RAG_Agent",
                        "agent_id": 1,
                        "traces": [
                            {
                                "invocation_id": "invocation_1",
                                "agent_type": "RAG",
                                "invocation_msg": "Please help me find information about Python",
                                "invocated_by": "user",
                                "available_tools": "search, retrieve, summarize",
                                "chat_history": [
                                    {"role": "user", "content": "Hello"}
                                ],
                                "agent_steps": [
                                    {
                                        "id": 1,
                                        "step_index": 1,
                                        "system_prompt": "You are a helpful assistant",
                                        "user_prompt": "Find information about Python",
                                        "strategy": "search_and_retrieve",
                                        "previous_responses": None,
                                        "current_response": "I'll search for Python information",
                                        "chat_index": 1,
                                        "step_score": {
                                            "relevance": 0.8,
                                            "accuracy": 0.9
                                        },
                                        "step_score_aggregated": 0.85,
                                        "step_quality": "good"
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        },
        404: {"model": ErrorResponse, "description": "Evaluation or agent not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    tags=["Agent Traces"],
    summary="Get agent traces by name and evaluation ID"
)
async def get_agent_traces(
    evaluation_id: int, 
    agent_name: str, 
    db: Session = Depends(get_db)
):
    """
    Get all agent traces for a specific agent by agent name and evaluation_id.
    
    This endpoint retrieves comprehensive trace information for a specific agent
    within an evaluation, including:
    - All trace invocations for the agent
    - Detailed step-by-step execution information
    - Performance metrics and quality scores for each step
    - Chat history and tool usage information
    
    Args:
        evaluation_id: The unique identifier of the evaluation
        agent_name: The name of the agent to retrieve traces for
    
    Returns:
        AgentTracesResponse: Complete trace information including all steps and metrics
    
    Raises:
        HTTPException: 404 if the evaluation or agent is not found
    """
    # First, verify the evaluation exists
    evaluation = (
        db.query(Evaluation)
        .filter(Evaluation.id == evaluation_id)
        .first()
    )
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    # Find the agent by name within this evaluation
    agent = (
        db.query(Agent)
        .filter(Agent.evaluation_id == evaluation_id)
        .filter(Agent.name == agent_name)
        .first()
    )
    
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Agent '{agent_name}' not found in evaluation {evaluation_id}"
        )
    
    # Get all agent traces for this agent
    agent_traces = (
        db.query(AgentTrace)
        .filter(AgentTrace.agent_id == agent.id)
        .all()
    )
    
    result = {
        "evaluation_id": evaluation_id,
        "agent_name": agent_name,
        "agent_id": agent.id,
        "traces": []
    }
    
    for trace in agent_traces:
        trace_data = {
            "invocation_id": trace.invocation_id,
            "agent_type": trace.agent_type,
            "invocation_msg": trace.invocation_msg,
            "invocated_by": trace.invocated_by,
            "available_tools": trace.available_tools,
            "chat_history": trace.chat_history,
            "agent_steps": []
        }
        
        # Include agent steps for each trace
        for step in trace.agent_steps:
            step_data = {
                "id": step.id,
                "step_index": step.step_index,
                "system_prompt": step.system_prompt,
                "user_prompt": step.user_prompt,
                "strategy": step.strategy,
                "previous_responses": step.previous_responses,
                "current_response": step.current_response,
                "chat_index": step.chat_index,
                "step_score": step.step_score,
                "step_score_aggregated": step.step_score_aggregated,
                "step_quality": step.step_quality
            }
            trace_data["agent_steps"].append(step_data)
        
        result["traces"].append(trace_data)
    
    return result

if __name__ == "__main__":

    uvicorn.run(
        "main:app",  # this file is main.py
        host="0.0.0.0",
        port=8000,
        reload=True,
    )