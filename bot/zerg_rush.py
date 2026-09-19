"""Zerg rush opponent profile.

Handles the parts of the rush that the ares build runner can't express in
`zerg_builds.yml`:

- worker mining, with speedmining (mineral boosting) explicitly disabled
- the rush attack: Zerglings stream at the enemy the moment they hatch,
  regardless of build progress
- continuous Zergling production + Overlords once the opening completes

The opening itself (Spawning Pool, Overlords, Zerglings, natural Hatchery,
Queen) is run by ares' build runner from `zerg_builds.yml`; the opening to use
is forced via the `MyBotBuild` key in `config.yml` (see `bot/main.py`).
"""

from typing import TYPE_CHECKING

from ares.behaviors.macro import AutoSupply, Mining, SpawnController
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit

if TYPE_CHECKING:
    from ares import AresBot

#: how often (game seconds) the all-in attack order is re-issued so that
#: newly spawned Zerglings join the wave
ATTACK_REISSUE_INTERVAL: float = 2.0

#: army composition used for continuous post-opening production:
#: freeflow Zerglings only (proportions ignored, everything spent on lings)
_ZERGLING_ONLY_COMP: dict = {
    UnitTypeId.ZERGLING: {"proportion": 1.0, "priority": 0},
}


class ZergRush:
    """Per-game state for the Zerg rush profile.

    Instantiated from `MyBot.on_start` when the bot's race is Zerg;
    `step()` is called once per game step from `MyBot.on_step`.
    """

    def __init__(self, ai: "AresBot") -> None:
        self.ai: "AresBot" = ai
        self._last_attack_time: float = -999.0

    def step(self) -> None:
        """Run one game step of the Zerg rush profile."""
        # keep workers mining; mineral_boost (speedmining) is on by default
        # in the Mining behavior, so explicitly turn it off
        self.ai.register_behavior(Mining(mineral_boost=False))

        # rush attack runs regardless of build progress: idle Zerglings
        # stream at the enemy the moment they hatch
        self._all_in_attack()

        # once the opening completes, take over production: keep supply up
        # and keep making lings. (During the opening the build runner needs
        # the larvae for its remaining steps, so production stays with it.)
        if not self.ai.build_order_runner.build_completed:
            return

        # AutoSupply is registered first so Overlords get larva priority
        # when supply-blocked (lings would otherwise eat every larva).
        self.ai.register_behavior(AutoSupply(self.ai.start_location))
        self.ai.register_behavior(
            SpawnController(_ZERGLING_ONLY_COMP, freeflow_mode=True)
        )

    def _all_in_attack(self) -> None:
        """Attack-move idle Zerglings at the rush target.

        Runs every step from the start of the game so the rush jumps out
        immediately — but only idle lings are ordered, so Zerglings that are
        already fighting are never interrupted. Queens are deliberately
        excluded: they stay home for injects, creep spread and base defense
        (see `managers/queen_manager.py`).
        """
        ai: "AresBot" = self.ai
        if ai.time - self._last_attack_time < ATTACK_REISSUE_INTERVAL:
            return

        attackers: list[Unit] = [*ai.units(UnitTypeId.ZERGLING).ready.idle]
        if not attackers:
            return

        target: Point2 = self._rush_target()
        for unit in attackers:
            unit.attack(target)
        self._last_attack_time = ai.time

    def _rush_target(self) -> Point2:
        """Prefer known enemy structures, else enemy start, else map center."""
        ai: "AresBot" = self.ai
        if ai.enemy_structures:
            return ai.enemy_structures.closest_to(ai.start_location).position
        if ai.enemy_start_locations:
            return ai.enemy_start_locations[0]
        return ai.game_info.map_center