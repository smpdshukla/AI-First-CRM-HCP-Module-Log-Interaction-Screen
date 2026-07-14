from typing import List, Optional, Annotated
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.tools.base import InjectedToolCallId
import os

_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.environ.get("GROQ_API_KEY"),
    temperature=0,
    max_tokens=200,
)


@tool
def log_interaction(
    hcp_name: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    interaction_type: str = "Meeting",
    date: Optional[str] = None,
    time: Optional[str] = None,
    attendees: Optional[str] = None,
    topics_discussed: Optional[str] = None,
    sentiment: Optional[str] = None,
    outcomes: Optional[str] = None,
    follow_up_actions: Optional[str] = None,
) -> Command:
    """Log a new HCP interaction. Call on first mention of a visit/call/email.
    Extract only what's stated; leave unmentioned fields empty.

    Args:
        hcp_name: HCP's name.
        interaction_type: Meeting, Call, or Email.
        date: ISO date YYYY-MM-DD.
        time: 24h HH:MM.
        attendees: Comma-separated list of other people present.
        topics_discussed: What was discussed.
        sentiment: Positive, Neutral, or Negative.
        outcomes: Key agreements/results.
        follow_up_actions: Comma-separated list of next steps.
    """
    def split_list(s):
        return [x.strip() for x in s.split(",") if x.strip()] if s else []

    populated = []
    if hcp_name: populated.append("HCP Name")
    if date: populated.append("Date")
    if sentiment: populated.append("Sentiment")
    if topics_discussed: populated.append("Topics Discussed")
    if outcomes: populated.append("Outcomes")

    fields_str = ", ".join(populated) if populated else "the details you provided"

    reply = (
        f"✅ **Interaction logged successfully!** The details ({fields_str}) "
        f"have been automatically populated based on your summary. "
        f"Would you like me to suggest a specific follow-up action, "
        f"such as scheduling a meeting?"
    )

    return Command(update={
        "hcp_name": hcp_name,
        "interaction_type": interaction_type,
        "date": date,
        "time": time,
        "attendees": split_list(attendees),
        "topics_discussed": topics_discussed,
        "sentiment": sentiment,
        "outcomes": outcomes,
        "follow_up_actions": split_list(follow_up_actions),
        "last_tool_called": "log_interaction",
        "last_agent_reply": reply,
        "messages": [ToolMessage(content=reply, tool_call_id=tool_call_id)],
    })


