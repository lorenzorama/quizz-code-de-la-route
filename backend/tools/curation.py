from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

_TS = re.compile(r"\[(\d+):(\d{2})\]")
_QUESTION = re.compile(r"question\s+(\d+)", re.IGNORECASE)
_BONNE = re.compile(r"bonne\s+r[eé]ponse", re.IGNORECASE)
_ANSWER_RUN = re.compile(
    r"\s*[,:]?\s*(?:r[eé]ponses?\s*)?([A-D](?:\s*(?:et|,|/)\s*[A-D])*)",
    re.IGNORECASE,
)


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
        run = _ANSWER_RUN.match(full, match.end())
        labels = (
            list(dict.fromkeys(re.findall(r"[A-D]", run.group(1).upper())))
            if run
            else []
        )
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


def frame_timestamp(filename: str) -> float:
    return float(os.path.splitext(os.path.basename(filename))[0])


def video_number(name: str) -> int:
    match = re.search(r"(\d+)\s*$", os.path.basename(name.rstrip("/")))
    if not match:
        raise ValueError(f"Cannot find a video number in {name!r}")
    return int(match.group(1))


def build_draft(video_dir: str) -> list[dict]:
    with open(os.path.join(video_dir, "transcript.txt"), encoding="utf-8") as fh:
        questions = parse_transcript(fh.read())

    frames = sorted(
        (f for f in os.listdir(video_dir) if f.endswith(".jpg")),
        key=frame_timestamp,
    )
    number = video_number(video_dir)

    entries = []
    for q in questions:
        candidates = [
            f for f in frames if q.display_start <= frame_timestamp(f) <= q.end_time
        ]
        entries.append(
            {
                "ref": f"v{number}q{q.index:02d}",
                "theme": "",
                "question_text": "",
                "options": {},
                "correct": q.correct,
                "explanation": q.explanation_raw,
                "frame": "",
                "crop": None,
                "candidate_frames": candidates,
                "window": [q.display_start, q.end_time],
            }
        )
    return entries


def draft(video_dir: str, out_path: str) -> None:
    if os.path.exists(out_path):
        raise FileExistsError(
            f"{out_path} already exists — refusing to overwrite curated data"
        )
    entries = build_draft(video_dir)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, ensure_ascii=False, indent=2)
