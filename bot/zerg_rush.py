"""Zerg rush opponent profile.

Handles the parts of the rush that the ares build runner can't express in
`zerg_builds.yml`:

- worker mining, with speedmining (mineral boosting) explicitly disabled
- the all-in attack once the opening build completes

The opening itself (Spawning Pool, Overlords, Zerglings, natural Hatchery,
Queen) is run by ares' build runner from `zerg_builds.yml`; the opening to use
is forced via the `MyBotBuild` key in `config.yml` (see `bot/main.py`).
"""

from typing import TYPE_CHECKING

from ares.behaviors.macro import Mining
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit

if TYPE_CHECKING:
    from ares import AresBot

#: how often (game seconds) the all-in attack order is re-issued so that
#: newly spawned Zerglings join the wave
ATTACK_REISSUE_INTERVAL: float = 2.0


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

        # opening still running: ares' build runner handles everything
        if not self.ai.build_order_runner.build_completed:
            return

        # opening done: send the finished wave at the enemy
        self._all_in_attack()

    def _all_in_attack(self) -> None:
        """Attack-move the whole rush army at the rush target.

        Orders are re-issued every `ATTACK_REISSUE_INTERVAL` game seconds so
        Zerglings that spawn after the opening completes join the all-in.
        """
        ai: "AresBot" = self.ai
        if ai.time - self._last_attack_time < ATTACK_REISSUE_INTERVAL:
            return

        attackers: list[Unit] = [
            *ai.units(UnitTypeId.ZERGLING).ready,
            *ai.units(UnitTypeId.QUEEN).ready,
        ]
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