# app/game_logic/fadu_logic.py
import random
from typing import Dict, Optional
from .fadu_data import STANDARD_FADUS, SACRIFICE_FADUS, calculate_probabilities, FaduConfig

class FaduService:
    def __init__(self):
        self.probabilities = calculate_probabilities()
    
    def draw_card(self, card_type: str = 'standard') -> Optional[Dict]:
        """Tire une carte selon le type spécifié"""
        if card_type not in ['standard', 'sacrifice']:
            return None
        
        pool_key = 'standard' if card_type == 'standard' else 'sacrifice'
    
        if pool_key not in self.probabilities:
            return None
        
        pool = self.probabilities[pool_key]
    
        if not pool:  # Liste vide
            return None
        
        total = sum(f.get('probability', 0) for f in pool)
    
        if total <= 0:
            return None
            
        rand = random.uniform(0, total)
        cumulative = 0
        
        for card in pool:
            cumulative += card['probability']
            if rand < cumulative:
                return {
                    "id": card['id'],
                    "name": card['name'],
                    "pfh": card['pfh'],
                    "image": card['image'],
                    "type": card_type
                }
        return None
    
def perform_sacrifice(self, current_pfh: int) -> Dict:
    """Gère la logique de sacrifice"""
    cost = FaduConfig.SACRIFICE_COST
    
    if current_pfh < cost:
        return {
            "success": False,
            "message": "PFH insuffisant pour sacrifier",
            "new_pfh": current_pfh  # Pas de changement
        }
    
    sacrifice_card = self.draw_card('sacrifice')
    if not sacrifice_card:
        return {
            "success": False,
            "message": "Échec du tirage de carte sacrifice",
            "new_pfh": current_pfh - cost  # Coût payé mais pas de carte
        }
    
    # Le sacrifice remplace le PFH par la valeur de la carte
    # (après avoir payé le coût)
    new_pfh = sacrifice_card['pfh']
    
    return {
        "success": True,
        "card": sacrifice_card,
        "new_pfh": new_pfh,
        "previous_pfh": current_pfh,
        "cost_paid": cost,
        "pfh_change": new_pfh - current_pfh + cost,  # Gain net
        "message": "Sacrifice réussi"
    }
    
    
    # Instance globale pour compatibilité
_service = FaduService()

def draw_card(card_type: str = 'standard') -> Optional[Dict]:
    """Fonction wrapper pour compatibilité avec game_actions.py"""
    return _service.draw_card(card_type)

def perform_sacrifice(current_pfh: int) -> Dict:
    """Fonction wrapper pour perform_sacrifice"""
    return _service.perform_sacrifice(current_pfh)

def get_card_probabilities() -> Dict:
    """Fonction wrapper pour get_card_probabilities"""
    return _service.get_card_probabilities()