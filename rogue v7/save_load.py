# save_load.py - 세이브/로드 담당
import json
import os

SAVE_FILE = 'save.json'


def save_game(player, last_shop_floor=1, floor_scale=0.10):
    import assets
    data = {
        'floor':            player.current_floor,
        'gold':             player.gold,
        'active_index':     player.active_index,
        'purchased_relics': list(player.purchased_relics),
        'last_shop_floor':  last_shop_floor,
        'floor_scale':      floor_scale,
        'relics':           player.relics,
        'party':            []
    }
    for char in player.party:
        data['party'].append({
            'name':       char['name'],
            'hp':         char['hp'],
            'current_hp': char['current_hp'],
            'atk':        char['atk'],
            'spd':        char['spd'],
            'mp':         char['mp'],
            'deck':       char['deck'][:]
        })
    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_game():
    if not os.path.exists(SAVE_FILE):
        return None
    with open(SAVE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_exists():
    return os.path.exists(SAVE_FILE)


def delete_save():
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
