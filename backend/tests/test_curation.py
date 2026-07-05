from PIL import Image
from tools.curation import DEFAULT_CROPS, crop_frame
from tools.curation import parse_transcript
from tools.curation import build_draft, frame_timestamp, video_number

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
