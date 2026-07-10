# AI-First CRM — HCP Log Interaction Module

An AI-first "Log Interaction" screen for pharma field reps. Instead of manually filling out a form, the rep simply **describes the interaction in natural language** in a chat panel, and a LangGraph agent — backed by a Groq-hosted LLM — extracts the details and populates the structured form automatically. The form itself is **read-only**; the only way to create or edit an interaction is through the AI assistant.

## Architecture

```
+---------------------+        +------------------------+        +-------------+
|   React + Redux UI   |  HTTP  |   FastAPI Backend       |        |  PostgreSQL |
|  +-------+ +-------+ |------->|                         |------->| interactions|
|  | Form  | | Chat  | |        |  LangGraph Agent        |        |   table     |
|  |(read- | | Panel | |<-------|  +------+   +-------+   |<-------|             |
|  | only) | |       | |        |  |agent |-->| tools |   |        +-------------+
|  +-------+ +-------+ |        |  +------+<--+-------+   |
+---------------------+        |        (Groq LLM)        |
                                 +------------------------+
```

**Flow per chat message:**
1. Rep types a message in the chat panel (e.g. "Met Dr. Sharma today, discussed OncoBoost, she was positive, shared 2 samples").
2. Frontend sends the message + `interaction_id` to `POST /interactions/chat`.
3. Backend loads (or creates) that interaction's state from Postgres.
4. The LangGraph agent reasons over the message, calling one or more of the 5 tools below.
5. Tool results are merged into the interaction's state (not just left in the chat log).
6. Updated state is saved back to Postgres and returned to the frontend.
7. The form re-renders with the new data; the chat panel shows the agent's reply.

## The 5 LangGraph Tools

| Tool | Purpose |
|---|---|
| **`log_interaction`** *(mandatory)* | Parses a fresh description and extracts HCP name, date/time, attendees, topics, sentiment, outcomes, and follow-ups -- populates the form in one shot. |
| **`edit_interaction`** *(mandatory)* | Patches a single field of an already-logged interaction (e.g. "actually change the sentiment to neutral"). |
| **`add_material_or_sample`** | Records marketing materials or drug samples shared with the HCP, appending to a running list. |
| **`suggest_followups`** | Generates 3 short, actionable next-step suggestions based on the topics discussed and observed sentiment. |
| **`summarize_voice_note`** | Condenses a rough/rambling voice-note transcript into a clean "Topics Discussed" summary. |

## Tech Stack

- **Frontend:** React + Redux, with a two-panel layout — a read-only interaction form on the left, and an AI chat assistant on the right.
- **Backend:** Python + FastAPI, exposing a small REST API that the frontend calls on every chat message.
- **AI Agent Framework:** LangGraph — implements a ReAct-style loop (`agent → tools → agent`) where an LLM decides which tool(s) to call based on the rep's message.
- **LLM:** Groq-hosted model.
- **Database:** PostgreSQL, accessed via SQLAlchemy (ORM layer) — one table (`interactions`) storing each interaction's full state as JSON.

## Model note

The assignment specifies `gemma2-9b-it`. As of now, on testing, this model no longer appears in Groq's list of available models (confirmed via `GET /openai/v1/models` against a live account) -- it has been deprecated/removed from the platform. The assignment document explicitly permits `llama-3.3-70b-versatile` as an alternative ("You may also consider llama-3.3-70b-versatile for context"), so that model is used as the primary/production model instead.

## Project Structure

```
HCP-Agent/
├── backend/
│   ├── .env.example        # Template for GROQ_API_KEY, DATABASE_URL
│   ├── db.py                # PostgreSQL persistence (save/load interaction
│   │                          state by interaction_id)
│   ├── graph.py              # LangGraph StateGraph wiring: agent node (LLM +
│   │                          tool binding) -> tools node -> END
│   ├── main.py                # FastAPI app; exposes /interactions/new,
│   │                          /interactions/chat, /interactions/{id}
│   ├── requirements.txt
│   ├── state.py               # InteractionState TypedDict (the form's shape)
│   │                          + reducers for merging concurrent tool writes
│   └── tools.py                # The 5 LangGraph tools the agent can call
│
├── frontend/
│   ├── public/
│   │   └── favicon.png
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js              # Axios/fetch wrapper for backend calls
│   │   ├── components/
│   │   │   ├── ChatPanel.jsx           # Chat interface for the rep
│   │   │   ├── InteractionForm.jsx     # Read-only form, renders agent state
│   │   │   ├── LogInteractionScreen.jsx # Top-level screen composing form + chat
│   │   │   └── LogInteractionScreen.css
│   │   ├── store/
│   │   │   ├── interactionSlice.js     # Redux state + async actions calling
│   │   │   │                             the FastAPI backend
│   │   │   └── store.js                # Redux store configuration
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── myenv/                   # Python virtual environment (not tracked in git)
├── .gitignore
└── README.md
```

## Setup & Running Locally
### Backend
```bash
cd backend
python -m venv myenv
myenv\Scripts\activate       # Windows
pip install -r requirements.txt
cp .env.example .env         # then fill in your GROQ_API_KEY and DATABASE_URL
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/interactions/new` | Starts a new, blank interaction. Returns an `interaction_id`. |
| `POST` | `/interactions/chat` | Sends a chat message; runs the LangGraph agent; returns updated state + agent reply. |
| `GET` | `/interactions/{interaction_id}` | Fetches the current state of an interaction (e.g. on page reload). |

## Demo Video
[link to your YouTube/Drive video once uploaded]
