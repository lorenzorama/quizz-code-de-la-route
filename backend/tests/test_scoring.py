from app.scoring import is_answer_correct


def test_single_correct_selected():
    assert is_answer_correct({1}, {1}) is True


def test_single_correct_wrong_option():
    assert is_answer_correct({1}, {2}) is False


def test_multi_correct_all_selected():
    assert is_answer_correct({1, 3}, {1, 3}) is True


def test_multi_correct_partial_selection_is_wrong():
    assert is_answer_correct({1, 3}, {1}) is False


def test_multi_correct_over_selection_is_wrong():
    assert is_answer_correct({1, 3}, {1, 3, 4}) is False


def test_empty_selection_is_wrong():
    assert is_answer_correct({1}, set()) is False


def test_selection_order_irrelevant():
    assert is_answer_correct({1, 2, 3}, {3, 2, 1}) is True


def test_empty_correct_set_is_wrong():
    assert is_answer_correct(set(), set()) is False
