"""
VoiceAgent — FastAPI Backend
Routes: POST /chat, POST /tts, DELETE /session/{id}, GET /health
"""

import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv(override=True)

from agent import run_agent, clear_session
from tts import synthesize_speech
from rag.pipeline import initialize_rag
from tools import TOOL_DISPLAY_NAMES


# ---------------------------------------------------------------------------
# Lifespan — initialize RAG on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[VoiceAgent] Starting up...")
    rag_url = os.getenv("RAG_SOURCE_URL", "")
    if rag_url:
        print(f"[VoiceAgent] Initializing RAG from: {rag_url}")
        initialize_rag(rag_url)
    else:
        print("[VoiceAgent] RAG_SOURCE_URL not set, RAG disabled.")
    yield
    print("[VoiceAgent] Shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="VoiceAgent API",
    version="1.0.0",
    description="Conversational AI agent with tools and voice synthesis.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    voice_mode: bool = False


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tools_used: list[str]
    tool_display_names: list[str]
    audio_base64: Optional[str] = None
    tts_provider: Optional[str] = None


class TTSRequest(BaseModel):
    text: str


class TTSResponse(BaseModel):
    audio_base64: Optional[str]
    provider: Optional[str]
    error: Optional[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "VoiceAgent"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Main chat endpoint. Accepts a user message, runs the agent,
    and optionally synthesizes the response as audio.
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Generate session ID if not provided
    session_id = req.session_id or str(uuid.uuid4())

    # Run agent
    try:
        result = await run_agent(
            user_message=req.message.strip(),
            session_id=session_id,
        )
    except Exception as e:
        print(f"[Agent error] {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    response_text = result["response"]
    tools_used = result["tools_used"]
    display_names = [TOOL_DISPLAY_NAMES.get(t, t) for t in tools_used]

    # Synthesize audio if voice mode is enabled
    audio_base64 = None
    tts_provider = None

    if req.voice_mode and response_text:
        tts_result = synthesize_speech(response_text)
        audio_base64 = tts_result.get("audio_base64")
        tts_provider = tts_result.get("provider")
        if tts_result.get("error"):
            print(f"[TTS warning] {tts_result['error']}")

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        tools_used=tools_used,
        tool_display_names=display_names,
        audio_base64=audio_base64,
        tts_provider=tts_provider,
    )


@app.post("/tts", response_model=TTSResponse)
async def tts(req: TTSRequest):
    """Standalone TTS endpoint. Converts text to audio."""
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    result = synthesize_speech(req.text.strip())
    return TTSResponse(
        audio_base64=result.get("audio_base64"),
        provider=result.get("provider"),
        error=result.get("error"),
    )


@app.delete("/session/{session_id}")
async def clear_session_route(session_id: str):
    """Clear the conversation memory for a given session."""
    clear_session(session_id)
    return {"cleared": session_id}
