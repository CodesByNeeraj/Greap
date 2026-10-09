"""Greap Agent: the conversational layer (an LLM with tool calling).

Uses OpenAI's Responses API, because the gpt-6 models do not allow function
tools with reasoning on the older Chat Completions endpoint.
"""

import json
from typing import Any

from openai import AsyncOpenAI

from greap.agent_prompt import buildSystemPrompt
from greap.constants import AGENT_REASONING_EFFORT, MAX_HISTORY_MESSAGES
from greap.constants import MAX_TOOL_ROUNDS
from greap.context_store import ContextStore
from greap.tool_schemas import TOOL_SCHEMAS
from greap.toolbox import Toolbox

FALLBACK_REPLY = "Sorry, I got stuck on that. Could you rephrase?"


def isUserMessage(item: Any) -> bool:
    """Only our own user messages are plain dicts; model output items are objects."""
    return isinstance(item, dict) and item.get("role") == "user"


def trimHistory(history: list[Any]) -> list[Any]:
    """Cap context size, cutting only at a user turn.

    Cutting mid tool-call would leave a tool result without its call, which
    the API rejects.
    """
    trimmed = history[-MAX_HISTORY_MESSAGES:]
    while trimmed and not isUserMessage(trimmed[0]):
        trimmed = trimmed[1:]
    return trimmed


def removeRepeatedLines(text: str) -> str:
    """Drop a line that repeats the one right before it.

    The model sometimes says the same sentence twice in one reply. Product lists
    are unaffected because no two of their lines are identical.
    """
    kept: list[str] = []
    for line in text.split("\n"):
        if line.strip() and kept and kept[-1].strip() == line.strip():
            continue
        kept.append(line)
    return "\n".join(kept)


class GreapAgent:
    """Keeps a short per-user conversation and runs the tool loop."""

    def __init__(
        self, llm: AsyncOpenAI, model: str, store: ContextStore, toolbox: Toolbox
    ) -> None:
        self.llm = llm
        self.model = model
        self.store = store
        self.toolbox = toolbox
        self.histories: dict[str, list[Any]] = {}

    async def handleMessage(self, telegramId: str, text: str) -> str:
        """Answer one user message, calling tools as the model asks."""
        history = self.histories.setdefault(telegramId, [])
        history.append({"role": "user", "content": text})
        for _ in range(MAX_TOOL_ROUNDS):
            reply = await self.llm.responses.create(
                model=self.model,
                instructions=buildSystemPrompt(self.store.getUser(telegramId)),
                input=trimHistory(history),
                tools=TOOL_SCHEMAS,
                reasoning={"effort": AGENT_REASONING_EFFORT},
            )
            # Output items (including reasoning) go back in so tool turns stay valid.
            history.extend(reply.output)
            calls = [item for item in reply.output if item.type == "function_call"]
            if not calls:
                return removeRepeatedLines(reply.output_text or FALLBACK_REPLY)
            await self.runToolCalls(telegramId, calls, history)
        return FALLBACK_REPLY

    async def runToolCalls(self, telegramId: str, calls: list, history: list) -> None:
        """Execute each requested tool and feed the result back to the model."""
        for call in calls:
            result = await self.toolbox.run(
                telegramId, call.name, json.loads(call.arguments or "{}")
            )
            history.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result),
                }
            )
