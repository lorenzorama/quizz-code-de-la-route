import json

import pytest
from app.importer import parse_workbook
from PIL import Image
from tools.curation import DEFAULT_CROPS, crop_frame
from tools.curation import parse_transcript
from tools.curation import build_draft, frame_timestamp, video_number
from tools.curation import build, validate_entry

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


STRAY = """[0:30] Question 1.
[0:34] rouler vite, réponse A, ralentir, réponse B.
[0:50] La bonne attitude. Bonne réponse, réponse B. À vitesse élevée le risque augmente.
"""

NO_LABEL = """[0:30] Question 1.
[0:34] a, réponse A, b, réponse B.
[0:50] Explication sans lettre finale. Bonne réponse évidente.
"""


def test_stray_uppercase_prose_not_captured_as_answer():
    qs = parse_transcript(STRAY)
    assert len(qs) == 1
    assert qs[0].correct == ["B"]


def test_missing_answer_letter_yields_empty_correct():
    qs = parse_transcript(NO_LABEL)
    assert len(qs) == 1
    assert qs[0].correct == []


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


def test_build_unknown_video_without_crop_fails_by_ref(tmp_path):
    curation = tmp_path / "curation"
    curation.mkdir()
    frames = tmp_path / "frames" / "video_99"
    frames.mkdir(parents=True)
    Image.new("RGB", (1920, 1080), "white").save(frames / "18.0.jpg")
    (curation / "video_99.json").write_text(
        json.dumps([_entry(ref="v99q01", correct=["A"], crop=None)]),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no crop for video_99"):
        build(
            str(curation),
            str(tmp_path / "frames"),
            str(tmp_path / "media"),
            str(tmp_path / "questions.xlsx"),
        )


def test_build_reuses_existing_crop_when_source_frame_is_gone(tmp_path):
    curation, frames_root, media, xlsx = _setup_build(tmp_path)
    build(str(curation), str(frames_root), str(media), str(xlsx))

    # The raw source frame gets rotated out (e.g. sources_data replaced by a
    # later batch), but the crop built earlier is still on disk.
    (frames_root / "video_1" / "18.0.jpg").unlink()

    n = build(str(curation), str(frames_root), str(media), str(xlsx))
    assert n == 1
    rows = parse_workbook(str(xlsx))
    assert rows[0].media_path == "video_1/v1q01.jpg"


def test_build_fails_when_frame_and_crop_are_both_missing(tmp_path):
    curation, frames_root, media, xlsx = _setup_build(tmp_path)
    (frames_root / "video_1" / "18.0.jpg").unlink()

    with pytest.raises(ValueError, match="v1q01"):
        build(str(curation), str(frames_root), str(media), str(xlsx))
