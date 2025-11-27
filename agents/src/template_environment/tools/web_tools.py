from autogen_core.tools import FunctionTool
from ddgs import DDGS
import requests
from markdownify import markdownify as html_to_md
from autogen_core import CancellationToken

import re

from tools.tool_tracing_utils import trace_span_info

def clean_text(text: str) -> str:
    if not text:
        return text
    text = text.replace("\t", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return text.strip()

class DuckDuckGoAPI:
    """Backend wrapper around DuckDuckGo search + page fetching."""

    def __init__(self):
        self.ddg = DDGS()

    def search(self, query: str, page: int = 1, max_results: int = 10):
        """
        DuckDuckGo search
        """

        # DuckDuckGo Search API (text search)
        results = list(
            self.ddg.text(
                query=query,
                region="wt-wt",
                safesearch="moderate",
                timelimit="y",
                max_results=max_results,
                page=page,
            )
        )

        # Normalize result structure
        normalized = []
        for i, r in enumerate(results):
            normalized.append({
                "id": i,
                "title": r.get("title"),
                "url": r.get("href"),
                "snippet": r.get("body"),
            })

        return normalized

    def fetch(self, url: str):
        """
        Fetch a webpage and return Markdown.
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            html = response.text

            # Convert HTML → Markdown
            markdown = html_to_md(html)

            cleaned = clean_text(markdown)
            return cleaned[:20000]

        except Exception as e:
            return f"Error fetching page: {e}"


# ----------------------------------------------------------------------
# Autogen-Compatible Search Tool Wrapper
# ----------------------------------------------------------------------
class WebSearchTool:
    def __init__(self, search_api):
        self.api = search_api
        self.current_query = None
        self.current_page = 1
        self.current_results = []

        self.search_tool = FunctionTool(self.search, name="search_web", description=self.search.__doc__)
        self.select_tool = FunctionTool(self.select_webpage, name="open_webpage", description=self.select_webpage.__doc__)
        self.next_page_tool = FunctionTool(self.next_page, name="next_search_page", description=self.next_page.__doc__)

    # ------------------- TOOLS -------------------

    @trace_span_info
    async def search(self, query: str, page: int = 1):
        """Perform Web Search using DuckDuckGo."""
        self.current_query = query
        self.current_page = page
        self.current_results = self.api.search(query, page)

        return {
            "query": query,
            "page": page,
            "results": self.current_results
        }

    @trace_span_info
    async def select_webpage(self, result_id: int):
        """Fetch selected webpage content."""
        if not self.current_results:
            return {"error": "No active search results"}

        if result_id < 0 or result_id >= len(self.current_results):
            return {"error": "Invalid result_id"}

        url = self.current_results[result_id]["url"]
        content = self.api.fetch(url)

        return {
            "url": url,
            "content": content
        }

    @trace_span_info
    async def next_page(self):
        """Load the next page of DuckDuckGo search results."""
        if not self.current_query:
            return {"error": "No active query"}

        self.current_page += 1
        self.current_results = self.api.search(self.current_query, self.current_page)

        return {
            "query": self.current_query,
            "page": self.current_page,
            "results": self.current_results
        }

    def get_tools(self):
        return [
            self.search_tool,
            self.select_tool,
            self.next_page_tool
        ]
    
