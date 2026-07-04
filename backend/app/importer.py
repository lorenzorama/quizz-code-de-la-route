from dataclasses import dataclass

import openpyxl

VALID_LABELS = ["A", "B", "C", "D"]
VALID_MEDIA_TYPES = {"image", "video", "none"}
REQUIRED_COLUMNS = [
    "ref",
    "theme",
    "question_text",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct",
    "explanation",
    "media_path",
    "media_type",
]


class QuestionImportError(Exception):
    pass


@dataclass
class OptionRow:
    label: str
    text: str
    is_correct: bool


@dataclass
class QuestionRow:
    ref: str
    theme: str
    text: str
    options: list[OptionRow]
    explanation: str
    media_path: str | None
    media_type: str


def parse_workbook(path: str) -> list[QuestionRow]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise QuestionImportError("Workbook is empty")

    header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise QuestionImportError(f"Missing columns: {missing}")
    idx = {name: header.index(name) for name in REQUIRED_COLUMNS}

    def cell(raw: tuple, name: str) -> str:
        value = raw[idx[name]]
        return "" if value is None else str(value).strip()

    result: list[QuestionRow] = []
    seen: set[str] = set()

    for line_no, raw in enumerate(rows[1:], start=2):
        ref = cell(raw, "ref")
        if not ref:
            continue  # skip blank rows

        if ref in seen:
            raise QuestionImportError(f"Row {line_no}: duplicate ref {ref!r}")
        seen.add(ref)

        correct = [c.strip().upper() for c in cell(raw, "correct").split(",") if c.strip()]
        if not correct:
            raise QuestionImportError(f"Row {line_no} ({ref}): no correct answer given")
        bad = [c for c in correct if c not in VALID_LABELS]
        if bad:
            raise QuestionImportError(f"Row {line_no} ({ref}): invalid correct labels {bad}")
        if len(set(correct)) != len(correct):
            raise QuestionImportError(
                f"Row {line_no} ({ref}): duplicate correct label(s)"
            )

        options: list[OptionRow] = []
        for label in VALID_LABELS:
            text = cell(raw, f"option_{label.lower()}")
            if text:
                options.append(OptionRow(label=label, text=text, is_correct=label in correct))
        if len(options) < 2:
            raise QuestionImportError(f"Row {line_no} ({ref}): needs at least 2 options")

        option_labels = {o.label for o in options}
        orphan = [c for c in correct if c not in option_labels]
        if orphan:
            raise QuestionImportError(
                f"Row {line_no} ({ref}): correct label(s) {orphan} have no option text"
            )

        media_type = cell(raw, "media_type").lower() or "none"
        if media_type not in VALID_MEDIA_TYPES:
            raise QuestionImportError(
                f"Row {line_no} ({ref}): invalid media_type {media_type!r}"
            )
        media_path = cell(raw, "media_path") or None

        result.append(
            QuestionRow(
                ref=ref,
                theme=cell(raw, "theme"),
                text=cell(raw, "question_text"),
                options=options,
                explanation=cell(raw, "explanation"),
                media_path=media_path,
                media_type=media_type,
            )
        )

    return result
