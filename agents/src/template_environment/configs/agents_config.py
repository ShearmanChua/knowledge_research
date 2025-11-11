from models.model import model
from tools import delegate_tasks, rag, web_search

user_cfgs = [
    {
        "name": "User",
        "description": (
            "User Agent used to initialize task" " to be performed by other agents"
        ),
        "user_topic_type": "User",
        "agent_topic_type": "Triage",
    }
]

autonomous_agents_cfgs = [
    {
        "name": "Triage",
        "description": "Triage agent to triage user tasks",
        "system_message": """You are a triage agent. You are responsible for triaging
user tasks and delegating them to the appropriate agents. You will receive user tasks
from the user agent and delegate them to the appropriate agents.

Your name: Triage
        """,
        "model_client": model,
        "delegate_tools": [delegate_tasks],
        "agent_topics": ["RAG", "WebSearch"],
        "handoff": True,
        "broadcast_topic": "PLACEHOLDER_BROADCAST",
    },
    {
        "name": "RAG",
        "description": (
            "An agent that uses Retrieval Augmented Generation to answer user "
            "queries"
        ),
        "system_message": """You are a RAG agent. You are responsible for answering user
queries. You will receive user queries from the user agent and answer them using
retrieved information.""",
        "model_client": model,
        "delegate_tools": [],
        "tools": [rag],
        "agent_topics": [],
        "handoff": False,
    },
    {
        "name": "WebSearch",
        "description": "An agent that performs web search to answer user queries",
        "system_message": (
            "You are a WebSearch agent. You are responsible for answering user "
            "queries. You will receive user queries from the user agent and answer "
            "them using retrieved information."
        ),
        "model_client": model,
        "delegate_tools": [],
        "tools": [web_search],
        "agent_topics": [],
        "handoff": False,
    },
    {
        "name": "Consolidate",
        "description": "Consolidate agent to answer user queries",
        "system_message": (
            "You are a Consolidate agent. You are responsible for aggragating "
            "information from other agents and answering user queries. You will "
            "receive information from other agents and answer user queries using "
            "the information."
        ),
        "model_client": model,
        "delegate_tools": [],
        "tools": [],
        "agent_topics": [],
    },
]
