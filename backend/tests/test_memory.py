from app.agent.memory import bayesian_score


def test_new_lesson_starts_at_half():
    assert bayesian_score(0, 0) == 0.5
