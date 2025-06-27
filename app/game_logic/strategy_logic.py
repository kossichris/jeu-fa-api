# # app/game_logic/strategy_logic.py
# from enum import Enum
# from typing import Tuple, Dict, Optional
# from pydantic import BaseModel
# import random
# from typing import Any  # Pour les types Dict

# class Strategy(str, Enum):
#     SUBMISSION = "V"
#     COOPERATION = "C"
#     WAR = "G"

# class FaduType(str, Enum):
#     STANDARD = "standard"
#     SACRIFICE = "sacrifice"

# class TurnResult(BaseModel):
#     turn_number: int
#     player1_pfh: int
#     player2_pfh: int
#     player1_strategy: Strategy
#     player2_strategy: Strategy
#     player1_sacrifice: bool
#     player2_sacrifice: bool
#     player1_fadu: Optional[Dict[str, Any]]
#     player2_fadu: Optional[Dict[str, Any]]
#     player1_sacrifice_fadu: Optional[Dict[str, Any]]
#     player2_sacrifice_fadu: Optional[Dict[str, Any]]

# # Constants
# INITIAL_PFH = 100
# SACRIFICE_COST = 14
# WINNING_PFH = 280
# MAX_TURNS = 20
# MAX_CONSECUTIVE_LOSSES = 3

# # Strategic parameters (exactly as in your calculate_gains method)
# a = 0.0  # Parameter for Soumission vs Soumission
# b = 0.0  # Parameter for Soumission vs Soumission
# c = 0.2  # Parameter for Cooperation vs War
# d = 0.2  # Parameter for War vs War
# e = 0.3  # Parameter for Cooperation transfer
# f = 0.8  # Parameter for War payoff

# def calculate_gains(
#     strategy1: Strategy,
#     strategy2: Strategy,
#     pfh1: int,
#     pfh2: int,
#     fadu1: Optional[Dict] = None,
#     fadu2: Optional[Dict] = None,
#     sacrifice1: bool = False,
#     sacrifice2: bool = False
# ) -> Tuple[int, int]:
#     """
#     Calculate gains according to the exact payoff matrix from the provided logic.
#     Returns (new_pfh1, new_pfh2)
#     """
#     # Get base PFH values from Fadus
#     X = fadu1.get("pfh", pfh1) if fadu1 else pfh1
#     Y = fadu2.get("pfh", pfh2) if fadu2 else pfh2

#     # Apply sacrifice card PFH if sacrifice was made
#     if sacrifice1 and fadu1 and fadu1.get("type") == FaduType.SACRIFICE:
#         X = fadu1["pfh"]
#     if sacrifice2 and fadu2 and fadu2.get("type") == FaduType.SACRIFICE:
#         Y = fadu2["pfh"]

#     # Calculate base gains without sacrifice cost
#     gains_p1, gains_p2 = 0, 0

#     # Soumission (V) vs Soumission (V)
#     if strategy1 == Strategy.SUBMISSION and strategy2 == Strategy.SUBMISSION:
#         gains_p1 = int((1 - a) * X + b * Y)
#         gains_p2 = int(a * X + (1 - b) * Y)

#     # Soumission (V) vs Coopération (C)
#     elif strategy1 == Strategy.SUBMISSION and strategy2 == Strategy.COOPERATION:
#         gains_p1 = int(X + (1 - f) * c * (X + Y))
#         gains_p2 = int(Y + f * c * (X + Y))

#     # Soumission (V) vs Guerre (G)
#     elif strategy1 == Strategy.SUBMISSION and strategy2 == Strategy.WAR:
#         gains_p1 = int((1 - e) * X)
#         gains_p2 = int(Y + e * X)

#     # Coopération (C) vs Soumission (V)
#     elif strategy1 == Strategy.COOPERATION and strategy2 == Strategy.SUBMISSION:
#         gains_p1 = int(X + f * c * (X + Y))
#         gains_p2 = int(Y + (1 - f) * c * (X + Y))

