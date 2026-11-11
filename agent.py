"""The tool loop (C3): the model asks for tools, the code runs them, the results go back, repeat.

Course session 5 ("the loop by hand"). Four things make it safe and easy to explain:
  - the model only sees the READ tools, bound to the asking student (tools.make_tools);
  - a tool that fails returns {"error": ...} to the model instead of crashing the run;
  - a fuse: at most settings.MAX_TOOL_STEPS model calls, then the loop stops (cost and runaway limit);
  - every call and result is kept in a log, which is what the explain_result and draft_request nodes read.
"""
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from config import settings
from models import build_model, load_prompt
from tools import make_tools


CAPS = {"search_rules": 1}        # one rule search per message is enough, and every call costs quota


def run_tools(question: str, student_id: str, mode: str, events: list[str]) -> list[dict]:
    """Run the tool loop for one message. Returns the log: [{"tool", "args", "result"}, ...]."""
    tools = make_tools(student_id)
    by_name = {t.name: t for t in tools}
    model = build_model(tools=tools)
    template, version = load_prompt("agent_prompt")
    messages = [SystemMessage(template.format(student_id=student_id, mode=mode, events=events or "none found")),
                HumanMessage(question)]
    config = {"run_name": "tool_loop", "tags": [f"prompt:agent_prompt:{version}"]}
    log, seen = [], set()

    for step in range(settings.MAX_TOOL_STEPS):
        ai: AIMessage = model.invoke(messages, config=config)
        messages.append(ai)
        if not ai.tool_calls:                       # the model says it is done
            return log
        for call in ai.tool_calls:
            key = (call["name"], json.dumps(call["args"], sort_keys=True))
            if call["name"] in CAPS and sum(e["tool"] == call["name"] for e in log) >= CAPS[call["name"]]:
                result = {"error": f"{call['name']} may be used at most {CAPS[call['name']]} time(s) per message"}
            elif key in seen:                         # the same call twice is a loop: answer it, do not run it again
                result = {"error": "you already made this exact call"}
            elif call["name"] not in by_name:
                result = {"error": f"no such tool: {call['name']}"}
            else:
                try:
                    result = json.loads(by_name[call["name"]].invoke(call["args"]))
                except Exception as err:            # a tool error goes back to the model as data
                    result = {"error": str(err)[:200]}
            seen.add(key)
            log.append({"tool": call["name"], "args": call["args"], "result": result})
            messages.append(ToolMessage(json.dumps(result, default=str), tool_call_id=call["id"], name=call["name"]))
    log.append({"tool": "(fuse)", "args": {}, "result": {"error": f"stopped after {settings.MAX_TOOL_STEPS} steps"}})
    return log
