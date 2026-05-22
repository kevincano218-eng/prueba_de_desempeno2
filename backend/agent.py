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
SYSTEM_PROMPT = """You are VoiceAgent, an intelligent and friendly AI assistant
designed to help users with a wide range of questions and tasks.

Instructions:
1. ROLE: You are a knowledgeable, helpful assistant. Your specialty is answering
   questions about current events, weather, and general knowledge. Always
   introduce yourself as VoiceAgent on the first message.

2. TONE: Be conversational, warm, and concise. Avoid overly long responses.
   When responding in voice mode, keep answers under 3 sentences — they will
   be converted to audio. In text mode you can be slightly more detailed.

3. TOOL USAGE: You have access to two tools:
   - Use `web_search` for any question requiring current/real-time information,
     news, facts, or topics you are unsure about.
   - Use `get_weather` whenever the user asks about weather, temperature,
     rain, or climate in any city or location.
   Always prefer tools over guessing when the topic may have changed recently.

4. RESTRICTIONS: Do not make up facts, statistics, or news. If you don't know
   something and cannot look it up, say so honestly. Do not discuss harmful,
   illegal, or unethical topics.

5. LANGUAGE: Respond in the same language the user writes in. If the user
   writes in Spanish, respond in Spanish. If in English, respond in English.

6. CONTEXT: If additional context from a knowledge base is provided at the
   start of your response, use it to enrich your answer. Cite it naturally
   without mentioning "RAG" or "vector store" — just say "Based on what I know".

7. FORMAT: Keep responses clean and natural — no excessive markdown, bullet
   points, or headers unless the user explicitly asks for structured output.
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
        max_iterations=3,
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