#     # Coopération (C) vs Coopération (C)
#     elif strategy1 == Strategy.COOPERATION and strategy2 == Strategy.COOPERATION:
#         gains_p1 = int((1 + c) * X)
#         gains_p2 = int((1 + c) * Y)

#     # Coopération (C) vs Guerre (G)
#     elif strategy1 == Strategy.COOPERATION and strategy2 == Strategy.WAR:
#         gains_p1 = int((1 - e) * (1 + c) * X)
#         gains_p2 = int((1 + c) * (Y + e * X))

#     # Guerre (G) vs Soumission (V)
#     elif strategy1 == Strategy.WAR and strategy2 == Strategy.SUBMISSION:
#         gains_p1 = int(X + e * Y)
#         gains_p2 = int((1 - e) * Y)

#     # Guerre (G) vs Coopération (C)
#     elif strategy1 == Strategy.WAR and strategy2 == Strategy.COOPERATION:
#         gains_p1 = int((1 + c) * (X + e * Y))
#         gains_p2 = int((1 - e) * (1 + c) * Y)

#     # Guerre (G) vs Guerre (G)
#     elif strategy1 == Strategy.WAR and strategy2 == Strategy.WAR:
#         I_X_gt_Y = 1 if X > Y else 0
#         I_Y_gt_X = 1 if Y > X else 0
        
#         gains_p1 = int((1 - d) * X + e * Y * I_X_gt_Y - e * X * I_Y_gt_X)
#         gains_p2 = int((1 - d) * Y + e * X * I_Y_gt_X - e * Y * I_X_gt_Y)

#     # Apply sacrifice cost if sacrifice was made
#     if sacrifice1:
#         gains_p1 -= SACRIFICE_COST
#     if sacrifice2:
#         gains_p2 -= SACRIFICE_COST

#     # Ensure gains are never negative
#     return max(gains_p1, 0), max(gains_p2, 0)

# def check_victory_conditions(
#     player1_pfh: int,
#     player2_pfh: int,
#     player1_loss_streak: int,
#     player2_loss_streak: int,
#     current_turn: int
# ) -> Tuple[bool, Optional[int]]:
#     """Check game end conditions exactly as in your next_phase method"""
#     # Loss by 3 consecutive zeros
#     if player1_loss_streak >= MAX_CONSECUTIVE_LOSSES:
#         return True, 2
#     if player2_loss_streak >= MAX_CONSECUTIVE_LOSSES:
#         return True, 1
    
#     # Win by reaching 280 PFH
#     if player1_pfh >= WINNING_PFH:
#         return True, 1
#     if player2_pfh >= WINNING_PFH:
#         return True, 2
    
#     # Game end after max turns
#     if current_turn >= MAX_TURNS:
#         if player1_pfh > player2_pfh:
#             return True, 1
#         elif player2_pfh > player1_pfh:
#             return True, 2
#         else:
#             return True, None  # Tie
    
#     return False, None

# def process_turn(
#     game_data: Dict,
#     player1_action: Dict,
#     player2_action: Dict
# ) -> TurnResult:
#     """Process a complete game turn with all mechanics"""
#     # Draw standard Fadus
#     fadu1 = draw_fadu(FaduType.STANDARD)
#     fadu2 = draw_fadu(FaduType.STANDARD)
    
#     # Handle sacrifices
#     sacrifice_fadu1 = None
#     if player1_action["sacrifice"] and game_data["player1_pfh"] >= SACRIFICE_COST:
#         sacrifice_fadu1 = draw_fadu(FaduType.SACRIFICE)
    
#     sacrifice_fadu2 = None
#     if player2_action["sacrifice"] and game_data["player2_pfh"] >= SACRIFICE_COST:
#         sacrifice_fadu2 = draw_fadu(FaduType.SACRIFICE)
    
#     # Calculate new PFH values
#     new_pfh1, new_pfh2 = calculate_gains(
#         strategy1=player1_action["strategy"],
#         strategy2=player2_action["strategy"],
#         pfh1=game_data["player1_pfh"],
#         pfh2=game_data["player2_pfh"],
#         fadu1=sacrifice_fadu1 if player1_action["sacrifice"] else fadu1,
#         fadu2=sacrifice_fadu2 if player2_action["sacrifice"] else fadu2,
#         sacrifice1=player1_action["sacrifice"],
#         sacrifice2=player2_action["sacrifice"]
#     )
    
