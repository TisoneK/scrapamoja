"""What to do about each kind of block: an ordered ladder of actions.

The ladder is walked by *attempt number* (how many consecutive blocks of this
type the site has produced), so the first challenge gets patience, the second
a stronger browser, and later ones a failover or a cooldown — never the same
retry in a loop. Ladders are data; override per site if needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

from .models import Action, BlockType, BlockVerdict, Decision

A = Action

DEFAULT_LADDERS: Dict[BlockType, Tuple[Action, ...]] = {
    # A better browser cannot change the country the request comes from.
    BlockType.GEO_BLOCK: (A.ROTATE_PROXY, A.FAILOVER_SITE, A.COOLDOWN),
    # Real browsers pass JS validation by running it: wait, then a stronger
    # (persistent, real-Chrome) browser, then a human, then give the site up.
    BlockType.JS_CHALLENGE: (A.WAIT_FOR_CLEARANCE, A.ESCALATE_BROWSER, A.ESCALATE_BROWSER,
                             A.HUMAN_HANDOFF, A.FAILOVER_SITE, A.COOLDOWN),
    # No third-party CAPTCHA solving: a stronger browser sometimes avoids the
    # check, otherwise a person solves it once and the profile remembers.
    BlockType.CAPTCHA: (A.ESCALATE_BROWSER, A.HUMAN_HANDOFF, A.FAILOVER_SITE, A.COOLDOWN),
    BlockType.RATE_LIMITED: (A.COOLDOWN,),
    BlockType.IP_BANNED: (A.ROTATE_PROXY, A.FAILOVER_SITE, A.COOLDOWN),
    BlockType.ACCESS_DENIED: (A.REFRESH_SESSION, A.ESCALATE_BROWSER, A.COOLDOWN),
    BlockType.AUTH_EXPIRED: (A.REFRESH_SESSION, A.COOLDOWN),
}

# Base cooldown (seconds) when the ladder reaches COOLDOWN; doubles per
# consecutive block, capped by ``max_cooldown``.
DEFAULT_COOLDOWNS: Dict[BlockType, float] = {
    BlockType.GEO_BLOCK: 3600.0,
    BlockType.JS_CHALLENGE: 1800.0,
    BlockType.CAPTCHA: 1800.0,
    BlockType.RATE_LIMITED: 60.0,
    BlockType.IP_BANNED: 7200.0,
    BlockType.ACCESS_DENIED: 900.0,
    BlockType.AUTH_EXPIRED: 300.0,
}


@dataclass
class BlockPolicy:
    ladders: Dict[BlockType, Tuple[Action, ...]] = field(default_factory=lambda: dict(DEFAULT_LADDERS))
    cooldowns: Dict[BlockType, float] = field(default_factory=lambda: dict(DEFAULT_COOLDOWNS))
    max_cooldown: float = 6 * 3600.0
    # Actions the caller cannot perform right now (no proxy pool, no display,
    # no failover list, non-interactive run) are skipped, not failed.
    unavailable: frozenset = frozenset()

    def decide(self, verdict: BlockVerdict, attempt: int, consecutive: int) -> Decision:
        """Pick the rung for ``attempt`` (0-based, per block type)."""
        ladder = [a for a in self.ladders.get(verdict.type, (A.COOLDOWN,))
                  if a not in self.unavailable or a is A.COOLDOWN]
        action = ladder[min(attempt, len(ladder) - 1)]
        if action not in (A.COOLDOWN, A.FAILOVER_SITE):
            return Decision(action, 0.0, f"{verdict.type.value} attempt {attempt + 1}")
        # Giving a site up (cooldown, or failing over to a sister site) also
        # rests it, so the rest of the run does not walk back into the block.
        base = verdict.retry_after if verdict.retry_after else self.cooldowns.get(verdict.type, 900.0)
        seconds = min(self.max_cooldown, base * (2 ** max(0, consecutive - 1)))
        why = "ladder exhausted" if action is A.COOLDOWN else "failing over"
        return Decision(action, seconds, f"{verdict.type.value}: {why}")
