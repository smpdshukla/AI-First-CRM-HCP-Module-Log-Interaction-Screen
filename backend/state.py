from typing import TypedDict, List, Optional, Literal, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


def take_last(_current, new):
    """Reducer: if two tool calls somehow fire in the same step, just keep
    the latest write instead of crashing. Safety net alongside
    parallel_tool_calls=False in graph.py."""
    return new


def merge_materials(current: list, new: list) -> list:
    """Reducer: accumulate materials/samples across tool calls instead of
    overwriting. Needed because a single user message (e.g. "left 10
    samples and shared the PDF") can trigger add_material_or_sample
    TWICE in the same graph step -- each call returns its own new item,
    and both need to survive, not just the last one."""
    return (current or []) + (new or [])


class Material(TypedDict):
    name: str
    type: Literal["material", "sample"]
    quantity: Optional[int]


class InteractionState(TypedDict):
    interaction_id: Optional[str]
    hcp_name: Annotated[Optional[str], take_last]
    interaction_type: Annotated[Optional[str], take_last]
    date: Annotated[Optional[str], take_last]
    time: Annotated[Optional[str], take_last]
    attendees: Annotated[List[str], take_last]
    topics_discussed: Annotated[Optional[str], take_last]
    materials_shared: Annotated[List[Material], merge_materials]
    sentiment: Annotated[Optional[Literal["Positive", "Neutral", "Negative"]], take_last]
    outcomes: Annotated[Optional[str], take_last]
    follow_up_actions: Annotated[List[str], take_last]
    suggested_followups: List[str]
    voice_note_summary: Annotated[Optional[str], take_last]

    messages: Annotated[List[BaseMessage], add_messages]
    last_tool_called: Annotated[Optional[str], take_last]
    last_agent_reply: Annotated[Optional[str], take_last]


def new_interaction_state(interaction_id: str) -> InteractionState:
    """Factory for a blank interaction — used when a rep starts a new log entry."""
    return InteractionState(
        interaction_id=interaction_id,
        hcp_name=None,
        interaction_type=None,
        date=None,
        time=None,
        attendees=[],
        topics_discussed=None,
        materials_shared=[],
        sentiment=None,
        outcomes=None,
        follow_up_actions=[],
        suggested_followups=[],
        voice_note_summary=None,
        messages=[],
        last_tool_called=None,
        last_agent_reply=None,
    )
