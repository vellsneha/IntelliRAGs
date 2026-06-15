"""One-shot: parse the current Claude Code session JSONL and write it as
human-readable text. Skips internal-only records (thinking blocks, file
snapshots, permission-mode bookkeeping); preserves every user/assistant
text, tool call, and tool result verbatim."""

import json
from pathlib import Path

SESSION = Path(
    "/Users/myid/.claude/projects/"
    "-Users-myid-Documents-Projects-IntelliRAGs/"
    "a25d36fe-9ed5-4eb7-9b92-1ddada08c422.jsonl"
)
OUT = Path("/Users/myid/Documents/Projects/IntelliRAGs/claude_conversation.txt")


def render_block(b: dict) -> str:
    t = b.get("type")
    if t == "text":
        return b.get("text", "")
    if t == "tool_use":
        name = b.get("name", "?")
        inp = b.get("input", {})
        try:
            inp_str = json.dumps(inp, indent=2, ensure_ascii=False)
        except Exception:
            inp_str = repr(inp)
        return f"[TOOL CALL: {name}]\n{inp_str}"
    if t == "tool_result":
        content = b.get("content")
        if isinstance(content, list):
            parts = []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    parts.append(c.get("text", ""))
            body = "\n".join(parts)
        elif isinstance(content, str):
            body = content
        else:
            body = json.dumps(content, ensure_ascii=False)
        is_error = b.get("is_error")
        tag = "TOOL RESULT (ERROR)" if is_error else "TOOL RESULT"
        return f"[{tag}]\n{body}"
    if t == "thinking":
        return ""  # internal, not visible in terminal
    if t == "image":
        return "[image omitted]"
    return f"[unhandled block type: {t}]"


def render_message(role: str, content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        rendered = [render_block(b) for b in content if isinstance(b, dict)]
        rendered = [r for r in rendered if r]
        return "\n\n".join(rendered)
    return json.dumps(content, ensure_ascii=False)


with SESSION.open("r", encoding="utf-8") as f, OUT.open("w", encoding="utf-8") as out:
    out.write(f"# Claude Code session transcript\n# Source: {SESSION.name}\n\n")
    turn = 0
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        t = d.get("type")
        if t not in ("user", "assistant"):
            continue
        msg = d.get("message") or {}
        if not isinstance(msg, dict):
            continue
        role = msg.get("role") or t
        content = msg.get("content")
        body = render_message(role, content).strip()
        if not body:
            continue
        turn += 1
        out.write("=" * 70 + "\n")
        out.write(f"[{turn}] {role.upper()}\n")
        out.write("=" * 70 + "\n")
        out.write(body)
        out.write("\n\n")

print(f"Wrote {OUT}")
print(f"  size: {OUT.stat().st_size:,} bytes")
