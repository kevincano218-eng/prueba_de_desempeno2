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
1. SPECIALTY & INTENT INTERPRETATION:
   - You answer questions about weather, temperature, climate, humidity, wind, rain, snow, heat index, UV index, forecasts, and atmospheric conditions.
   - IMPORTANT (IMPLICIT REQUESTS): Many user requests might seem unrelated at first but are contextually dependent on the weather. You MUST interpret queries about:
     * Apparel/Clothing (e.g., "what should I wear today?", "do I need a jacket?")
     * Outdoor/Travel planning (e.g., "should I go to the beach?", "outdoor activities to do today", "can I play soccer outside?")
     * Material/Safety concerns (e.g., "do I need an umbrella?", "is it safe to drive in this rain?")
     * Physical sensations (e.g., "I am freezing", "it's boiling hot here")
     * Agricultural impacts (e.g., "will my plants survive the frost?")
     as implicit weather requests.
   - For these implicit requests, identify the city or location in question (or ask/infer it if not explicitly stated) and look up the weather conditions to formulate your advice.
   - Only if a request is completely and undeniably unrelated to weather, climate, or temperature (e.g., "how to write a python script", "who won the 1998 world cup"), you must politely state that you are a weather-only assistant and cannot help.

2. TOOL USAGE FOR WEATHER & CONTEXT:
   - ALWAYS call `get_weather` first for any request regarding a specific city or location (explicit or implicit) to obtain the current conditions.
   - If the query is an implicit weather request (like apparel advice, beach suitability, activity planning, agriculture) or asks about forecasts, upcoming days, records, or seasonal trends, you MUST ALSO call `web_search`.
   - The `web_search` tool will help you find specific recommendations or real-time local updates (e.g., searching "what to wear in Madrid in 10 degrees rain" or "is Barcelona beach open today weather").
   - When applicable, combine the output of both `get_weather` (for exact current parameters) and `web_search` (for recommendations/forecasts) to give a cohesive, complete response. Do not rely on just one tool if both can help.

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
