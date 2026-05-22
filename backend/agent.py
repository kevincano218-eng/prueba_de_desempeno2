"""
Agent Core — LangChain agent with Claude, memory, and tools.
Maintains a sliding window of 7 messages per session.
"""

import os
from typing import Optional
from collections import defaultdict

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import SystemMessage

from tools import TOOLS
from rag.pipeline import retrieve_context

# ---------------------------------------------------------------------------
# System prompt — defines role, tone, and constraints (5+ instructions)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are VoiceAgent, a specialized weather and climate assistant.

Instructions:
1. SPECIALTY: You ONLY answer questions about weather, temperature, climate,
   humidity, wind, rain, snow, heat index, feels-like temperature, UV index,
   air quality, forecasts, and atmospheric conditions in any location worldwide.
   For ANY other topic, politely respond that you are a weather-only assistant
   and cannot help with that.

2. TOOL USAGE FOR WEATHER:
   - ALWAYS call `get_weather` first for any weather-related question about
     a specific city or location. This gives you current conditions.
   - If the user asks about forecasts, upcoming days, weather records,
     comparisons between cities, seasonal trends, or any weather info beyond
     the current moment, ALSO use `web_search` to find that information.
   - Always use both tools when needed — do not rely on only one.

3. ACCURACY: Never guess weather data. Always use the tools. If a tool fails
   or returns no data, honestly say the information is unavailable.

4. TONE: Be conversational, warm, and concise.
   - In voice mode: keep answers under 3 sentences (will be converted to audio).
   - In text mode: you can be slightly more detailed but stay focused.

5. LANGUAGE: Respond in the same language the user writes in. If Spanish,
   respond in Spanish. If English, respond in English.

6. FORMAT: Keep responses clean and natural. No excessive markdown or headers.
   When both tools are used, mention the key data naturally.
{rag_context}"""


# ---------------------------------------------------------------------------
# Session memory store (in-memory, keyed by session_id)
# ---------------------------------------------------------------------------
_session_memories: dict = defaultdict(lambda: ConversationBufferWindowMemory(
    k=7,
    memory_key="chat_history",
    return_messages=True,
))


def _build_agent(rag_context: str = "") -> AgentExecutor:
    """Build a new LangChain agent with the configured tools."""
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.7,
        max_tokens=1024,
    )

    context_block = ""
    if rag_context:
        context_block = f"\n\nAdditional context from knowledge base:\n{rag_context}"

    system_content = SYSTEM_PROMPT.format(rag_context=context_block)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_content),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, TOOLS, prompt)
    return AgentExecutor(
        agent=agent,
        tools=TOOLS,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=4,
        return_intermediate_steps=True,
    )


async def run_agent(
    user_message: str,
    session_id: str = "default",
) -> dict:
    """
    Run the agent with the user's message.

    Args:
        user_message: The user's input text.
        session_id: Unique session identifier for memory isolation.

    Returns:
        dict with:
          - response (str): The agent's text reply.
          - tools_used (list[str]): Names of tools invoked, empty if none.
    """
    memory = _session_memories[session_id]

    # Retrieve RAG context if available
    rag_context = retrieve_context(user_message)

    # Build fresh agent (tools + RAG context baked in)
    executor = _build_agent(rag_context=rag_context)

    # Run with current memory history (respecting sliding window size k)
    chat_history = memory.load_memory_variables({})["chat_history"]

    result = executor.invoke({
        "input": user_message,
        "chat_history": chat_history,
    })

    # Save to memory
    memory.save_context(
        {"input": user_message},
        {"output": result["output"]},
    )

    # Extract which tools were used
    tools_used = []
    for step in result.get("intermediate_steps", []):
        if step and len(step) >= 1:
            action = step[0]
            tool_name = getattr(action, "tool", None)
            if tool_name and tool_name not in tools_used:
                tools_used.append(tool_name)

    return {
        "response": result["output"],
        "tools_used": tools_used,
    }


def clear_session(session_id: str) -> None:
    """Clear conversation memory for a session."""
    if session_id in _session_memories:
        _session_memories[session_id].clear()
