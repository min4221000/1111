# assets.py
import copy
import random

STAGE_INFO = {
    1: {"name": "초보자의 숲", "multiplier": 1.0},
    2: {"name": "어둠의 던전", "multiplier": 1.5}
}

def get_stage_by_floor(floor):
    if floor <= 15: return 1
    return 2

# 1. 직업 데이터 (전사, 마법사 고정 / 크리티컬 등 삭제)
CLASSES = {
    "전사": {
        "name": "전사", "hp": 100, "mp": 10, "atk": 20, "defense": 5, "spd": 10,
        "type": "melee", # 근접: 턴당 MP 1 회복
        "deck": ["강타", "강타", "강타", "방패막기", "방패막기", "전투의함성", "응급처치"]
    },
    "마법사": {
        "name": "마법사", "hp": 60, "mp": 20, "atk": 20, "defense": 2, "spd": 12,
        "type": "ranged", # 원거리: 턴당 MP 2 회복
        "deck": ["화염구", "화염구", "화염구", "마나폭발", "마법방어막", "번개화살", "치유의빛"]
    }
}

# 2. 카드 데이터 (직업 전용으로 분리)
CARDS = {
    # ── 전사 전용 ──
    "강타": {"name": "강타", "class": "전사", "cost": 3, "damage_mult": 1.5, "heal": 0, "target": "enemy", "effect": None, "description": "ATK 1.5배 데미지."},
    "방패막기": {"name": "방패막기", "class": "전사", "cost": 4, "damage_mult": 0, "heal": 0, "target": "self", "effect": "def_up", "description": "3턴간 방어력 5 증가."},
    "연속베기": {"name": "연속베기", "class": "전사", "cost": 6, "damage_mult": 2.2, "heal": 0, "target": "enemy", "effect": None, "description": "ATK 2.2배 강력한 데미지."},
    "전투의함성": {"name": "전투의함성", "class": "전사", "cost": 8, "damage_mult": 0, "heal": 0, "target": "party", "effect": "atk_up", "description": "파티 전체 3턴간 공격력 20% 상승."},
    "응급처치": {"name": "응급처치", "class": "전사", "cost": 5, "damage_mult": 0, "heal": 25, "target": "ally", "effect": None, "description": "아군 1명 HP 25 회복."},
    
    # ── 마법사 전용 ──
    "화염구": {"name": "화염구", "class": "마법사", "cost": 5, "damage_mult": 1.8, "heal": 0, "target": "enemy", "effect": "burn", "description": "ATK 1.8배 + 화상(3턴) 부여."},
    "번개화살": {"name": "번개화살", "class": "마법사", "cost": 7, "damage_mult": 1.5, "heal": 0, "target": "enemy", "effect": "stun", "description": "ATK 1.5배 + 기절(1턴) 부여."},
    "마나폭발": {"name": "마나폭발", "class": "마법사", "cost": 12, "damage_mult": 2.5, "heal": 0, "target": "enemy_all", "effect": None, "description": "모든 적에게 ATK 2.5배 광역 데미지."},
    "마법방어막": {"name": "마법방어막", "class": "마법사", "cost": 6, "damage_mult": 0, "heal": 0, "target": "self", "effect": "def_up", "description": "3턴간 방어력 5 증가."},
    "치유의빛": {"name": "치유의빛", "class": "마법사", "cost": 6, "damage_mult": 0, "heal": 40, "target": "ally", "effect": None, "description": "아군 1명 HP 40 대폭 회복."},
}

# 3. 몬스터 (간소화)
MONSTERS = {
    # 1 스테이지 (1~14층)
    "고블린": {"name": "고블린", "stage": 1, "base_hp": 40, "base_atk": 8, "base_def": 2, "pattern": ["normal", "normal", "power"], "reward_gold": 15},
    "늑대": {"name": "늑대", "stage": 1, "base_hp": 55, "base_atk": 12, "base_def": 1, "pattern": ["normal", "rush", "normal"], "reward_gold": 20},
    "트롤새끼": {"name": "트롤새끼", "stage": 1, "base_hp": 80, "base_atk": 10, "base_def": 5, "pattern": ["normal", "power", "normal"], "reward_gold": 25},
    # 2 스테이지 (16~29층)
    "해골전사": {"name": "해골전사", "stage": 2, "base_hp": 120, "base_atk": 18, "base_def": 8, "pattern": ["normal", "power", "normal"], "reward_gold": 30},
    "불도마뱀": {"name": "불도마뱀", "stage": 2, "base_hp": 100, "base_atk": 22, "base_def": 5, "pattern": ["normal", "fire_aoe", "normal"], "reward_gold": 35},
    "암흑기사": {"name": "암흑기사", "stage": 2, "base_hp": 150, "base_atk": 25, "base_def": 12, "pattern": ["normal", "dark_slash", "power"], "reward_gold": 45},
}

# 4. 보스 (15층, 30층)
BOSSES = {
    15: {"name": "숲의 군주", "base_hp": 250, "base_atk": 20, "base_def": 10, "pattern": ["normal", "power", "aoe", "normal"], "reward_gold": 100},
    30: {"name": "심연의 근원", "base_hp": 500, "base_atk": 35, "base_def": 15, "pattern": ["normal", "dark_slash", "power", "aoe"], "reward_gold": 500},
}

# 5. 이벤트 (간소화)
EVENTS = [
    {"name": "신비한 샘물", "description": "맑은 물이 솟아납니다.", "choices": [{"text": "마신다 (파티 HP 30 회복)", "effect": {"party_hp": 30}}]},
    {"name": "버려진 무기고", "description": "쓸만한 무기가 보입니다.", "choices": [{"text": "챙긴다 (파티 ATK +3)", "effect": {"atk": 3}}, {"text": "무시한다", "effect": {}}]},
    {"name": "마력의 파편", "description": "공중에 떠다니는 마력 덩어리입니다.", "choices": [{"text": "흡수한다 (최대 HP +10)", "effect": {"max_hp": 10}}, {"text": "무시한다", "effect": {}}]}
]

# 팩토리 함수들
def get_monster(name: str, floor: int):
    stage = get_stage_by_floor(floor)
    base = copy.deepcopy(MONSTERS[name])
    scale = (1 + floor * 0.1) * STAGE_INFO[stage]['multiplier']
    base["hp"] = int(base["base_hp"] * scale)
    base["atk"] = int(base["base_atk"] * scale)
    base["defense"] = int(base["base_def"] * scale)
    return base

def get_boss(floor: int):
    base = copy.deepcopy(BOSSES[floor])
    scale = 1 + floor * 0.05
    base["hp"] = int(base["base_hp"] * scale)
    base["atk"] = int(base["base_atk"] * scale)
    base["defense"] = int(base["base_def"] * scale)
    return base

def get_class(name: str): return copy.deepcopy(CLASSES[name])
def get_card(name: str): return copy.deepcopy(CARDS[name])
def get_random_event(): return copy.deepcopy(random.choice(EVENTS))
def get_stage_monsters(stage: int): return [name for name, data in MONSTERS.items() if data["stage"] == stage]