#     # Update consecutive losses
#     player1_loss_streak = game_data.get("player1_consecutive_losses", 0)
#     player2_loss_streak = game_data.get("player2_consecutive_losses", 0)
    
#     if new_pfh1 <= 0:
#         player1_loss_streak += 1
#     else:
#         player1_loss_streak = 0
        
#     if new_pfh2 <= 0:
#         player2_loss_streak += 1
#     else:
#         player2_loss_streak = 0
    
#     # Create turn result
#     return TurnResult(
#         turn_number=game_data["current_turn"],
#         player1_pfh=new_pfh1,
#         player2_pfh=new_pfh2,
#         player1_strategy=player1_action["strategy"],
#         player2_strategy=player2_action["strategy"],
#         player1_sacrifice=player1_action["sacrifice"],
#         player2_sacrifice=player2_action["sacrifice"],
#         player1_fadu=fadu1,
#         player2_fadu=fadu2,
#         player1_sacrifice_fadu=sacrifice_fadu1,
#         player2_sacrifice_fadu=sacrifice_fadu2
#     )

# def draw_fadu(fadu_type: FaduType = FaduType.STANDARD) -> Dict:
#     """Draw a Fadu card (simplified - should be replaced with actual weighted draw)"""
#     return {
#         "type": fadu_type.value,
#         "pfh": random.randint(5, 70),  # Should use actual weighted probabilities
#         "name": f"{fadu_type.value}_card_{random.randint(1, 100)}",
#         "modifiers": {}
#     }

# app/game_logic/strategy_logic.py
from enum import Enum
from typing import Tuple, Dict, Optional
from pydantic import BaseModel
import random
from typing import Any

class Strategy(str, Enum):
    SUBMISSION = "V"
    COOPERATION = "C"
    WAR = "G"

class FaduType(str, Enum):
    STANDARD = "standard"
    SACRIFICE = "sacrifice"

class TurnResult(BaseModel):
    turn_number: int
    player1_pfh: int
    player2_pfh: int
    player1_strategy: Strategy
    player2_strategy: Strategy
    player1_sacrifice: bool
    player2_sacrifice: bool
    player1_fadu: Optional[Dict[str, Any]]
    player2_fadu: Optional[Dict[str, Any]]
    player1_sacrifice_fadu: Optional[Dict[str, Any]]
    player2_sacrifice_fadu: Optional[Dict[str, Any]]
    game_ended: bool
    winner: Optional[int]

# Constants
INITIAL_PFH = 100
SACRIFICE_COST = 14
WINNING_PFH = 280
MAX_TURNS = 20
MAX_CONSECUTIVE_LOSSES = 3

# Strategic parameters
a = 0.0  # Parameter for Soumission vs Soumission
b = 0.0  # Parameter for Soumission vs Soumission
c = 0.2  # Parameter for Cooperation vs War
d = 0.2  # Parameter for War vs War
e = 0.3  # Parameter for Cooperation transfer
f = 0.8  # Parameter for War payoff

