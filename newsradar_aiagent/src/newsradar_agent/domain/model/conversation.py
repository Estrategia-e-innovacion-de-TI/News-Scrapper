"""Conversation state model.

Tracks the multi-turn conversation between user and agent,
including message history, detected intents, and pending actions.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Role(str, Enum):
    """Message role in the conversation."""

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    """A single message in the conversation.

    Attributes
    ----------
    role : Role
        Who sent the message.
    content : str
        Message text content.
    metadata : dict
        Optional metadata (e.g., tool call results, intent info).
    """

    role: Role
    content: str
    metadata: dict = Field(default_factory=dict)


class ConversationState(BaseModel):
    """State of an ongoing conversation.

    Attributes
    ----------
    conversation_id : str
        Unique identifier for this conversation.
    messages : list[Message]
        Ordered list of messages in the conversation.
    current_intent : Any | None
        The most recently detected intent.
    pending_tool_call : str | None
        MCP tool name pending execution, if any.
    context : dict
        Accumulated context from the conversation (company, NIT, terms, etc.).
    turn_count : int
        Number of user turns in this conversation.
    """

    conversation_id: str = ""
    messages: list[Message] = Field(default_factory=list)
    current_intent: Any | None = None
    pending_tool_call: str | None = None
    context: dict = Field(default_factory=dict)
    turn_count: int = 0
