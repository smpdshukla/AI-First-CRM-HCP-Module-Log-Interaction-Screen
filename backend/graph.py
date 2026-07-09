"""
graph.py
--------
Wires together the LangGraph agent:

    START -> agent (LLM decides which tool(s) to call, or replies directly)
          -> tools (executes the tool, merges result + last_agent_reply into state)
          -> END
    (if no tool call was needed: agent -> END directly)

Note: this intentionally does NOT loop back from tools -> agent. Each tool
already sets its own "last_agent_reply" (e.g. "Logged interaction with Dr.
Sharma."), so a second LLM call here would only reword something already
said -- at the cost of a full extra tool-schema-laden call per turn. See
the comment above graph.add_edge("tools", END) below.
"""

import os
import time
from typing import Annotated
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from groq import BadRequestError

load_dotenv()  # reads GROQ_API_KEY (and DATABASE_URL) from your .env file

from state import InteractionState
from tools import ALL_TOOLS

# --- LLM setup ---------------------------------------------------------
# NOTE: The assignment specifies "gemma2-9b-it", but this model has been
# deprecated / removed from Groq's platform (confirmed via GET
# /openai/v1/models against a live account on 2026-07-08 -- it no longer
# appears in the list of models available to a fresh Groq account). The
# assignment doc explicitly permits "llama-3.3-70b-versatile" as an
# alternative ("You may also consider llama-3.3-70b-versatile for
# context"), so that's used here.
#
# This model has a 100,000 tokens/day free-tier cap, which is easy to
# exhaust during iterative development since every call re-sends the
# full system prompt + all 5 tool schemas + recent chat history. Two
# mitigations below: a trimmed system prompt, and capping history to
# the last 6 messages instead of the full growing conversation.
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.environ.get("GROQ_API_KEY"),
    temperature=0,
)
llm_with_tools = llm.bind_tools(ALL_TOOLS) 

SYSTEM_PROMPT = SystemMessage(content=(
    "You are the CRM assistant for a pharma field rep. You control the "
    "interaction form entirely via tool calls -- never ask the user to "
    "fill it manually.\n"
    "Tool routing rules:\n"
    "- log_interaction: first mention of a visit/call/email with an HCP. "
    "Extract only what's stated (name, sentiment, topics, outcomes); "
    "don't guess unmentioned fields.\n"
    "- edit_interaction: rep corrects/changes something already logged.\n"
    "- add_material_or_sample: rep mentions sharing a brochure/PDF/"
    "leave-behind, or leaving physical samples.\n"
    "- suggest_followups: once topics + sentiment are both known.\n"
    "- summarize_voice_note: rep gives a raw/rambling dictated transcript.\n"
    "After a tool runs, do NOT repeat its result in your own words -- the "
    "tool's own message to the user is shown directly. Only reply directly "
    "(no tool call) when the rep is just asking a question."
))


def agent_node(state: InteractionState) -> dict:
    """The reasoning step: LLM looks at recent message history + decides
    tool calls.

    Occasionally Groq's tool-calling models mis-format a function call --
    a known intermittent quirk, not a logic bug. We retry a couple of
    times with a short delay. If it still can't produce a valid tool call
    after all attempts, we fall back to a plain text reply instead of
    crashing the whole request -- the user can just repeat/rephrase.

    Only the last 6 messages are sent, not the full history, to keep
    each call's token cost from growing unbounded as a conversation
    goes on -- this matters a lot given the free-tier daily token cap.
    """
    from langchain_core.messages import AIMessage

    messages = [SYSTEM_PROMPT] + state["messages"][-6:]

    last_error = None
    for attempt in range(3):  # original + 2 retries
        try:
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}
        except Exception as e:
            last_error = e
            print(f"[agent_node] {type(e).__name__} attempt {attempt}: {e}", flush=True)
            time.sleep(1.5)
            continue

    # All attempts failed to format a valid tool call -- degrade gracefully
    # instead of returning a 500 error to the frontend.
    fallback = AIMessage(
        content=(
            "I had trouble processing that just now -- could you try "
            "rephrasing, or send it again?"
        )
    )
    return {
        "messages": [fallback],
        "last_agent_reply": (
            "I had trouble processing that just now -- please try again."
        ),
    }


def merge_materials_reducer(state: InteractionState, tool_output: dict) -> dict:
    """Special-case merge so add_material_or_sample APPENDS instead of overwriting."""
    if "materials_shared" in tool_output:
        existing = state.get("materials_shared", [])
        tool_output["materials_shared"] = existing + tool_output["materials_shared"]
    return tool_output


def build_graph():
    graph = StateGraph(InteractionState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    graph.set_entry_point("agent")

    # If the LLM's last message requested a tool call -> go to tools,
    # otherwise -> end the turn (just a plain reply, no action needed).
    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: END},
    )
    # After running tools, go straight to END instead of back to the
    # agent. Each tool already writes its own "last_agent_reply" (e.g.
    # "Logged interaction with Dr. Sharma."), so looping back to the LLM
    # here would just spend a second full LLM call (system prompt + all
    # 5 tool schemas again) to have it reword something already said --
    # pure token waste against the daily cap. The FastAPI endpoint should
    # return state["last_agent_reply"] to the chat panel.
    graph.add_edge("tools", END)

    return graph.compile()


# Compiled, ready-to-invoke graph
hcp_agent = build_graph()