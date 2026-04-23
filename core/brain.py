"""
JARVIS Brain — Claude API integration with tool use and memory context.
All skill calls are dispatched via Claude's tool_use feature so JARVIS
decides on its own which action to take based on natural language.
"""
import json
import anthropic
from core import memory as mem
from config.settings import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """\
You are JARVIS, a highly intelligent personal AI assistant running on your user's local machine.
You are helpful, precise, and slightly formal — like the original JARVIS from Iron Man.

CRITICAL RULES:
- You ONLY act when the user gives you an explicit command or question. Never take initiative.
- Never perform actions, send notifications, or do anything unless the user directly asks you to.
- You are a command-driven assistant: receive command → execute → report result. Nothing more.
- Do not suggest follow-up actions unless asked.
- Respond concisely. After a tool call, give a brief one-line confirmation.

You have access to:
- The user's conversation history and learned preferences
- Computer control tools (open apps, search, system info)
- Memory: ability to save facts the user asks you to remember

User memories and preferences:
{memory_context}

Connected devices: {device_list}
"""

# ─── Tool definitions (Claude calls these to control the PC) ─────────────────

TOOLS = [
    {
        "name": "open_application",
        "description": "Open an application on the user's Windows PC by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Application name, e.g. 'notepad', 'chrome', 'spotify'"}
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "web_search",
        "description": "Open the default browser and search for a query on Google.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "save_memory",
        "description": "Save a fact or preference about the user for future reference.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Category: preference / fact / task / reminder"},
                "fact": {"type": "string", "description": "The fact to remember"},
            },
            "required": ["category", "fact"],
        },
    },
    {
        "name": "get_system_info",
        "description": "Retrieve basic system information (time, battery, running processes).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


# ─── Tool dispatcher ──────────────────────────────────────────────────────────

async def _dispatch_tool(name: str, inputs: dict) -> str:
    from skills.computer_control import open_application, web_search, get_system_info

    if name == "open_application":
        return await open_application(inputs["app_name"])
    if name == "web_search":
        return await web_search(inputs["query"])
    if name == "save_memory":
        await mem.save_memory(inputs["category"], inputs["fact"])
        return f"Saved: [{inputs['category']}] {inputs['fact']}"
    if name == "get_system_info":
        return await get_system_info()
    return f"Unknown tool: {name}"


# ─── Main think() function ────────────────────────────────────────────────────

async def think(user_input: str, device_id: str = "pc") -> str:
    """Process user input through Claude and return JARVIS's response."""
    await mem.save_message("user", user_input, device_id)

    history = await mem.get_recent_conversation(limit=20)
    memory_ctx = await mem.format_memory_context()
    devices = await mem.get_active_devices()
    device_list = ", ".join(d["name"] for d in devices) or "PC only"

    system = SYSTEM_PROMPT.format(memory_context=memory_ctx, device_list=device_list)

    messages = [{"role": m["role"], "content": m["content"]} for m in history]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        tools=TOOLS,
        messages=messages,
    )

    # Handle tool use in a loop until Claude gives a final text response
    while response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = await _dispatch_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

    reply = next(
        (block.text for block in response.content if hasattr(block, "text")),
        "I'm sorry, I didn't catch that.",
    )

    await mem.save_message("assistant", reply, device_id)
    return reply
