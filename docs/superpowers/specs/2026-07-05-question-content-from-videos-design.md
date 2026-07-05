# Building Real Questions from YouTube Video Frames — Design

**Date:** 2026-07-05
**Status:** Approved (design), pending implementation plan

## 1. Purpose

Replace the placeholder question bank with real questions built from driving-code
training videos. Each video ships as a folder of **frames** (1920×1080 JPEGs, one
every 3 s, filename = timestamp in seconds) plus a timestamped **transcript**. Each
video contains ~10 questions. A frame shows the road-situation photo on top, a
divider, then the question number + text + answer choices below. The goal: a
**hybrid, human-curated** pipeline that turns these into `questions.xlsx` rows +
cropped situation photos the app can serve, designed to extend as new videos are
added.

## 2. Division of labour (hybrid, curator = the assistant)

- **Mechanical (script):** parse a transcript into per-question data (number,
  correct answer(s), explanation, time window, candidate frame list); crop the
  chosen frames; (re)generate `questions.xlsx`.
- **Curation (assistant, viewing frames):** for each question — read the *clean
  on-screen* question text + choices from the frame (the ASR transcript is noisy),
  pick the best frame (sharp, no avatar covering the photo, matches the question),
  assign a practical theme, and write a clean faithful explanation from the
  transcript.

## 3. Data flow & locations

```
sources_data/video_N/            (INPUT, git-ignored: large raw data)
  0.0.jpg … 483.0.jpg, transcript.txt
        │  (1) draft: parse transcript + list candidate frames
        ▼
backend/data/curation/video_N.json   (SOURCE OF TRUTH, tracked — I fill it)
        │  (2) build: crop chosen frames + regenerate xlsx
        ├────────────────► backend/media/video_N/qNN.jpg   (tracked crops)
        └────────────────► backend/data/questions.xlsx     (generated, tracked)
                                   │  (3) existing import CLI
                                   ▼
                              python -m app.cli import → DB
```

- Raw frames/transcripts (`sources_data/`) stay **git-ignored** (already are).
- The curated content (`curation/video_N.json`), the cropped media, and the
  generated `questions.xlsx` are **tracked**, so the app has its content in git
  without needing the raw video data.
- Cropping needs the raw frames present locally (they are on the author's machine).

## 4. Curation file format (`backend/data/curation/video_N.json`)

A JSON array; one object per question that the assistant completes:

```json
{
  "ref": "v1q02",
  "theme": "cyclistes",
  "question_text": "Pour limiter le risque d'accident",
  "options": { "A": "Je ralentis", "B": "Je klaxonne", "C": "Je fais un appel lumineux" },
  "correct": ["A"],
  "explanation": "Le cycliste à contre-sens vous a aperçu : il faut ralentir. Klaxonner ou faire un appel lumineux est inutile.",
  "frame": "78.0.jpg",
  "crop": null
}
```

- `ref`: stable, `v<video>q<NN>` (e.g. `v1q02`). Import is idempotent by `ref`.
- `options`: 2–4 of A/B/C/D (only those present in the question).
- `correct`: list of labels (supports multi-answer, e.g. `["A","D"]`).
- `question_text`/`options`: read from the on-screen text (clean), not the ASR.
- `explanation`: clean faithful rewrite from the transcript.
- `frame`: the chosen frame filename within `sources_data/video_N/`.
- `crop`: `null` → use the video's default crop; or `[x, y, w, h]` to override
  per question (e.g. to dodge an avatar).

## 5. Tooling (`backend/tools/curation.py`, tested)

New dependency: **Pillow** (added to `backend/requirements.txt`) for cropping.

- `parse_transcript(text: str) -> list[ParsedQuestion]` — pure, testable.
  `ParsedQuestion = {number: int, correct: list[str], explanation_raw: str,
  start_time: float, end_time: float | None}`. Robustly finds `question <n>`
  markers (line-start *or* inline, as in video_2) and `Bonne réponse …` (single
  or "X et Y") anywhere in the segment. `[m:ss]` timestamps → seconds.
- `draft(video_dir, out_json)` — seeds `curation/video_N.json` from the transcript:
  fills `ref`/`correct`/`explanation` (raw) + a `candidate_frames` list (frames
  whose timestamp falls in each question's window) and leaves
  `question_text`/`options`/`theme`/`frame` blank for the assistant.
- `build(curation_dir, frames_root, media_root, xlsx_path)` — for every
  `curation/video_N.json`: crop each question's chosen `frame` (default crop or
  override) → `media/video_N/qNN.jpg`; then regenerate `questions.xlsx` from **all**
  curation files (columns: `ref, theme, question_text, option_a..d, correct,
  explanation, media_path, media_type`; `media_path = "video_N/qNN.jpg"`,
  `media_type = "image"`, `correct` joined as e.g. `"A,D"`).

Default crop per video: full width × the region above the yellow divider
(≈ top 60 %). The exact divider row is measured once per video and stored as the
video's default crop in a small config (constant/dict in `curation.py`), since the
template is constant within a producer.

## 6. Themes

Practical, short theme strings assigned per question by the assistant (e.g.
`priorités`, `panneaux`, `vitesse`, `distances-de-sécurité`, `mécanique-entretien`,
`équipements-sécurité`, `permis-à-points`, `assurance-constat`, `cyclistes`,
`premiers-secours`). The proposed set is presented to the user for validation as
questions are curated; themes are free-form strings, so the vocabulary can evolve.

## 7. Workflow per video

Run from the repo root; the tool takes explicit paths:
1. `python backend/tools/curation.py draft sources_data/video_N backend/data/curation/video_N.json`
   → draft `curation/video_N.json` (seeded fields + `candidate_frames`).
2. Assistant views candidate frames, fills question text/options/theme/frame,
   refines the explanation.
3. `python backend/tools/curation.py build` → crops + regenerates `questions.xlsx`.
4. `cd backend && python -m app.cli import data/questions.xlsx` → DB; verify in the app.

Tests import the pure parser as `from tools.curation import parse_transcript`
(pytest runs from `backend/`, where `pythonpath = .` puts `tools/` on the path).

## 8. Scope of this batch

Build the tooling + curate the **two current videos (~20 questions)**. The pipeline
is reusable: dropping a new `sources_data/video_N/` and repeating the workflow adds
its questions. Placeholder questions are replaced by the generated bank.

## 9. Error handling
- Transcript parsing: tolerate ASR noise and both question-marker styles; a
  question with no detectable `Bonne réponse` is flagged in the draft for manual
  fill rather than dropped.
- Build: a curation entry with a missing `frame` file, empty `question_text`, no
  `correct`, or `correct` referencing an absent option → a clear error naming the
  `ref` (fail loudly, don't emit a broken row), consistent with the existing
  importer's philosophy.
- Idempotent by `ref`; re-running `build` + import updates, never duplicates.

## 10. Testing
- `parse_transcript`: question segmentation, single + multi correct
  (`"Bonne réponse A et D"`), inline `question N` markers (video_2 style),
  `[m:ss]` → seconds, and a no-answer question surfaced (not dropped).
- `build`: given a tiny curation file + a synthetic frame image, produces a cropped
  file of the expected dimensions and a `questions.xlsx` with the correct columns,
  `media_path`, and `correct` joining; idempotent re-run.
- `parse_workbook`/import already tested (Phase 1) — the generated xlsx must satisfy
  that importer's validation (verified end-to-end by importing after build).

## 11. Deferred
- Video clips as media (image only for now).
- Automatic avatar detection / automatic frame selection (curation handles it).
- A curation UI (JSON files for now).
