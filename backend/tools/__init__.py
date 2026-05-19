from .web_search import web_search
from .weather import get_weather

TOOLS = [web_search, get_weather]

TOOL_DISPLAY_NAMES = {
    "web_search": "Web Search",
    "get_weather": "Weather",
}
