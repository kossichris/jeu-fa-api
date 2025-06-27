# app/game_logic/fadu_data.py
from typing import List, Dict

class FaduConfig:
    SACRIFICE_COST = 14
    MIN_PFH = 1
    MAX_PFH = 64

STANDARD_FADUS: List[Dict] = [
    {"id": "f1", "name": "gbe_medji", "pfh": 64, "image": "gbe_medji.png", "count": 1},
    {"id": "f2", "name": "yeku_medji", "pfh": 60, "image": "yeku_medji.png", "count": 1},
    {"id": "f3", "name": "woli_medji", "pfh": 56, "image": "woli_medji.png", "count": 1},
    # ... compléter avec toutes les cartes standard
]

SACRIFICE_FADUS: List[Dict] = [
    {"id": "sf1", "name": "gbe_medji", "pfh": 64, "image": "gbe_medji.png", "count": 4},
    {"id": "sf2", "name": "yeku_medji", "pfh": 60, "image": "yeku_medji.png", "count": 4},
    {"id": "sf3", "name": "woli_medji", "pfh": 56, "image": "woli_medji.png", "count": 4},
    # ... compléter avec toutes les cartes de sacrifice
]

def calculate_probabilities():
    """Calcule les probabilités basées sur les counts"""
    total_standard = sum(f['count'] for f in STANDARD_FADUS)
    total_sacrifice = sum(f['count'] for f in SACRIFICE_FADUS)
    
    standard_with_prob = [
        {**f, "probability": f['count'] / total_standard} 
        for f in STANDARD_FADUS
    ]
    
    sacrifice_with_prob = [
        {**f, "probability": f['count'] / total_sacrifice} 
        for f in SACRIFICE_FADUS
    ]
    
    return {
        "standard": standard_with_prob,
        "sacrifice": sacrifice_with_prob,
        "config": {
            "sacrifice_cost": FaduConfig.SACRIFICE_COST,
            "min_pfh": FaduConfig.MIN_PFH,
            "max_pfh": FaduConfig.MAX_PFH
        }
    }