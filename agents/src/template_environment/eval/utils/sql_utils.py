from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    JSON,
    DateTime,
    ForeignKey,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone

Base = declarative_base()


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    status = Column(String, default="IN_PROGRESS")  # IN_PROGRESS, COMPLETED, FAILED

    # Relationships
    agents = relationship(
        "Agent",
        back_populates="evaluation",
        cascade="all, delete-orphan",
    )


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"))
    trace_id = Column(String, unique=True, index=True)
    name = Column(String)  # Type of agent (e.g., "RAG", "Triage", etc.)
    tool_metrics = Column(JSON, nullable=True)  # Store tool metrics as JSON
    stepwise_metrics = Column(JSON, nullable=True)  # Store stepwise metrics as JSON

    # Relationships
    evaluation = relationship("Evaluation", back_populates="agents")
    agent_traces = relationship(
        "AgentTrace", back_populates="agent", cascade="all, delete-orphan"
    )


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    invocation_id = Column(String, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    agent_type = Column(String)  # Type of agent (e.g., "RAG", "Triage", etc.)

    # Invocation information
    invocation_msg = Column(String)  # The message that invoked this agent
    invocated_by = Column(String)  # Who invoked this agent
    available_tools = Column(String)  # JSONL string of available tools
    chat_history = Column(JSON)

    # Relationships
    agent = relationship("Agent", back_populates="agent_traces")
    agent_steps = relationship(
        "AgentStep", back_populates="agent_trace", cascade="all, delete-orphan"
    )


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id = Column(Integer, primary_key=True, index=True)
    trace_invocation_id = Column(String, ForeignKey("agent_traces.invocation_id"))
    step_index = Column(Integer)
    system_prompt = Column(String)
    user_prompt = Column(String)
    strategy = Column(String)
    previous_responses = Column(String, nullable=True)
    current_response = Column(String)
    chat_index = Column(Integer)

    # Step score fields
    step_score = Column(
        JSON, nullable=True
    )  # Store the entire step_score object as JSON
    step_score_aggregated = Column(Float, nullable=True)
    step_quality = Column(String, nullable=True)

    # Relationship
    agent_trace = relationship("AgentTrace", back_populates="agent_steps")


class ToolUsefulness(Base):
    __tablename__ = "tool_usefulness"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String, index=True)
    tool_name = Column(String)
    tool_usefulness_reason = Column(String)
    tool_usefulness = Column(Float)


# Create PostgreSQL database connection
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://user:password@postgres:5432/postgres"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,       # helps keep connections alive
    pool_size=10,             # optional: adjust for concurrency
    max_overflow=20,          # optional: allow extra connections
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