def calculate_gains(
    strategy1: Strategy,
    strategy2: Strategy,
    pfh1: int,
    pfh2: int,
    fadu1: Optional[Dict] = None,
    fadu2: Optional[Dict] = None,
    sacrifice1: bool = False,
    sacrifice2: bool = False
) -> Tuple[int, int]:
    """
    Calculate gains according to the exact payoff matrix.
    Returns (new_pfh1, new_pfh2)
    """
    # Determine X and Y values based on sacrifice and fadu cards
    if sacrifice1 and fadu1 and fadu1.get("type") == FaduType.SACRIFICE:
        X = fadu1["pfh"]
    elif fadu1:
        X = fadu1.get("pfh", pfh1)
    else:
        X = pfh1

    if sacrifice2 and fadu2 and fadu2.get("type") == FaduType.SACRIFICE:
        Y = fadu2["pfh"]
    elif fadu2:
        Y = fadu2.get("pfh", pfh2)
    else:
        Y = pfh2

    # Calculate base gains
    gains_p1, gains_p2 = 0, 0

    # Soumission (V) vs Soumission (V)
    if strategy1 == Strategy.SUBMISSION and strategy2 == Strategy.SUBMISSION:
        gains_p1 = int((1 - a) * X + b * Y)
        gains_p2 = int(a * X + (1 - b) * Y)

    # Soumission (V) vs Coopération (C)
    elif strategy1 == Strategy.SUBMISSION and strategy2 == Strategy.COOPERATION:
        gains_p1 = int(X + (1 - f) * c * (X + Y))
        gains_p2 = int(Y + f * c * (X + Y))

    # Soumission (V) vs Guerre (G)
    elif strategy1 == Strategy.SUBMISSION and strategy2 == Strategy.WAR:
        gains_p1 = int((1 - e) * X)
        gains_p2 = int(Y + e * X)

    # Coopération (C) vs Soumission (V)
    elif strategy1 == Strategy.COOPERATION and strategy2 == Strategy.SUBMISSION:
        gains_p1 = int(X + f * c * (X + Y))
        gains_p2 = int(Y + (1 - f) * c * (X + Y))

    # Coopération (C) vs Coopération (C)
    elif strategy1 == Strategy.COOPERATION and strategy2 == Strategy.COOPERATION:
        gains_p1 = int((1 + c) * X)
        gains_p2 = int((1 + c) * Y)

    # Coopération (C) vs Guerre (G)
    elif strategy1 == Strategy.COOPERATION and strategy2 == Strategy.WAR:
        gains_p1 = int((1 - e) * (1 + c) * X)
        gains_p2 = int((1 + c) * (Y + e * X))

    # Guerre (G) vs Soumission (V)
    elif strategy1 == Strategy.WAR and strategy2 == Strategy.SUBMISSION:
        gains_p1 = int(X + e * Y)
        gains_p2 = int((1 - e) * Y)

    # Guerre (G) vs Coopération (C)
    elif strategy1 == Strategy.WAR and strategy2 == Strategy.COOPERATION:
        gains_p1 = int((1 + c) * (X + e * Y))
        gains_p2 = int((1 - e) * (1 + c) * Y)

    # Guerre (G) vs Guerre (G)
    elif strategy1 == Strategy.WAR and strategy2 == Strategy.WAR:
        I_X_gt_Y = 1 if X > Y else 0
        I_Y_gt_X = 1 if Y > X else 0
        
        gains_p1 = int((1 - d) * X + e * Y * I_X_gt_Y - e * X * I_Y_gt_X)
        gains_p2 = int((1 - d) * Y + e * X * I_Y_gt_X - e * Y * I_X_gt_Y)

    # Apply sacrifice cost
    if sacrifice1:
        gains_p1 -= SACRIFICE_COST
    if sacrifice2:
        gains_p2 -= SACRIFICE_COST

    # Ensure gains are never negative
    return max(gains_p1, 0), max(gains_p2, 0)

def check_victory_conditions(
    player1_pfh: int,
    player2_pfh: int,
    player1_loss_streak: int,
    player2_loss_streak: int,
    current_turn: int
) -> Tuple[bool, Optional[int]]:
    """Check game end conditions"""
    # Loss by 3 consecutive zeros
    if player1_loss_streak >= MAX_CONSECUTIVE_LOSSES:
        return True, 2
    if player2_loss_streak >= MAX_CONSECUTIVE_LOSSES:
        return True, 1
    
    # Win by reaching 280 PFH
    if player1_pfh >= WINNING_PFH:
        return True, 1
    if player2_pfh >= WINNING_PFH:
        return True, 2
    
    # Game end after max turns
    if current_turn >= MAX_TURNS:
        if player1_pfh > player2_pfh:
            return True, 1
        elif player2_pfh > player1_pfh:
            return True, 2
        else:
            return True, None  # Tie
    
    return False, None

