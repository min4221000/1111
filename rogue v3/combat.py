# combat.py
import time
import random
import assets
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

# ── 간소화된 상태이상 관리 ──
def _init_statuses(entity):
    if 'statuses' not in entity: entity['statuses'] = {}

def get_effective_stat(entity, stat_name):
    _init_statuses(entity)
    val = entity.get(stat_name, 0)
    if stat_name == 'atk' and entity['statuses'].get('atk_up', 0) > 0: val = int(val * 1.2)
    elif stat_name == 'defense' and entity['statuses'].get('def_up', 0) > 0: val += 5
    return val

def process_turn_statuses(entity):
    _init_statuses(entity)
    expired = []
    for status, turns in entity['statuses'].items():
        if turns > 0:
            if status == 'burn':
                dmg = 5
                entity['current_hp'] = max(0, entity['current_hp'] - dmg)
                console.print(f"  [bold red]🔥 화상! {entity['name']}이(가) {dmg} 피해를 입었습니다.[/bold red]")
            entity['statuses'][status] -= 1
            if entity['statuses'][status] <= 0: expired.append(status)
    for s in expired: del entity['statuses'][s]

def _hp_bar(cur, max_hp, length=16):
    ratio = max(cur, 0) / max(max_hp, 1)
    color = "green" if ratio > 0.5 else "yellow" if ratio > 0.25 else "red"
    filled = int(ratio * length)
    return f"[{color}]{'█' * filled}[/{color}][dim]{'░' * (length - filled)}[/dim]"

def draw_combat_screen(player, monster, turn):
    console.clear()
    console.print(Panel(f" ⏱ {turn}턴  │  💰 {player.gold}G", box=box.HORIZONTALS, style="dim white"))
    
    # 적 패널
    m_table = Table.grid(padding=(0, 1)); m_table.add_column(width=28); m_table.add_column()
    m_table.add_row(f"[bold red]👾 {monster['name']}[/bold red]", f"{_hp_bar(monster['current_hp'], monster['hp'])} [white]{monster['current_hp']}/{monster['hp']}[/white]")
    status_str = " ".join([f"[{k}]" for k, v in monster.get('statuses', {}).items() if v > 0])
    if status_str: m_table.add_row("", f"[red]{status_str}[/red]")
    console.print(Panel(m_table, title="[red]ENEMY[/red]", box=box.ROUNDED, style="red"))

    # 파티 패널
    p_table = Table.grid(padding=(0, 1)); p_table.add_column(width=10); p_table.add_column(width=10); p_table.add_column(); p_table.add_column()
    for i, char in enumerate(player.party):
        mark = "[bold green]▶ 전방[/bold green]" if i == player.active_index else "[dim]  후방[/dim]"
        c_status = " ".join([f"[{k}]" for k, v in char.get('statuses', {}).items() if v > 0])
        p_table.add_row(mark, f"[bold]{char['name']}[/bold]\n[dim]{c_status}[/dim]", f"{_hp_bar(char['current_hp'], char['hp'])} {char['current_hp']}/{char['hp']}", f"EN: [cyan]{char['current_energy']}/{char['mp']}[/cyan]")
    console.print(Panel(p_table, title="[green]PARTY[/green]", box=box.ROUNDED, style="green"))

def _use_card(card, active, player, monster):
    console.print(f"\n  [cyan]🃏 '{card['name']}' 사용![/cyan]")
    effect = card.get('effect')
    _init_statuses(active); _init_statuses(monster)
    
    # 힐 처리 (파티원 선택)
    heal_amt = card.get('heal', 0)
    if heal_amt > 0:
        if card['target'] == 'ally':
            console.print("  누구에게 사용하시겠습니까? 1.전사  2.마법사")
            t_idx = 0
            while True:
                try: 
                    t_idx = int(console.input("  대상 번호: ")) - 1
                    if t_idx in [0, 1]: break
                except: pass
            target = player.party[t_idx]
            target['current_hp'] = min(target['hp'], target['current_hp'] + heal_amt)
            console.print(f"  [green]❤️ {target['name']}의 체력 {heal_amt} 회복![/green]")

    # 버프 처리
    if effect == 'atk_up':
        for c in player.party:
            _init_statuses(c); c['statuses']['atk_up'] = 3
        console.print("  [yellow]💪 파티 공격력 증가! (3턴)[/yellow]")
    if effect == 'def_up':
        active['statuses']['def_up'] = 3
        console.print("  [blue]🛡️ 방어력 증가! (3턴)[/blue]")

    # 공격 처리
    dmg_mult = card.get('damage_mult', 0)
    if dmg_mult > 0:
        base_atk = get_effective_stat(active, 'atk')
        dmg = max(1, int(base_atk * float(dmg_mult)) - get_effective_stat(monster, 'defense'))
        
        if card['target'] == 'enemy_all':
            monster['current_hp'] -= dmg
            console.print(f"  [bold red]⚔️ 광역! {monster['name']}에게 {dmg} 피해![/bold red]")
        else:
            monster['current_hp'] -= dmg
            console.print(f"  [bold red]⚔️ {monster['name']}에게 {dmg} 피해![/bold red]")

        if effect == 'burn':
            monster['statuses']['burn'] = 3
            console.print(f"  [red]🔥 {monster['name']}에게 화상 부여! (3턴)[/red]")
        elif effect == 'stun':
            monster['statuses']['stun'] = 1
            console.print(f"  [bold yellow]⚡ {monster['name']} 기절! (1턴)[/bold yellow]")

