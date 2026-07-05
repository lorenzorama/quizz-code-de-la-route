# Question-Content Tooling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the tooling that turns driving-code video transcripts + frames into curated questions: a transcript parser, a "draft curation" seeder, a frame cropper, and a builder that regenerates `questions.xlsx` from curation files.

**Architecture:** A single tested module `backend/tools/curation.py`. `parse_transcript` (pure) segments a transcript by "Bonne réponse" markers (reliable) into per-question data. `draft` seeds a `curation/video_N.json` for the human curator (correct answer + raw explanation + candidate frames). `crop_frame` (Pillow) cuts the situation photo above the divider. `build` validates all curation files, crops chosen frames into `backend/media/`, and regenerates `backend/data/questions.xlsx` (which the existing import CLI consumes). This plan builds the tooling only; curating the two videos is a separate collaborative step.

**Tech Stack:** Python 3.12, Pillow (new), openpyxl (existing), pytest. Runs from the repo root; tests run from `backend/` (`pythonpath = .`).

## Global Constraints

- New module lives at `backend/tools/curation.py` (package `tools`, importable as `tools.curation` when pytest runs from `backend/`). Add `backend/tools/__init__.py`.
- New dependency **Pillow** added to `backend/requirements.txt`, installed with `uv pip install` in the existing `.venv` (Python 3.12 via `uv`).
- `ref` scheme: `v<videoNumber>q<NN>` by question ordinal (e.g. `v1q02`) — NOT the transcript's stated number (ASR mislabels it). Import is idempotent by `ref`.
- Correct answers stored as a list of labels; written to xlsx as comma-joined (e.g. `"A,D"`).
- Generated `questions.xlsx` columns exactly: `ref, theme, question_text, option_a, option_b, option_c, option_d, correct, explanation, media_path, media_type`. `media_path = "video_N/<ref>.jpg"`, `media_type = "image"`.
- Default crop per video: `(x, y, w, h)` in `DEFAULT_CROPS` (full width above the yellow divider). A curation entry may override with its own `crop`.
- Build fails loudly (raises `ValueError` naming the `ref`) on a bad entry; never emits a broken row.
- Run backend commands from `backend/` with the venv active; tool commands from the repo root.
- Every task ends with a passing test run and a commit.

---

### Task 1: `parse_transcript` + module scaffold + Pillow

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/tools/__init__.py`
- Create: `backend/tools/curation.py`
- Create: `backend/tests/test_curation.py`

**Interfaces:**
- Produces:
  - `@dataclass ParsedQuestion(index: int, correct: list[str], explanation_raw: str, display_start: float, end_time: float)`.
  - `parse_transcript(text: str) -> list[ParsedQuestion]` — segments by "Bonne réponse" markers; `display_start` = time of the first "question N" marker inside the segment (else segment start); `end_time` = the "Bonne réponse" time; `correct` = labels after that marker.

- [ ] **Step 1: Add Pillow to `backend/requirements.txt`**

Append this line:

```
pillow==11.*
```

- [ ] **Step 2: Install it**

Run (from `backend/`): `. .venv/bin/activate && uv pip install -r requirements.txt`
Expected: Pillow installs without error.

- [ ] **Step 3: Create `backend/tools/__init__.py`** (empty file).

- [ ] **Step 4: Create `backend/tools/curation.py` (parser portion)**

```python
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
```

- [ ] **Step 5: Write the failing tests — `backend/tests/test_curation.py`**

```python
from tools.curation import parse_transcript

SINGLE = """[0:15] Question 1.
[0:19] maintenir la vitesse, réponse A, bloquer, réponse B.
[0:55] Retenez le principe. Bonne réponse, réponse A.
[0:57] Question 2.
[1:04] je ralentis, réponse A, je klaxonne, réponse B.
[1:31] Le cycliste vous a vu. Bonne réponse A.
"""

MULTI = """[3:00] Question 4.
[3:03] piste, réponse A, bande, réponse B, oui, réponse C, non, réponse D.
[3:06] Explication. Bonne réponse B et C.
"""

INLINE = """[0:30] Le frein est au milieu.
[0:47] Retenez la position. Bonne réponse, B, question 2.
[0:50] priorité, oui, réponse A, non, réponse B.
[1:33] Priorité à droite. Bonne réponse A et D, question 3.
"""


