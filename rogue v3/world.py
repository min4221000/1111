# world.py
import random
import assets
import time
import combat
import visuals

last_shop_floor = -3 

def generate_floor_event(floor):
    global last_shop_floor
    if floor in [15, 30]: return "boss" # 15층, 30층 보스
    
    rand = random.random()
    if rand > 0.8 and (floor - last_shop_floor >= 3):
        last_shop_floor = floor
        return "shop" # 아이템 대신 능력치/회복 상점
    
    return "combat" if rand < 0.75 else "event"

def handle_combat(player, floor):
    if floor in [15, 30]:
        monster = assets.get_boss(floor)
    else:
        m_name = random.choice(assets.get_stage_monsters(assets.get_stage_by_floor(floor)))
        monster = assets.get_monster(m_name, floor)
    
    monster['current_hp'] = monster['hp']
    print(f"\n🌑 야생의 {monster['name']}이(가) 나타났다!")
    time.sleep(1.5)
    return combat.run_combat(player, monster)

def handle_random_event(player, floor):
    visuals.clear_screen()
    event = assets.get_random_event()
    print(f"🌀 [사건 발생] {event['name']}\n📜 {event['description']}\n")
    
    for i, opt in enumerate(event['choices'], 1):
        print(f"  {i}. {opt['text']}")
        
    choice = 0
    while not (0 <= choice < len(event['choices'])):
        try: choice = int(input("\n번호 입력: ")) - 1
        except ValueError: pass

    effect = event['choices'][choice].get('effect', {})
    _apply_effect(player, effect)
    time.sleep(2)

def handle_shop(player, floor):
    visuals.clear_screen()
    while True:
        print(f"🏕️ [휴식처] 골드를 지불하고 정비할 수 있습니다. (보유: {player.gold}G)\n")
        print("  1. 전원 HP 30 회복 (30G)")
        print("  2. 파티 전체 공격력 +2 (60G)")
        print("  0. 떠나기")
        
        try: choice = int(input("\n선택: "))
        except ValueError: continue
        
        if choice == 0: break
        elif choice == 1 and player.gold >= 30:
            player.gold -= 30
            for c in player.party: c['current_hp'] = min(c['hp'], c['current_hp'] + 30)
            print("❤️ 파티의 체력이 회복되었습니다!")
        elif choice == 2 and player.gold >= 60:
            player.gold -= 60
            for c in player.party: c['atk'] += 2
            print("⚔️ 파티의 공격력이 올랐습니다!")
        else:
            print("골드가 부족하거나 잘못된 입력입니다.")
        time.sleep(1)
        visuals.clear_screen()

def _apply_effect(player, effect):
    if 'party_hp' in effect:
        for char in player.party:
            char['current_hp'] = min(char['hp'], char['current_hp'] + effect['party_hp'])
        print(f"❤️ 파티 전원 HP {effect['party_hp']} 회복!")
    if 'max_hp' in effect:
        for char in player.party:
            char['hp'] += effect['max_hp']
            char['current_hp'] += effect['max_hp']
        print(f"❤️ 최대 HP {effect['max_hp']} 증가!")
    if 'atk' in effect:
        for char in player.party: char['atk'] += effect['atk']
        print(f"⚔️ ATK {effect['atk']} 증가!")