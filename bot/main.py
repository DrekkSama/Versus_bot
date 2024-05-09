from typing import Optional

from ares import AresBot
from ares.behaviors.combat import CombatManeuver
from ares.behaviors.combat.individual import StutterUnitBack
from cython_extensions import cy_closest_to, cy_distance_to



from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.unit import Unit
from sc2.position import Point2
from sc2.units import Units



class MyBot(AresBot):
    def __init__(self, game_step_override: Optional[int] = None):
        
        super().__init__(game_step_override)

    async def on_step(self, iteration: int) -> None:
        await super(MyBot, self).on_step(iteration)
        
        enemy_units = self.enemy_units
        #get marines to Attack towards the enemy start location
        for marine in self.units(UnitTypeId.MARINE).idle:
            harrass_maneuvers = CombatManeuver()

            if enemy_units:

                closest_enemy: Unit = cy_closest_to(marine.position, enemy_units)
                target = self.enemy_start_locations[0] 
                
                harrass_maneuvers.add(StutterUnitBack
                                      (marine, 
                                       closest_enemy, 
                                       kite_via_pathing=True))
                
                self.register_behavior(harrass_maneuvers) 
                
      
        
