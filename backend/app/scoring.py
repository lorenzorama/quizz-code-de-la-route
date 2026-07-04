def is_answer_correct(
    correct_option_ids: set[int], selected_option_ids: set[int]
) -> bool:
    """A question is correct only when the selected options exactly match the
    (non-empty) set of correct options — all correct chosen, none incorrect."""
    if not correct_option_ids:
        return False
    return selected_option_ids == correct_option_ids
