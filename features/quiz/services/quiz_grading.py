def get_correct_answers(question) -> list:
    """Authoritative correct answer indices for a question (0-based, into `options`)."""
    return list(question.correct_option_indices or [])


def is_answer_correct(question, chosen: list) -> bool:
    """A question is correct when the chosen set exactly matches the correct
    set — for single_answer that's a 1-for-1 match, for multi_answer it's
    all-or-nothing (no missing, no extra)."""
    correct = set(get_correct_answers(question))
    if not correct:
        return False
    return set(chosen or []) == correct
