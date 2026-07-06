from __future__ import annotations

import argparse
import glob
import json
import os
import re
from dataclasses import dataclass

from openpyxl import Workbook
from PIL import Image

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


# Situation photo sits above the yellow divider (~y=632) for this producer's
# 1920x1080 template. Tune per video after viewing frames if needed.
# Same 1920x1080 producer template across every video so far: the situation
# photo sits above the yellow divider (~y=632). A video that needs a different
# crop can override it per-entry via the JSON "crop" field (checked first in
# build()). Videos beyond this range still fail loudly until added here.
DEFAULT_CROPS: dict[int, tuple[int, int, int, int]] = {
    n: (0, 0, 1920, 632) for n in range(1, 59)
}


def crop_frame(
    frame_path: str, box: tuple[int, int, int, int], out_path: str
) -> None:
    x, y, w, h = box
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with Image.open(frame_path) as img:
        img.crop((x, y, x + w, y + h)).save(out_path)


_XLSX_COLUMNS = [
    "ref", "theme", "question_text",
    "option_a", "option_b", "option_c", "option_d",
    "correct", "explanation", "media_path", "media_type",
]
_VALID_LABELS = ["A", "B", "C", "D"]


def validate_entry(entry: dict) -> None:
    ref = entry.get("ref") or "<no ref>"
    if not entry.get("question_text"):
        raise ValueError(f"{ref}: empty question_text")
    options = entry.get("options") or {}
    if len(options) < 2:
        raise ValueError(f"{ref}: needs at least 2 options")
    correct = entry.get("correct") or []
    if not correct:
        raise ValueError(f"{ref}: no correct answer")
    orphan = [c for c in correct if c not in options]
    if orphan:
        raise ValueError(f"{ref}: correct label(s) {orphan} have no option")
    if not entry.get("frame"):
        raise ValueError(f"{ref}: no frame chosen")


def build(
    curation_dir: str, frames_root: str, media_root: str, xlsx_path: str
) -> int:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "questions"
    sheet.append(_XLSX_COLUMNS)

    count = 0
    for path in sorted(glob.glob(os.path.join(curation_dir, "video_*.json"))):
        number = video_number(os.path.splitext(os.path.basename(path))[0])
        folder = f"video_{number}"
        with open(path, encoding="utf-8") as fh:
            entries = json.load(fh)
        for entry in entries:
            validate_entry(entry)
            frame_path = os.path.join(frames_root, folder, entry["frame"])
            if not os.path.exists(frame_path):
                raise ValueError(f"{entry['ref']}: frame not found at {frame_path}")
            if entry.get("crop"):
                box = tuple(entry["crop"])
            elif number in DEFAULT_CROPS:
                box = DEFAULT_CROPS[number]
            else:
                raise ValueError(
                    f"{entry['ref']}: no crop for video_{number} — add it to "
                    f"DEFAULT_CROPS or set the entry's \"crop\""
                )
            media_rel = f"{folder}/{entry['ref']}.jpg"
            crop_frame(frame_path, box, os.path.join(media_root, media_rel))

            options = entry["options"]
            sheet.append([
                entry["ref"],
                entry.get("theme", ""),
                entry["question_text"],
                options.get("A", ""),
                options.get("B", ""),
                options.get("C", ""),
                options.get("D", ""),
                ",".join(entry["correct"]),
                entry.get("explanation", ""),
                media_rel,
                "image",
            ])
            count += 1

    os.makedirs(os.path.dirname(xlsx_path) or ".", exist_ok=True)
    workbook.save(xlsx_path)
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="curation")
    sub = parser.add_subparsers(dest="command", required=True)

    p_draft = sub.add_parser("draft")
    p_draft.add_argument("video_dir")
    p_draft.add_argument("out_path")

    p_build = sub.add_parser("build")
    p_build.add_argument("--curation-dir", default="backend/data/curation")
    p_build.add_argument("--frames-root", default="sources_data")
    p_build.add_argument("--media-root", default="backend/media")
    p_build.add_argument("--xlsx-path", default="backend/data/questions.xlsx")

    args = parser.parse_args(argv)
    if args.command == "draft":
        draft(args.video_dir, args.out_path)
        print(f"Wrote draft to {args.out_path}")
    else:
        n = build(args.curation_dir, args.frames_root, args.media_root, args.xlsx_path)
        print(f"Built {n} questions into {args.xlsx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
