"""
main.py
-------
FastAPI backend exposing the HCP interaction agent to the frontend.

Flow per request:
  1. Frontend sends the rep's chat message + interaction_id.
  2. We load (or create) that interaction's state from Postgres.
  3. We append the user's message and run the LangGraph agent.
  4. We save the updated state back to Postgres and return it to the
     frontend, which re-renders the (read-only) form + shows the agent's
     chat reply.
"""

from dotenv import load_dotenv
load_dotenv()  # must run BEFORE importing graph/tools, which read GROQ_API_KEY at import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid

from state import new_interaction_state
from graph import hcp_agent
from db import init_db, save_interaction, load_interaction

app = FastAPI(title="HCP CRM Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Create the interactions table if it doesn't exist yet."""
    init_db()


class ChatRequest(BaseModel):
    interaction_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    interaction_id: str
    state: dict
    reply: str


@app.post("/interactions/new")
def create_interaction():
    """Start a brand new, blank interaction (called when rep opens the screen)."""
    interaction_id = str(uuid.uuid4())
    state = new_interaction_state(interaction_id)
    save_interaction(interaction_id, _serialize(state))
    return {"interaction_id": interaction_id, "state": _serialize(state)}


@app.post("/interactions/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Main endpoint the chat panel calls on every message."""
    interaction_id = req.interaction_id or str(uuid.uuid4())

    stored = load_interaction(interaction_id)
    state = stored if stored else new_interaction_state(interaction_id)

    # Chat history IS now persisted (as JSON-safe dicts, converted back to
    # real LangChain message objects here) -- previously this line always
    # rebuilt from an empty list every request, so the agent had zero
    # memory of prior turns even mid-conversation. agent_node's `[-6:]`
    # slice now actually limits a REAL growing history, as intended.
    prior_messages = _dicts_to_messages(state.get("messages", []))
    state["messages"] = prior_messages + [HumanMessage(content=req.message)]

    result_state = hcp_agent.invoke(state)

    serialized = _serialize(result_state)
    save_interaction(interaction_id, serialized)

    reply = result_state.get("last_agent_reply") or "Got it."

    return ChatResponse(
        interaction_id=interaction_id,
        state=serialized,
        reply=reply,
    )


@app.get("/interactions/{interaction_id}")
def get_interaction(interaction_id: str):
    """Fetch current form state (e.g. on page reload)."""
    state = load_interaction(interaction_id)
    if not state:
        return {"error": "not found"}
    return state

def _serialize(state: dict) -> dict:
    """Convert LangChain message objects into JSON-safe dicts (instead of
    dropping them) before persisting to Postgres / returning over the API,
    so conversation history survives across requests."""
    out = dict(state)
    if "messages" in out:
        out["messages"] = _messages_to_dicts(out["messages"])
    return out


def _messages_to_dicts(messages: list) -> list[dict]:
    """LangChain message objects -> JSON-safe dicts for storage."""
    out = []
    for m in messages:
        entry = {"type": m.type, "content": m.content}
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            entry["tool_calls"] = m.tool_calls
        if isinstance(m, ToolMessage):
            entry["tool_call_id"] = m.tool_call_id
        out.append(entry)
    return out


def _dicts_to_messages(dicts: list) -> list:
    """Stored dicts -> LangChain message objects, to feed back into the graph."""
    restored = []
    for d in dicts:
        if d["type"] == "human":
            restored.append(HumanMessage(content=d["content"]))
        elif d["type"] == "ai":
            restored.append(AIMessage(
                content=d["content"],
                tool_calls=d.get("tool_calls", []),
            ))
        elif d["type"] == "tool":
            restored.append(ToolMessage(
                content=d["content"],
                tool_call_id=d.get("tool_call_id", ""),
            ))
    return restored