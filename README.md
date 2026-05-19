# VoiceAgent

A multimodal conversational AI web application. Users interact with an intelligent agent by typing or speaking, and the agent responds in text or synthesized voice. The agent has access to real tools and the UI shows when each tool is activated.

**Use case:** General-purpose AI assistant with real-time web search, live weather data, and persistent knowledge retrieval (RAG).

---

## Architecture

```
voiceagent/
├── backend/              # Python FastAPI server
│   ├── main.py           # API routes: /chat, /tts, /health
│   ├── agent.py          # LangChain agent + 7-message memory
│   ├── tts.py            # ElevenLabs / OpenAI TTS synthesis
│   ├── tools/
│   │   ├── web_search.py # Tool 1: Web search (Tavily with DuckDuckGo fallback)
│   │   └── weather.py    # Tool 2: Weather (OpenWeatherMap with Open-Meteo fallback)
│   ├── rag/
│   │   └── pipeline.py   # RAG: Scrapes URL at startup → Supabase Vector Store
│   └── requirements.txt
├── frontend/             # React + Vite
│   └── src/
│       ├── App.jsx       # Main chat UI
│       ├── api.js        # Backend API calls
│       ├── components/
│       │   ├── MessageBubble.jsx  # Chat messages with tool badges
│       │   ├── ToolBadge.jsx      # Visual tool indicator
│       │   ├── AudioPlayer.jsx    # Voice playback controls
│       │   ├── VoiceToggle.jsx    # Text / Voice mode toggle
│       │   └── TypingIndicator.jsx
│       └── hooks/
│           └── useVoiceInput.js   # Web Speech API hook
├── .env.example
└── README.md
```

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- API keys (see Environment Variables below)
- A Supabase Project (for Persistent RAG)

---

## Setup & Installation

### 1. Database Setup (Supabase)
To use the RAG capabilities, create a project on [Supabase](https://supabase.com). Go to the **SQL Editor** in your dashboard and run the following script to create the necessary vector tables and functions:

```sql
create extension if not exists vector;

create table documents (
  id uuid primary key default uuid_generate_v4(),
  content text,
  metadata jsonb,
  embedding vector(384)
);

create function match_documents (
  query_embedding vector(384),
  match_count int DEFAULT null,
  filter jsonb DEFAULT '{}'
) returns table (
  id uuid,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
#variable_conflict use_column
begin
  return query
  select id, content, metadata, 1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where metadata @> filter
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;
```

### 2. Environment Variables

```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 3. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Frontend Setup

```bash
cd frontend
npm install
```

---

## Running the Application

Open **two terminals**:

**Terminal 1 — Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Then open **http://localhost:5173** in your browser.

---

## Tools & Fallbacks

### Tool 1: Web Search (`web_search`)
- **Primary:** [Tavily API](https://tavily.com)
- **Keyless Fallback:** DuckDuckGo Search / Wikipedia (triggers automatically if the Tavily API key is missing).
- **When activated:** The agent uses this tool for current events, news, recent facts, or internet data.

### Tool 2: Weather (`get_weather`)
- **Primary:** [OpenWeatherMap API](https://openweathermap.org/api)
- **Keyless Fallback:** [Open-Meteo](https://open-meteo.com) (triggers automatically if the OpenWeatherMap API key is missing).
- **When activated:** Real-time weather, temperature, rain, or climate queries.

### TTS (Text-to-Speech)
- **Primary:** [ElevenLabs](https://elevenlabs.io)
- **Fallback:** OpenAI TTS (used if ElevenLabs API key is missing).

---

## Persistent RAG Knowledge Base

This project uses a **permanent Supabase pgvector store** instead of volatile in-memory databases like FAISS.

When `RAG_SOURCE_URL` is set in the `.env` file, on backend startup:
1. It connects securely to your Supabase project using the `SUPABASE_SERVICE_KEY`.
2. It fetches and scrapes the provided URL content.
   - *SPA Metadata Support:* If the target page is a Single Page Application (like `https://www.ellibrototal.com/ltotal/`) where the HTML body is mostly empty JavaScript, the scraper automatically extracts the `<title>` and `<meta name="description">` to ensure no data is missed.
3. It splits the content into overlapping chunks.
4. Generates local embeddings using `sentence-transformers/all-MiniLM-L6-v2`.
5. Permanently saves the embeddings to the remote `documents` table in Supabase via LangChain's `SupabaseVectorStore`.

Before generating a response, the agent queries the Supabase database to retrieve the top relevant chunks and injects them as context, allowing it to accurately answer specific questions about the defined URL.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Claude API key |
| `TAVILY_API_KEY` | ⚠ optional | Web search tool (Falls back to DuckDuckGo if empty) |
| `OPENWEATHER_API_KEY` | ⚠ optional | Weather tool (Falls back to Open-Meteo if empty) |
| `ELEVENLABS_API_KEY` | ⚠ optional | Primary TTS (Falls back to OpenAI if empty) |
| `OPENAI_API_KEY` | ⚠ optional | Fallback TTS |
| `RAG_SOURCE_URL` | ⚠ optional | URL to scrape at startup (e.g. `https://www.ellibrototal.com/ltotal/`) |
| `SUPABASE_URL` | ⚠ optional | Project URL for persistent RAG |
| `SUPABASE_SERVICE_KEY` | ⚠ optional | Service Role Key for persistent RAG |

---

## Technical Decisions

- **Supabase pgvector:** Selected over FAISS or Chroma to provide persistent, production-ready cloud storage for embeddings without losing data on restarts.
- **SPA Metadata Extractor:** Added to bypass the client-side rendering limitations of traditional web scraping without needing a headless browser like Puppeteer.
- **FastAPI** over Flask/Django: async-native, fast cold starts.
- **LangChain** with `create_tool_calling_agent`: native tool use with Claude's function calling, clean memory integration.
- **ConversationBufferWindowMemory (k=7)**: sliding window keeps costs predictable while satisfying context requirements.
- **React + Vite**: fast dev loop, component isolation makes UI tool badges and custom audio players easy to swap.
