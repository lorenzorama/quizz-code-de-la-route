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
