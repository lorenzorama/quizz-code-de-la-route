import pytest

from app.importer import QuestionImportError, parse_workbook
from tests.helpers import valid_row, write_workbook


def test_parses_single_correct(tmp_path):
    path = write_workbook(tmp_path / "q.xlsx", [valid_row(correct="B")])
    rows = parse_workbook(path)
    assert len(rows) == 1
    q = rows[0]
    assert q.ref == "Q001"
    assert q.media_type == "image"
    assert [o.label for o in q.options if o.is_correct] == ["B"]


def test_parses_multi_correct(tmp_path):
    path = write_workbook(tmp_path / "q.xlsx", [valid_row(correct="A,C")])
    rows = parse_workbook(path)
    correct = {o.label for o in rows[0].options if o.is_correct}
    assert correct == {"A", "C"}


def test_blank_rows_skipped(tmp_path):
    path = write_workbook(tmp_path / "q.xlsx", [valid_row(), {"ref": ""}])
    assert len(parse_workbook(path)) == 1


def test_missing_media_becomes_none(tmp_path):
    path = write_workbook(
        tmp_path / "q.xlsx", [valid_row(media_path="", media_type="none")]
    )
    assert parse_workbook(path)[0].media_path is None


def test_invalid_correct_label_raises(tmp_path):
    path = write_workbook(tmp_path / "q.xlsx", [valid_row(correct="Z")])
    with pytest.raises(QuestionImportError, match="invalid correct labels"):
        parse_workbook(path)


def test_no_correct_answer_raises(tmp_path):
    path = write_workbook(tmp_path / "q.xlsx", [valid_row(correct="")])
    with pytest.raises(QuestionImportError, match="no correct answer"):
        parse_workbook(path)


def test_correct_label_without_option_text_raises(tmp_path):
    path = write_workbook(
        tmp_path / "q.xlsx", [valid_row(correct="D", option_d="")]
    )
    with pytest.raises(QuestionImportError, match="no option text"):
        parse_workbook(path)


def test_duplicate_ref_raises(tmp_path):
    path = write_workbook(
        tmp_path / "q.xlsx", [valid_row(ref="Q001"), valid_row(ref="Q001")]
    )
    with pytest.raises(QuestionImportError, match="duplicate ref"):
        parse_workbook(path)


def test_invalid_media_type_raises(tmp_path):
    path = write_workbook(tmp_path / "q.xlsx", [valid_row(media_type="gif")])
    with pytest.raises(QuestionImportError, match="invalid media_type"):
        parse_workbook(path)


def test_too_few_options_raises(tmp_path):
    path = write_workbook(
        tmp_path / "q.xlsx",
        [valid_row(option_b="", option_c="", option_d="", correct="A")],
    )
    with pytest.raises(QuestionImportError, match="at least 2 options"):
        parse_workbook(path)
