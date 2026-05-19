"""
Tool 1: Web Search
Uses Tavily API to search the web for current information.
Name: web_search
Description: Searches the web for real-time information about any topic.
Parameters:
  - query (str): The search query to look up.
"""

import os
import requests
from langchain.tools import tool


def web_search_keyless(query: str) -> str:
    """Fallback search using DuckDuckGo Instant Answers and Wikipedia APIs."""
    results = []

    # 1. Try DuckDuckGo Instant Answers
    try:
        ddg_url = "https://api.duckduckgo.com/"
        ddg_params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }
        ddg_resp = requests.get(ddg_url, params=ddg_params, headers={"User-Agent": "VoiceAgent/1.0"}, timeout=8)
        if ddg_resp.status_code == 200:
            ddg_data = ddg_resp.json()
            abstract = ddg_data.get("AbstractText", "")
            abstract_url = ddg_data.get("AbstractURL", "")
            if abstract:
                results.append(f"Resumen (DuckDuckGo): {abstract}\nFuente: {abstract_url}")
    except Exception as e:
        print(f"[Search Fallback] DDG error: {e}")

    # 2. Try Wikipedia Search
    try:
        wiki_url = "https://es.wikipedia.org/w/api.php"
        wiki_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "utf8": 1,
            "format": "json"
        }
        wiki_resp = requests.get(wiki_url, params=wiki_params, headers={"User-Agent": "VoiceAgent/1.0"}, timeout=8)
        if wiki_resp.status_code == 200:
            wiki_data = wiki_resp.json()
            search_results = wiki_data.get("query", {}).get("search", [])
            if search_results:
                results.append("\nResultados de Wikipedia:")
                from bs4 import BeautifulSoup
                for i, item in enumerate(search_results[:3], 1):
                    title = item.get("title")
                    snippet = item.get("snippet", "")
                    clean_snippet = BeautifulSoup(snippet, "html.parser").get_text()
                    pageid = item.get("pageid")
                    source_url = f"https://es.wikipedia.org/?curid={pageid}"
                    results.append(f"{i}. {title}\n   {clean_snippet}\n   Fuente: {source_url}")
    except Exception as e:
        print(f"[Search Fallback] Wikipedia error: {e}")

    return "\n".join(results) if results else "No se encontraron resultados de búsqueda web."


@tool
def web_search(query: str) -> str:
    """
    Search the web for real-time, up-to-date information on any topic.
    Use this when the user asks about current events, news, facts,
    or anything that requires fresh information from the internet.

    Args:
        query: The search query string.

    Returns:
        A formatted string with the search results.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return web_search_keyless(query)

    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": 4,
            "include_answer": True,
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code in (401, 403):
            print("[Search] Invalid TAVILY_API_KEY, falling back to keyless search.")
            return web_search_keyless(query)
        response.raise_for_status()
        data = response.json()

        # Build a clean result string
        parts = []
        if data.get("answer"):
            parts.append(f"Summary: {data['answer']}")

        if data.get("results"):
            parts.append("\nTop results:")
            for i, result in enumerate(data["results"][:3], 1):
                title = result.get("title", "No title")
                content = result.get("content", "")[:300]
                url_res = result.get("url", "")
                parts.append(f"\n{i}. {title}\n   {content}\n   Source: {url_res}")

        return "\n".join(parts) if parts else "No results found."

    except requests.exceptions.Timeout:
        return "Web search timed out. Please try again."
    except requests.exceptions.RequestException as e:
        return f"Web search error: {str(e)}"
    except Exception as e:
        return f"Unexpected error during web search: {str(e)}"
