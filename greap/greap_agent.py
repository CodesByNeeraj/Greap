"""Greap Agent: the conversational layer (an LLM with tool calling)."""

import json
from typing import Any

from openai import AsyncOpenAI

from greap.agent_prompt import buildSystemPrompt
from greap.constants import MAX_HISTORY_MESSAGES, MAX_TOOL_ROUNDS
from greap.context_store import ContextStore
from greap.tool_schemas import TOOL_SCHEMAS
from greap.toolbox import Toolbox

FALLBACK_REPLY = "Sorry, I got stuck on that. Could you rephrase?"


def trimHistory(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cap context size, cutting only at a user turn.

    Cutting mid tool-call would leave a tool result without its call, which
    the API rejects.
    """
    trimmed = history[-MAX_HISTORY_MESSAGES:]
    while trimmed and trimmed[0]["role"] != "user":
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


def assistantMessage(message: Any) -> dict[str, Any]:
    """Convert the SDK message back into the dict the API expects."""
    result: dict[str, Any] = {"role": "assistant", "content": message.content}
    if message.tool_calls:
        result["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls
        ]
    return result


class GreapAgent:
    """Keeps a short per-user conversation and runs the tool loop."""

    def __init__(
        self, llm: AsyncOpenAI, model: str, store: ContextStore, toolbox: Toolbox
    ) -> None:
        self.llm = llm
        self.model = model
        self.store = store
        self.toolbox = toolbox
        self.histories: dict[str, list[dict[str, Any]]] = {}

    async def handleMessage(self, telegramId: str, text: str) -> str:
        """Answer one user message, calling tools as the model asks."""
        history = self.histories.setdefault(telegramId, [])
        history.append({"role": "user", "content": text})
        for _ in range(MAX_TOOL_ROUNDS):
            system = buildSystemPrompt(self.store.getUser(telegramId))
            reply = await self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, *trimHistory(history)],
                tools=TOOL_SCHEMAS,
            )
            message = reply.choices[0].message
            history.append(assistantMessage(message))
            if not message.tool_calls:
                return removeRepeatedLines(message.content or FALLBACK_REPLY)
            await self.runToolCalls(telegramId, message.tool_calls, history)
        return FALLBACK_REPLY

    async def runToolCalls(self, telegramId: str, calls: list, history: list) -> None:
        """Execute each requested tool and feed the result back to the model."""
        for call in calls:
            result = await self.toolbox.run(
                telegramId,
                call.function.name,
                json.loads(call.function.arguments or "{}"),
            )
            history.append(
                {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)}
            )
