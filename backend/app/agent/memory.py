"""Steps 6-8: Bayesian score update, demote/retire, expiry, reason-tag lessons. Log every change."""


def bayesian_score(wins: float, losses: float) -> float:
    return (wins + 1) / (wins + losses + 2)
