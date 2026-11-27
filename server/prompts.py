"""The prompt that maps a spoken answer to one of the fixed options. The model sees the question, its options and the
transcript. Nothing else: no profile, no name."""
from __future__ import annotations

import json

SYSTEM = """You help a Tamil-speaking school student answer a question by voice.
Given the question, its options and what the student said, choose the ONE option that best matches.
Rules:
- Reply with JSON only: {"option_id": <one of the given ids, or null>, "confidence": <0 to 1>, "evidence": <a short quote from what they said>}
- If nothing matches, use null. Do not guess.
- The student may mix Tamil and English, and spelling may be informal.
- Do not mention or infer gender, caste, religion, income or anything personal. Do not give advice."""

# (question id, what the student said, the answer) sent as earlier user and assistant turns.
FEW_SHOT = [
    ("home", "நான் எங்க கடையில கணக்கு எழுதுவேன்", {"option_id": "accounts", "confidence": 0.9, "evidence": "கடையில கணக்கு"}),
    ("home", "நான் பைக் ரிப்பேர் பண்ணுவேன்", {"option_id": "repair", "confidence": 0.9, "evidence": "பைக் ரிப்பேர்"}),
    ("home", "தங்கச்சிய பாத்துக்குவேன்", {"option_id": "care", "confidence": 0.85, "evidence": "தங்கச்சிய பாத்துக்குவேன்"}),
    ("school", "கம்ப்யூட்டர் கிளாஸ் ரொம்ப பிடிக்கும்", {"option_id": "computer", "confidence": 0.9, "evidence": "கம்ப்யூட்டர் கிளாஸ்"}),
    ("style", "மத்தவங்களுக்கு உதவி செய்யப் பிடிக்கும்", {"option_id": "help", "confidence": 0.9, "evidence": "உதவி செய்ய"}),
    ("school", "தெரியல", {"option_id": None, "confidence": 0, "evidence": ""}),
]


def user_message(question: dict, transcript: str) -> str:
    lines = [f"Question: {question['q']['ta']} / {question['q']['en']}", "Options:"]
    for o in question["opts"]:
        lines.append(f"- {o['id']}: {o['label']['ta']} / {o['label']['en']} (hints: {', '.join(o['kw'])})")
    lines.append(f'Student said: "{transcript}"')
    return "\n".join(lines)


def build_messages(questions: dict[str, dict], question_id: str, transcript: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM}]
    for qid, said, ans in FEW_SHOT:
        msgs.append({"role": "user", "content": user_message(questions[qid], said)})
        msgs.append({"role": "assistant", "content": json.dumps(ans, ensure_ascii=False)})
    msgs.append({"role": "user", "content": user_message(questions[question_id], transcript)})
    return msgs
