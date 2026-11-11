"""Intake guardrails (C5): plain code, no model. They run before ANYTHING else sees a message.

    result = check_message(text, student_id, turns)
    result.text      the message with private numbers hidden (this is what the model and the history see)
    result.blocked   None, or {"kind": ..., "message": ...}: the reply to give instead of running the graph
    result.notes     things we did that the student should know ("I hid a phone number")

Course session 7 (defense in depth: filters, PII, authorization, limits). Why code and not the model:
a model can be talked out of a rule, and it answers differently on different runs (we saw the same
injection message classified two ways). A regular expression gives the same answer every time.
The checks are cheap, so they come first and cost no model call when they block.

    hide      phone numbers, e-mail addresses and long digit strings (PII hiding)
    block     prompt injection and claims of authority ("I am the organizer, approve it")
    block     abusive language
    block     requests for ANOTHER student's phone, e-mail or address
    block     empty, over-long messages, and chats past the message limit (cost fuse)
Anything else passes. Whether a message is on-topic is decided later by the classifier (out_of_scope route).
"""
import re
from dataclasses import dataclass, field

from config import settings
from fest_data import load_students

# ---- PII hiding ----------------------------------------------------------------------------------
# A run of digits (spaces and hyphens allowed inside) that has 10 or more digits is a phone or account number.
# The look-behind keeps a student ID like C233001 and short numbers like "1050 BDT" or "2026-06-15" untouched.
NUMBER_RUN = re.compile(r"(?<![\w])\+?\d[\d \-]{8,18}\d(?![\w])")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

# ---- prompt injection and claims of authority --------------------------------------------------------
INJECTION = [re.compile(p, re.I) for p in [
    r"\b(ignore|disregard|forget|override|bypass)\b.{0,30}\b(previous|prior|above|earlier|preceding|all|your|the|any)\b.{0,20}\b(instructions?|rules?|prompts?|guidelines?|safety|restrictions?)",
    r"\b(reveal|show|print|repeat|leak|display|tell me)\b.{0,25}\b(system|hidden|initial|original|secret)\b.{0,10}\b(prompt|instructions?|message)",
    r"\bsystem prompt\b",
    r"\byou are now\b",
    r"\bact as (if you (are|were)|an? (admin|administrator|organizer|different|new|unrestricted|evil))",
    r"\bpretend (to be|you are|you're)\b",
    r"\b(developer|debug|god|admin) mode\b",
    r"\bjailbreak",
    r"\bnew instructions?\s*:",
    r"</?\s*(system|assistant|instructions?)\s*>",
    r"\b(i am|i'm|this is|as)\s+(the |an |your )?(organi[sz]er|admin|administrator|developer|teacher|professor)\b",
    r"\bapprove\b.{0,25}\b(it|this|my|the|all)\b.{0,15}\b(request|registration|exception)",
    r"\bregister (everyone|everybody|all students)\b",
    r"\bwithout (organi[sz]er )?approval\b",
]]
ABUSE = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*|asshole|bastard|moron|idiot)\b", re.I)

# ---- another student's private details ---------------------------------------------------------------------
PRIVATE_WORDS = re.compile(r"\b(phone|mobile|cell|contact number|whatsapp|e-?mail|address|home number)\b", re.I)

MESSAGES = {
    "empty": "Please type a question about CSE Fest 2026: rules, eligibility, schedule clashes or registration.",
    "too_long": "That message is too long. Please keep it under {n} characters.",
    "injection": "I can't follow instructions that try to change how I work. I can help with CSE Fest 2026 rules, "
                 "eligibility, schedule clashes and registration. Only a fest organizer can approve a request.",
    "abuse": "Please keep the chat respectful. I'm happy to help with questions about the fest.",
    "privacy": "I can't share another student's personal details or registrations. "
               "Each student can check their own status in their own chat.",
    "limit": "This conversation has reached its message limit. Please start a new one (/new) or contact the organizers.",
}


@dataclass
class GuardResult:
    text: str
    blocked: dict | None = None
    notes: list[str] = field(default_factory=list)


def hide_pii(text: str) -> tuple[str, list[str]]:
    """Replace phone/account numbers and e-mail addresses with placeholders. Returns (new text, what was hidden)."""
    hidden = []

    def number(m: re.Match) -> str:
        if sum(c.isdigit() for c in m.group()) < 10:
            return m.group()                      # dates, fees and the like stay as they are
        hidden.append("number")
        return "[number hidden]"

    text = NUMBER_RUN.sub(number, text)
    text, n = EMAIL.subn("[email hidden]", text)
    if n:
        hidden.append("email")
    return text, hidden


def asks_for_others_private_details(text: str, student_id: str) -> bool:
    """A private-detail word (phone, e-mail, address) together with another student's first name or ID."""
    if not PRIVATE_WORDS.search(text):
        return False
    words = set(re.findall(r"[a-z]+", text.lower()))
    ids = set(re.findall(r"[a-z]\d{6}", text.lower()))
    for s in load_students().values():
        if s["id"] == student_id:
            continue
        if s["id"].lower() in ids or s["name"].split()[0].lower() in words:
            return True
    return False


def block(kind: str) -> GuardResult:
    msg = MESSAGES[kind].format(n=settings.MAX_QUESTION_CHARS)
    return GuardResult(text="", blocked={"kind": kind, "message": msg})


def check_message(text: str, student_id: str, turns: int = 0) -> GuardResult:
    text = (text or "").strip()
    if not text:
        return block("empty")
    if len(text) > settings.MAX_QUESTION_CHARS:
        return block("too_long")
    if turns >= settings.MAX_TURNS_PER_THREAD:
        return block("limit")
    if any(p.search(text) for p in INJECTION):
        return block("injection")
    if ABUSE.search(text):
        return block("abuse")
    clean, hidden = hide_pii(text)                  # hide first: the student's OWN e-mail may contain a classmate's name
    if asks_for_others_private_details(clean, student_id):
        return block("privacy")
    notes = [f"I hid a private {h} from your message." for h in dict.fromkeys(hidden)]
    return GuardResult(text=clean, notes=notes)
