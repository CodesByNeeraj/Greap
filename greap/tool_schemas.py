"""OpenAI tool definitions the Greap Agent can call."""

from typing import Any

from greap.constants import CHOICE_BUY_REMAINING, CHOICE_CANCEL, CHOICE_EXTEND


def tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    """Build one function-tool definition in the Responses API's flat shape."""
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


STR = {"type": "string"}
INT = {"type": "integer"}
BOOL = {"type": "boolean"}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    tool(
        "save_profile",
        "Save onboarding details. Call with only the fields the user just gave. "
        "country must be a 2-letter ISO code such as SG.",
        {
            "name": STR,
            "addressLine1": STR,
            "city": STR,
            "postalCode": STR,
            "country": STR,
        },
        [],
    ),
    tool(
        "search_products",
        "Search Reap's catalog. Pass cursor from the previous result to see more.",
        {"query": STR, "cursor": STR},
        ["query"],
    ),
    tool(
        "join_queue",
        "Join the shared queue for a product from the latest search. First call "
        "with confirmed=false to get a preview, show it, and call again with "
        "confirmed=true only after the user says yes.",
        {"productId": STR, "units": INT, "confirmed": BOOL},
        ["productId", "units", "confirmed"],
    ),
    tool(
        "buy_carton",
        "Buy whole cartons directly at the carton price. Same two-step "
        "confirmed flag as join_queue.",
        {"productId": STR, "cartons": INT, "confirmed": BOOL},
        ["productId", "cartons", "confirmed"],
    ),
    tool("get_status", "Show the user's entries and queue progress.", {}, []),
    tool(
        "change_units",
        "Change units on a queued entry.",
        {"entryId": STR, "units": INT},
        ["entryId", "units"],
    ),
    tool("cancel_entry", "Cancel a queued entry.", {"entryId": STR}, ["entryId"]),
    tool(
        "resolve_short_queue",
        "Record the user's choice after a queue missed its deadline.",
        {
            "entryId": STR,
            "choice": {
                "type": "string",
                "enum": [CHOICE_BUY_REMAINING, CHOICE_EXTEND, CHOICE_CANCEL],
            },
        },
        ["entryId", "choice"],
    ),
    tool("get_past_purchases", "List the user's paid and ordered items.", {}, []),
    tool(
        "get_recommendations",
        "Suggest items from the user's purchase history. Call at the start of a "
        "new order.",
        {},
        [],
    ),
]