def test_segments_two_questions_with_display_start_and_end():
    qs = parse_transcript(SINGLE)
    assert len(qs) == 2
    assert qs[0].index == 1
    assert qs[0].correct == ["A"]
    assert qs[0].display_start == 15.0
    assert qs[0].end_time == 55.0
    assert qs[1].correct == ["A"]
    assert qs[1].display_start == 57.0
    assert qs[1].end_time == 91.0


def test_multi_answer():
    qs = parse_transcript(MULTI)
    assert len(qs) == 1
    assert qs[0].correct == ["B", "C"]


def test_inline_question_markers_and_multi():
    qs = parse_transcript(INLINE)
    assert len(qs) == 2
    assert qs[0].correct == ["B"]
    assert qs[1].correct == ["A", "D"]


def test_empty_transcript():
    assert parse_transcript("") == []
```

- [ ] **Step 6: Run the tests**

Run (from `backend/`, venv active): `pytest tests/test_curation.py -v`
Expected: 4 tests PASS. (Pure — no DB needed.)

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/tools/__init__.py backend/tools/curation.py backend/tests/test_curation.py
git commit -m "feat(tools): add transcript parser for question curation"
```

---

### Task 2: `draft` — seed a curation file

**Files:**
- Modify: `backend/tools/curation.py`
- Modify: `backend/tests/test_curation.py`

**Interfaces:**
- Consumes: `parse_transcript` (Task 1).
- Produces:
  - `frame_timestamp(filename: str) -> float` (e.g. `"78.0.jpg" -> 78.0`).
  - `video_number(name: str) -> int` (e.g. `"video_1" -> 1`).
  - `build_draft(video_dir: str) -> list[dict]` — returns the draft entries (pure, testable).
  - `draft(video_dir: str, out_path: str) -> None` — writes the draft JSON (refuses to overwrite an existing file).

- [ ] **Step 1: Add imports + helpers + draft to `backend/tools/curation.py`**

Add these imports at the top (below `import re`):

```python
import json
import os
```

Append to the file:

```python
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
```

- [ ] **Step 2: Write the failing test — append to `backend/tests/test_curation.py`**

Add this import at the top:

```python
from tools.curation import build_draft, frame_timestamp, video_number
```

Append:

```python
def test_frame_timestamp_and_video_number():
    assert frame_timestamp("78.0.jpg") == 78.0
    assert frame_timestamp("/a/b/102.0.jpg") == 102.0
    assert video_number("video_1") == 1
    assert video_number("sources_data/video_12/") == 12


def test_build_draft_seeds_refs_and_candidate_frames(tmp_path):
    video = tmp_path / "video_3"
    video.mkdir()
    (video / "transcript.txt").write_text(SINGLE, encoding="utf-8")
    for name in ["12.0.jpg", "18.0.jpg", "54.0.jpg", "60.0.jpg", "90.0.jpg"]:
        (video / name).write_bytes(b"")

    entries = build_draft(str(video))
    assert [e["ref"] for e in entries] == ["v3q01", "v3q02"]
    assert entries[0]["correct"] == ["A"]
    # q1 window [15, 55] → frames 18.0 and 54.0
    assert entries[0]["candidate_frames"] == ["18.0.jpg", "54.0.jpg"]
    # q2 window [57, 91] → frames 60.0 and 90.0
    assert entries[1]["candidate_frames"] == ["60.0.jpg", "90.0.jpg"]
    assert entries[0]["question_text"] == "" and entries[0]["frame"] == ""
```

- [ ] **Step 3: Run the tests**

Run: `pytest tests/test_curation.py -v`
Expected: all PASS (6 tests total).

- [ ] **Step 4: Commit**

```bash
git add backend/tools/curation.py backend/tests/test_curation.py
git commit -m "feat(tools): seed draft curation files from transcript + frames"
```

---

### Task 3: `crop_frame` + default crops

**Files:**
- Modify: `backend/tools/curation.py`
- Modify: `backend/tests/test_curation.py`