def run_combat(player, monster):
    turn = 1; is_new_turn = True
    player.init_combat_decks()
    _init_statuses(monster)

    while True:
        active = player.active_char
        if is_new_turn:
            player.apply_natural_regen()
            player.draw_cards(active, 4)
            is_new_turn = False

        draw_combat_screen(player, monster, turn)
        console.print("\n  [bold cyan]1.[/bold cyan] 평타   [bold cyan]2.[/bold cyan] 덱 사용   [bold cyan]3.[/bold cyan] 스왑\n")
        cmd = console.input("  선택: ").strip()

        if cmd == '1':
            dmg = max(1, get_effective_stat(active, 'atk') - get_effective_stat(monster, 'defense'))
            monster['current_hp'] -= dmg
            for c in player.party: c['current_energy'] = min(c['mp'], c['current_energy'] + 1)
            console.print(f"\n  [red]⚔  평타! {dmg} 피해! (파티 EN 1 회복)[/red]")
            time.sleep(1)
        
        elif cmd == '2':
            console.print("\n  [cyan]🃏 내 패 (Hand)[/cyan]")
            for i, c_name in enumerate(active['hand'], 1):
                temp_card = assets.CARDS.get(c_name, {})
                console.print(f"    {i}. {c_name} (EN: {temp_card.get('cost', 1)})")
            console.print("    0. 뒤로가기")
            try:
                c = int(console.input("\n  사용할 카드: "))
                if c == 0: continue
                if 1 <= c <= len(active['hand']):
                    card_name = active['hand'][c - 1]
                    card = assets.CARDS[card_name]
                    if active['current_energy'] < card['cost']:
                        console.print("  [red]❌ EN 부족![/red]"); time.sleep(0.8); continue
                    
                    active['current_energy'] -= card['cost']
                    active['discard_pile'].append(active['hand'].pop(c - 1))
                    _use_card(card, active, player, monster)
                    time.sleep(1.2)
            except: continue
        elif cmd == '3':
            player.swap(); active = player.active_char; player.draw_cards(active, 4); time.sleep(0.6)
        else: continue

        # 전투 승리 체크
        if monster['current_hp'] <= 0:
            console.clear()
            player.gold += monster.get('reward_gold', 10)
            console.print(f"[bold green]🎉 승리! {monster.get('reward_gold', 10)}G 획득![/bold green]")
            time.sleep(1.5)
            _card_reward_event(player)
            return True

        # 몬스터 턴
        if monster['statuses'].get('stun', 0) > 0:
            console.print(f"\n  [bold yellow]⚡ {monster['name']}은(는) 기절해서 행동하지 못합니다![/bold yellow]")
            monster['statuses']['stun'] -= 1
        else:
            base_dmg = max(5, monster.get('atk', 10))
            pattern = monster.get('pattern', ['normal'])
            act = pattern[turn % len(pattern)]
            
            if act == 'aoe' or act == 'fire_aoe':
                console.print(f"\n  [bold red]👾 {monster['name']}의 광역 공격![/bold red]")
                for c in player.party:
                    dmg = max(1, int(base_dmg * 1.2) - get_effective_stat(c, 'defense'))
                    c['current_hp'] = max(0, c['current_hp'] - dmg)
                    console.print(f"   [red]{c['name']}에게 {dmg} 피해![/red]")
            elif act == 'power':
                dmg = max(1, int(base_dmg * 1.5) - get_effective_stat(active, 'defense'))
                active['current_hp'] = max(0, active['current_hp'] - dmg)
                console.print(f"\n  [bold red]👾 {monster['name']}의 강타! {active['name']}에게 {dmg} 피해![/bold red]")
            else:
                dmg = max(1, base_dmg - get_effective_stat(active, 'defense'))
                active['current_hp'] = max(0, active['current_hp'] - dmg)
                console.print(f"\n  [bold red]👾 {monster['name']}의 공격! {active['name']}에게 {dmg} 피해![/bold red]")
        time.sleep(1.2)

        if not [c for c in player.party if c['current_hp'] > 0]: return False
        process_turn_statuses(active); process_turn_statuses(monster)
        turn += 1; is_new_turn = True

def _card_reward_event(player):
    console.clear()
    char = player.active_char
    # 직업에 맞는 카드만 보상으로 등장
    class_cards = [k for k, v in assets.CARDS.items() if v['class'] == char['name']]
    choices = random.sample(class_cards, min(3, len(class_cards)))
    
    console.print(f"\n[bold yellow]🎁 전리품: {char['name']}의 덱에 추가할 카드를 고르세요![/bold yellow]\n")
    for i, c_name in enumerate(choices, 1):
        card = assets.CARDS[c_name]
        console.print(f"  {i}. [cyan]{card['name']}[/] (EN: {card['cost']}) - {card['description']}")
    console.print("  0. 스킵")
    
    while True:
        cmd = console.input("\n  선택: ")
        if cmd == '0': break
        elif cmd in ['1', '2', '3']:
            new_card = choices[int(cmd)-1]
            if len(char['deck']) >= 15: # 15장 제한 압축 로직
                console.print(f"\n[red]⚠️ 덱이 꽉 찼습니다! (최대 15장)[/red]")
                for i, c in enumerate(char['deck'], 1): console.print(f"  {i}. {c}")
                try:
                    drop = int(console.input("버릴 카드의 번호: ")) - 1
                    if 0 <= drop < 15: char['deck'].pop(drop)
                    else: continue
                except: continue
            char['deck'].append(new_card)
            console.print(f"[bold green]✨ '{new_card}' 획득![/bold green]")
            break
    time.sleep(1.5)