"""Tie-aware moneyline arithmetic for the NFL contract.

The NBA policy module assumes every settled game pays out or loses. On a
two-way NFL moneyline a tie is a PUSH: the stake is returned and the bet
neither wins nor loses. That changes the expected value, the break-even price
and the Kelly fraction, so reusing the NBA arithmetic unchanged would
systematically overstate edge.

    EV per unit staked = p_win*(d-1) - p_lose*1 - cost
    with p_win + p_lose + p_push = 1

A push returns the stake, contributing zero to profit but still consuming
exposure and still paying any per-stake cost. Because p_lose is smaller than
(1 - p_win) whenever a push is possible, ignoring the push makes a bet look
worse on EV but also mis-sizes Kelly; both are corrected here.

Kelly for a three-outcome bet with a push is the growth-optimal fraction of
    f* = (p_win*(d-1) - p_lose) / (d-1)
which reduces to the familiar binary form when p_push = 0.
"""
import numpy as np

CONTRACT = "nfl_regular_fullgame_moneyline_ot_tie_push"


def settle(outcome, side, odds, stake, cost_per_stake=0.):
    """Return realised profit for one settled NFL moneyline bet.

    outcome is "home", "away" or "tie". A tie pushes: the stake comes back, so
    profit is zero before costs. Cancellations and postponements beyond the
    book's action window are voids and settle exactly like a push.
    """
    if side not in ("home", "away"):
        raise ValueError("side must be home or away")
    if outcome not in ("home", "away", "tie", "void"):
        raise ValueError("outcome must be home, away, tie or void")
    if stake < 0 or odds <= 1:
        raise ValueError("Stake must be nonnegative and decimal odds above 1")
    charge = stake*cost_per_stake
    if outcome in ("tie", "void"):
        return -charge          # stake returned; only the transaction cost is sunk
    if outcome == side:
        return stake*(odds-1)-charge
    return -stake-charge


def candidate(p_home, p_tie, home_odds, away_odds, policy):
    """Best of the two sides under the push-aware contract, or neither."""
    p_tie = float(np.clip(p_tie, 0., .5))
    p_home = float(np.clip(p_home, 0., 1.))
    haircut = policy["probability_haircut"]
    cost = policy["cost_per_stake"]
    decided = 1-p_tie
    sides = {"home": p_home*decided, "away": (1-p_home)*decided}
    choices = []
    for side, p_win in sides.items():
        odds = float(home_odds if side == "home" else away_odds)
        # The haircut is applied to the winning probability only; the push
        # probability is not a claim about our edge, so it is not shaved.
        risk = max(0., p_win-haircut)
        p_lose = max(0., decided-risk) if decided > 0 else 0.
        ev = risk*(odds-1)-p_lose-cost
        edge = risk*(odds-1)-p_lose
        kelly = max(0., edge/(odds-1)) if odds > 1 else 0.
        # Break-even price given the push: solve risk*(d-1) - p_lose - cost = 0.
        minimum = (p_lose+cost)/risk+1 if risk > 0 else None
        choices.append({"side": side, "p_win": risk, "p_lose": p_lose, "p_push": p_tie,
                        "odds": odds, "ev": ev, "kelly": kelly, "min_odds": minimum})
    best = max(choices, key=lambda c: c["ev"])
    best["qualifies"] = best["ev"] >= policy["min_ev"] and best["kelly"] > 0
    best["contract"] = CONTRACT
    return best