**Interfaces:**
- Produces:
  - `DEFAULT_CROPS: dict[int, tuple[int, int, int, int]]` — per video number, `(x, y, w, h)`.
  - `crop_frame(frame_path: str, box: tuple[int, int, int, int], out_path: str) -> None` — crops `(x, y, w, h)` and saves; creates the output directory.

- [ ] **Step 1: Add Pillow import + crop to `backend/tools/curation.py`**

Add at the top (below `import os`):

```python
from PIL import Image
```

Append:

```python
# Situation photo sits above the yellow divider (~y=632) for this producer's
# 1920x1080 template. Tune per video after viewing frames if needed.
DEFAULT_CROPS: dict[int, tuple[int, int, int, int]] = {
    1: (0, 0, 1920, 632),
    2: (0, 0, 1920, 632),
}


def crop_frame(
    frame_path: str, box: tuple[int, int, int, int], out_path: str
) -> None:
    x, y, w, h = box
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with Image.open(frame_path) as img:
        img.crop((x, y, x + w, y + h)).save(out_path)
```

- [ ] **Step 2: Write the failing test — append to `backend/tests/test_curation.py`**

Add these imports at the top:

```python
from PIL import Image
from tools.curation import DEFAULT_CROPS, crop_frame
```

Append:

```python
def test_default_crops_present():
    assert DEFAULT_CROPS[1] == (0, 0, 1920, 632)


def test_crop_frame_produces_expected_size(tmp_path):
    src = tmp_path / "frame.jpg"
    Image.new("RGB", (1920, 1080), "white").save(src)
    out = tmp_path / "out" / "q01.jpg"
    crop_frame(str(src), (0, 0, 1920, 632), str(out))
    assert out.exists()
    with Image.open(out) as img:
        assert img.size == (1920, 632)
```

- [ ] **Step 3: Run the tests**

Run: `pytest tests/test_curation.py -v`
Expected: all PASS (8 tests total).

- [ ] **Step 4: Commit**

```bash
git add backend/tools/curation.py backend/tests/test_curation.py
git commit -m "feat(tools): add frame cropper with per-video default crops"
```

---

### Task 4: `build` (+ validation, xlsx regeneration) and CLI `main`

**Files:**
- Modify: `backend/tools/curation.py`
- Modify: `backend/tests/test_curation.py`

**Interfaces:**
- Consumes: `crop_frame`/`DEFAULT_CROPS` (Task 3), `video_number` (Task 2), `parse_workbook` (existing, `app.importer`).
- Produces:
  - `validate_entry(entry: dict) -> None` — raises `ValueError` (naming the `ref`) on a bad entry.
  - `build(curation_dir: str, frames_root: str, media_root: str, xlsx_path: str) -> int` — crops chosen frames + regenerates `questions.xlsx`; returns the number of questions written.
  - `main(argv: list[str] | None = None) -> int` — argparse dispatch for `draft` and `build`.

- [ ] **Step 1: Add imports + validation + build + main to `backend/tools/curation.py`**

Add these imports at the top:

```python
import argparse
import glob

from openpyxl import Workbook
```

Append:

```python
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
            box = tuple(entry["crop"]) if entry.get("crop") else DEFAULT_CROPS[number]
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
```

- [ ] **Step 2: Write the failing tests — append to `backend/tests/test_curation.py`**

Add these imports at the top:

```python
import json

import pytest
from app.importer import parse_workbook
from tools.curation import build, validate_entry
```

Append:

```python
def _entry(**over):
    entry = {
        "ref": "v1q01", "theme": "vitesse",
        "question_text": "Le régulateur permet de",
        "options": {"A": "maintenir", "B": "bloquer"},
        "correct": ["A"], "explanation": "Explication.",
        "frame": "18.0.jpg", "crop": None,
    }
    entry.update(over)
    return entry


def test_validate_entry_rejects_bad_rows():
    with pytest.raises(ValueError, match="empty question_text"):
        validate_entry(_entry(question_text=""))
    with pytest.raises(ValueError, match="no correct answer"):
        validate_entry(_entry(correct=[]))
    with pytest.raises(ValueError, match="have no option"):
        validate_entry(_entry(correct=["C"]))
    with pytest.raises(ValueError, match="no frame chosen"):
        validate_entry(_entry(frame=""))


def _setup_build(tmp_path):
    curation = tmp_path / "curation"
    curation.mkdir()
    frames = tmp_path / "frames" / "video_1"
    frames.mkdir(parents=True)
    Image.new("RGB", (1920, 1080), "white").save(frames / "18.0.jpg")
    (curation / "video_1.json").write_text(
        json.dumps([_entry(correct=["A"])]), encoding="utf-8"
    )
    media = tmp_path / "media"
    xlsx = tmp_path / "questions.xlsx"
    return curation, tmp_path / "frames", media, xlsx


def test_build_crops_and_writes_valid_xlsx(tmp_path):
    curation, frames_root, media, xlsx = _setup_build(tmp_path)
    n = build(str(curation), str(frames_root), str(media), str(xlsx))
    assert n == 1
    # cropped media created at media/video_1/v1q01.jpg
    cropped = media / "video_1" / "v1q01.jpg"
    assert cropped.exists()
    with Image.open(cropped) as img:
        assert img.size == (1920, 632)
    # generated xlsx passes the existing importer's validation
    rows = parse_workbook(str(xlsx))
    assert len(rows) == 1
    assert rows[0].ref == "v1q01"
    assert rows[0].media_path == "video_1/v1q01.jpg"
    assert rows[0].media_type == "image"
    assert [o.label for o in rows[0].options if o.is_correct] == ["A"]


def test_build_is_idempotent(tmp_path):
    curation, frames_root, media, xlsx = _setup_build(tmp_path)
    build(str(curation), str(frames_root), str(media), str(xlsx))
    build(str(curation), str(frames_root), str(media), str(xlsx))
    assert len(parse_workbook(str(xlsx))) == 1
```

- [ ] **Step 3: Run the tests**

Run: `pytest tests/test_curation.py -v`
Expected: all PASS (12 tests total). This includes the integration check that `build`'s output satisfies the Phase-1 `parse_workbook` validator.

- [ ] **Step 4: Run the full backend suite**

Run: `pytest -q`
Expected: all pass (no regressions).

- [ ] **Step 5: Commit**

```bash
git add backend/tools/curation.py backend/tests/test_curation.py
git commit -m "feat(tools): build questions.xlsx + crops from curation files"
```

---

## After the tooling (collaborative, not a task here)

Once the tooling is merged, curate the two videos together:
1. `python backend/tools/curation.py draft sources_data/video_1 backend/data/curation/video_1.json`
   (and `video_2`).
2. The assistant views each question's `candidate_frames`, fills `question_text`/`options`/`theme`/`frame`, refines `explanation`, and proposes the theme vocabulary for the user to validate.
3. `python backend/tools/curation.py build` → crops + `questions.xlsx`.
4. `cd backend && python -m app.cli import data/questions.xlsx` → verify in the app.

## Self-Review

**Spec coverage:**
- Transcript parsing (timestamps, single/multi answer, inline markers, ASR-robust segmentation by "Bonne réponse") → Task 1. ✓
- Draft seeding (ref by ordinal, correct + raw explanation + candidate frames) → Task 2. ✓
- Cropping the situation photo (Pillow, per-video default + override) → Task 3. ✓
- Build: validation (fail loudly by ref), crops, regenerate xlsx (exact columns, comma-joined correct, media_path/type), idempotent, and generated xlsx satisfies the existing importer → Task 4. ✓
- CLI `draft`/`build` from repo root → Task 4 (`main`). ✓
- Raw frames git-ignored; curation/media/xlsx tracked → paths in `main` defaults + build writes under `backend/`. ✓

**Placeholder scan:** No TBDs; every code + test block is concrete.

**Type consistency:** `ParsedQuestion` fields (`index`, `correct`, `explanation_raw`, `display_start`, `end_time`) defined in Task 1, consumed in Task 2's `build_draft`. `frame_timestamp`/`video_number` defined Task 2, used in Tasks 2 and 4. `crop_frame(frame_path, box, out_path)` + `DEFAULT_CROPS` defined Task 3, used in Task 4's `build`. `build`/`validate_entry`/`main` in Task 4. xlsx columns match the Phase-1 importer's `REQUIRED_COLUMNS`, verified by the `parse_workbook` integration test.

**Deferred:** actual curation content; video-clip media; avatar auto-detection; curation UI.
