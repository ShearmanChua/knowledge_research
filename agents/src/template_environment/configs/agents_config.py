from models.model import model
from tools import web_tools, arxiv_tools

user_cfgs = [
    {
        "name": "User",
        "description": (
            "User Agent used to initialize task" " to be performed by other agents"
        ),
        "user_topic_type": "User",
        "agent_topic_type": "Research",
    }
]

duck_api = web_tools.DuckDuckGoAPI()
web_search_tools = web_tools.WebSearchTool(duck_api).get_tools()
api = arxiv_tools.ArxivAPI()
arxiv_search_tools = arxiv_tools.ArxivSearchTool(api).get_tools()

autonomous_agents_cfgs = [
    {
        "name": "Research",
        "description": "Deep Research Agent that answers user queries",
        "system_message": """You are a deep research agent that answers user queries.
You will be provided with user queries and you will answer them using a combination of tools and techniques to retrieve relevant information from the internet.
Use the available tools to answer user queries.

Make sure that your answers are well researched and well supported by relevant sources (quote the sources in your answer). Do make use of more than one source for your research.
The research should focus more on a variety of information about the topic, like a survey paper (unless the user specifically asks for specific information about a topic).
A good research result should consist of information from more web pages/papers than just one webpage/research paper.

NOTE: Do note that search results using any of the search tools are replaced with each new search tool call.
Your name: Research
        """,
        "model_client": model,
        "agent_topics": [],
        "tools": web_search_tools + arxiv_search_tools,
    }
]