@tool
def edit_interaction(
    field: str,
    new_value: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Edit one field of the currently logged interaction (a correction/change).

    Args:
        field: One of hcp_name, interaction_type, date, time,
            topics_discussed, sentiment, outcomes.
        new_value: The corrected value.
    """
    allowed_fields = {
        "hcp_name", "interaction_type", "date", "time",
        "topics_discussed", "sentiment", "outcomes",
    }
    field_label = field.replace("_", " ").title()

    if field not in allowed_fields:
        reply = (
            f"⚠️ I couldn't update that — **{field_label}** isn't an editable "
            f"field. You can edit: HCP Name, Interaction Type, Date, Time, "
            f"Topics Discussed, Sentiment, or Outcomes."
        )
        return Command(update={
            "last_tool_called": "edit_interaction",
            "last_agent_reply": reply,
            "messages": [ToolMessage(content=reply, tool_call_id=tool_call_id)],
        })

    reply = (
        f"✅ **{field_label} updated successfully!** It's now set to "
        f"'{new_value}'. Let me know if anything else needs a correction."
    )
    return Command(update={
        field: new_value,
        "last_tool_called": "edit_interaction",
        "last_agent_reply": reply,
        "messages": [ToolMessage(content=reply, tool_call_id=tool_call_id)],
    })


@tool
def add_material_or_sample(
    name: str,
    item_type: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[dict, InjectedState],
    quantity: Optional[str] = None,
) -> Command:
    """Record a material (brochure/PDF) or sample shared with the HCP.

    Args:
        name: Name of the material or sample.
        item_type: "material" or "sample".
        quantity: Number of samples left, if any (as a plain number, e.g. "10").
    """
    parsed_quantity = None
    if quantity is not None:
        try:
            parsed_quantity = int(quantity)
        except (ValueError, TypeError):
            parsed_quantity = None

    new_item = {"name": name, "type": item_type, "quantity": parsed_quantity}
    existing = state.get("materials_shared", [])

    label = "material" if item_type == "material" else "sample"
    qty_str = f" ({parsed_quantity} units)" if parsed_quantity else ""

    reply = (
        f"✅ **{label.title()} added successfully!** '{name}'{qty_str} has "
        f"been recorded as shared with the HCP. Want to log anything else "
        f"that was handed over during the visit?"
    )

    return Command(update={
        "materials_shared": existing + [new_item],
        "last_tool_called": "add_material_or_sample",
        "last_agent_reply": reply,
        "messages": [ToolMessage(content=reply, tool_call_id=tool_call_id)],
    })


@tool
def suggest_followups(
    topics_discussed: str,
    sentiment: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Suggest 3 follow-up actions once topics + sentiment are known.

    Args:
        topics_discussed: What was discussed.
        sentiment: The HCP's observed sentiment.
    """
    prompt = (
        f"You are a pharma sales assistant. Based on this HCP interaction, "
        f"suggest exactly 3 short, actionable follow-up steps.\n\n"
        f"Topics discussed: {topics_discussed}\n"
        f"HCP sentiment: {sentiment}\n\n"
        f"Return ONLY a numbered list of 3 short suggestions, nothing else."
    )
    response = _llm.invoke(prompt)
    suggestions = [
        line.strip("0123456789. ").strip()
        for line in response.content.strip().split("\n")
        if line.strip()
    ][:3]

    suggestions_str = "\n".join(f"{i+1}. {s}" for i, s in enumerate(suggestions))
    reply = (
        f"✅ **Here are some suggested follow-ups!**\n\n{suggestions_str}\n\n"
        f"Would you like me to add any of these to Follow-Up Actions?"
    )

    return Command(update={
        "suggested_followups": suggestions,
        "last_tool_called": "suggest_followups",
        "last_agent_reply": reply,
        "messages": [ToolMessage(content=reply, tool_call_id=tool_call_id)],
    })


@tool
def summarize_voice_note(
    raw_transcript: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Clean up a rambling voice-note transcript into the Topics Discussed field.

    Args:
        raw_transcript: The raw, unedited transcript text.
    """
    prompt = (
        "Summarize this field rep's voice note into 2-3 concise sentences "
        "suitable for a CRM 'Topics Discussed' field. Keep only concrete, "
        "relevant details (drugs, studies, HCP reactions, upcoming events "
        "mentioned).\n\n"
        "Respond with ONLY the summary text itself -- no preamble, no "
        "introduction like 'Here is a summary', no quotation marks, "
        "just the 2-3 sentences directly.\n\n"
        f"Transcript: {raw_transcript}"
    )
    response = _llm.invoke(prompt)
    summary = response.content.strip()

    # Safety strip in case the model still adds a preamble despite instructions
    for prefix in [
        "here is a summary of the voice note in 2-3 concise sentences:",
        "here is a summary of the voice note:",
        "here is a 2-3 sentence summary:",
        "summary:",
    ]:
        if summary.lower().startswith(prefix):
            summary = summary[len(prefix):].strip()
            break

    reply = (
        f"✅ **Voice note summarized successfully!** Topics Discussed has "
        f"been updated with:\n\n\"{summary}\"\n\n"
        f"Does that capture it accurately, or would you like me to adjust it?"
    )

    return Command(update={
        "voice_note_summary": summary,
        "last_tool_called": "summarize_voice_note",
        "last_agent_reply": reply,
        "messages": [ToolMessage(content=reply, tool_call_id=tool_call_id)],
    })


ALL_TOOLS = [
    log_interaction,
    edit_interaction,
    add_material_or_sample,
    suggest_followups,
    summarize_voice_note,
]
