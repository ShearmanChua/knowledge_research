from autogen_core.tools import FunctionTool
from ddgs import DDGS
import requests
from markdownify import markdownify as html_to_md
from autogen_core import CancellationToken
from playwright.async_api import async_playwright

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

    async def search(self, query: str, page: int = 1, max_results: int = 10):
        """
        DuckDuckGo search
        """

        # DuckDuckGo Search API (text search)
        results = list(
            self.ddg.text(
                query=query,
                region="us-en",
                safesearch="moderate",
                timelimit="y",
                max_results=max_results,
                page=page,
                backend="google",
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

    async def fetch(self, url: str):
        """
        Fetch a webpage using Playwright Async API.
        Handles HTML, PDFs, Cloudflare, and JS-heavy sites.
        """
        # ---------- PDF detection (URL hint) ----------
        if url.lower().endswith(".pdf"):
            try:
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                return "PDF content detected — binary file skipped."
            except Exception as e:
                return f"Error fetching PDF: {e}"

        # ---------- HTML fetch via Playwright ----------
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                    ]
                )

                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/123.0.0.0 Safari/537.36"
                    )
                )

                page = await context.new_page()

                try:
                    # robust JS loading
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=15000
                    )
                except Exception:
                    # retry once with looser settings
                    try:
                        await page.goto(url, timeout=15000)
                    except Exception as e:
                        await browser.close()
                        return f"Error fetching page: {e}"

                # allow JS to finish rendering
                await page.wait_for_timeout(2000)

                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass  # Not all sites reach networkidle

                # Retry extracting HTML a few times if the page is still navigating
                html = None
                for _ in range(3):
                    try:
                        html = await page.content()
                        break
                    except Exception:
                        await page.wait_for_timeout(500)

                if html is None:
                    await browser.close()
                    return "Error: page kept navigating; unable to extract content."

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
        """
        Perform Web Search using DuckDuckGo (each query overwrites existing results).

        WARNING: Search results get replaced when a new query is performed. Therefore, ONLY perform one query at a time
        and open the required webpages/results before moving onto the next query. 

        e.g. workflow: search -> select_webpage -> next_page -> select_webpage -> search
        """
        self.current_query = query
        self.current_page = page
        self.current_results = await self.api.search(query, page)

        return {
            "query": query,
            "page": page,
            "results": self.current_results
        }

    @trace_span_info
    async def select_webpage(self, url: str):
        """Fetch selected webpage content by URL."""
        if not url:
            return {"error": "No URL provided"}

        content = await self.api.fetch(url)

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
        self.current_results = await self.api.search(self.current_query, self.current_page)

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
    
