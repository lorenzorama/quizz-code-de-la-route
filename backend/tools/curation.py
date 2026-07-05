from __future__ import annotations

import re
from dataclasses import dataclass

_TS = re.compile(r"\[(\d+):(\d{2})\]")
_QUESTION = re.compile(r"question\s+(\d+)", re.IGNORECASE)
_BONNE = re.compile(r"bonne\s+r[eé]ponse", re.IGNORECASE)
_LABEL = re.compile(r"\b([A-D])\b")


@dataclass
class ParsedQuestion:
    index: int
    correct: list[str]
    explanation_raw: str
    display_start: float
    end_time: float


def parse_transcript(text: str) -> list[ParsedQuestion]:
    """Segment a timestamped transcript into per-question data.

    Segmentation anchors on "Bonne réponse" markers (one per question, reliable)
    rather than the ASR-mislabeled "Question N" markers.
    """
    parts: list[str] = []
    char_time: list[float] = []
    for raw in text.splitlines():
        raw = raw.strip()
        m = _TS.match(raw)
        if not m:
            continue
        seconds = float(int(m.group(1)) * 60 + int(m.group(2)))
        content = raw[m.end():].strip() + " "
        parts.append(content)
        char_time.extend([seconds] * len(content))
    full = "".join(parts)
    if not full:
        return []

    answers: list[tuple[int, float, list[str]]] = []
    for match in _BONNE.finditer(full):
        tail = full[match.end(): match.end() + 60].split(".")[0]
        labels = list(dict.fromkeys(_LABEL.findall(tail.upper())))
        answers.append((match.start(), char_time[match.start()], labels))

    qmarks = [(q.start(), char_time[q.start()]) for q in _QUESTION.finditer(full)]

    questions: list[ParsedQuestion] = []
    prev_pos = 0
    prev_time = 0.0
    for k, (apos, atime, labels) in enumerate(answers):
        segment = full[prev_pos:apos].strip()
        display_start = prev_time
        for qpos, qtime in qmarks:
            if prev_pos <= qpos < apos:
                display_start = qtime
                break
        questions.append(
            ParsedQuestion(
                index=k + 1,
                correct=labels,
                explanation_raw=segment,
                display_start=display_start,
                end_time=atime,
            )
        )
        prev_pos = apos
        prev_time = atime
    return questions