def draw_fadu(fadu_type: FaduType = FaduType.STANDARD) -> Dict:
    """
    Draw a Fadu card with proper weighted probabilities
    TODO: Implement actual weighted distribution
    """
    if fadu_type == FaduType.STANDARD:
        # Standard Fadu distribution (simplified)
        pfh_values = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70]
        weights = [15, 12, 10, 8, 7, 6, 5, 4, 3, 2, 2, 1, 1, 1]  # Example weights
        pfh = random.choices(pfh_values, weights=weights)[0]
    else:  # SACRIFICE
        # Sacrifice Fadu typically has higher values
        pfh_values = [30, 40, 50, 60, 70, 80, 90, 100]
        weights = [1, 2, 3, 4, 3, 2, 1, 1]  # Example weights
        pfh = random.choices(pfh_values, weights=weights)[0]
    
    return {
        "type": fadu_type.value,
        "pfh": pfh,
        "name": f"{fadu_type.value}_card_{random.randint(1, 100)}",
        "modifiers": {}
    }

def calculate_turn_results(
    game_data: Dict,
    player1_action: Dict,
    player2_action: Dict
) -> TurnResult:
    """
    Main function to calculate turn results
    This is the equivalent of strategy_logic.calculate_turn_results()
    """
    # Draw standard Fadus for both players
    fadu1 = draw_fadu(FaduType.STANDARD)
    fadu2 = draw_fadu(FaduType.STANDARD)
    
    # Handle sacrifices (only if player has enough PFH)
    sacrifice_fadu1 = None
    player1_can_sacrifice = (
        player1_action.get("sacrifice", False) and 
        game_data["player1_pfh"] >= SACRIFICE_COST
    )
    if player1_can_sacrifice:
        sacrifice_fadu1 = draw_fadu(FaduType.SACRIFICE)
    
    sacrifice_fadu2 = None
    player2_can_sacrifice = (
        player2_action.get("sacrifice", False) and 
        game_data["player2_pfh"] >= SACRIFICE_COST
    )
    if player2_can_sacrifice:
        sacrifice_fadu2 = draw_fadu(FaduType.SACRIFICE)
    
    # Calculate new PFH values
    new_pfh1, new_pfh2 = calculate_gains(
        strategy1=player1_action["strategy"],
        strategy2=player2_action["strategy"],
        pfh1=game_data["player1_pfh"],
        pfh2=game_data["player2_pfh"],
        fadu1=sacrifice_fadu1 if player1_can_sacrifice else fadu1,
        fadu2=sacrifice_fadu2 if player2_can_sacrifice else fadu2,
        sacrifice1=player1_can_sacrifice,
        sacrifice2=player2_can_sacrifice
    )
    
    # Update consecutive losses tracking
    player1_loss_streak = game_data.get("player1_consecutive_losses", 0)
    player2_loss_streak = game_data.get("player2_consecutive_losses", 0)
    
    if new_pfh1 == 0:
        player1_loss_streak += 1
    else:
        player1_loss_streak = 0
        
    if new_pfh2 == 0:
        player2_loss_streak += 1
    else:
        player2_loss_streak = 0
    
    # Check victory conditions
    game_ended, winner = check_victory_conditions(
        new_pfh1, new_pfh2,
        player1_loss_streak, player2_loss_streak,
        game_data.get("current_turn", 1)
    )
    
    # Create and return turn result
    return TurnResult(
        turn_number=game_data.get("current_turn", 1),
        player1_pfh=new_pfh1,
        player2_pfh=new_pfh2,
        player1_strategy=player1_action["strategy"],
        player2_strategy=player2_action["strategy"],
        player1_sacrifice=player1_can_sacrifice,
        player2_sacrifice=player2_can_sacrifice,
        player1_fadu=fadu1,
        player2_fadu=fadu2,
        player1_sacrifice_fadu=sacrifice_fadu1,
        player2_sacrifice_fadu=sacrifice_fadu2,
        game_ended=game_ended,
        winner=winner
    )

# Alias pour compatibilité
process_turn = calculate_turn_results