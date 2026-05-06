# combat.py - 전투 진행 전체 담당 (턴 순서, 카드 사용, 몬스터 행동, 상태이상)
import time
import random
import assets
from assets import STATUS_INFO
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


def _init_statuses(entity):
    # statuses 키가 없으면 빈 딕셔너리로 초기화
    if 'statuses' not in entity:
        entity['statuses'] = {}


def get_effective_stat(entity, stat_name):
    # 버프/디버프 반영된 실제 수치 반환 - 피해 계산 전에 항상 이걸 거쳐야 함
    _init_statuses(entity)
    val = entity.get(stat_name, 0)

    if stat_name == 'atk':
        if entity['statuses'].get('atk_up', 0) > 0:
            val = int(val * 1.2)   # 공격 강화: +20%
        if entity['statuses'].get('weak', 0) > 0:
            val = int(val * 0.75)  # 약화: -25%

    return val


def _apply_def_up(dmg, defender):
    # 방어막이 있으면 받는 피해 30% 감소
    if defender.get('statuses', {}).get('def_up', 0) > 0:
        dmg = int(dmg * 0.7)
    return dmg


def _calc_dmg(attacker, defender, mult=1.0):
    # 최종 피해량 계산 순서: 공격력 → 방어막 → 취약
    atk = get_effective_stat(attacker, 'atk')
    raw = max(1, int(atk * mult))
    dmg = _apply_def_up(raw, defender)
    return _apply_vulnerable(dmg, defender)


def _apply_vulnerable(dmg, target):
    # 취약 상태면 받는 피해 50% 추가
    _init_statuses(target)
    if target['statuses'].get('vulnerable', 0) > 0:
        dmg = int(dmg * 1.5)
    return dmg


def process_turn_statuses(entity):
    # 턴 종료마다 호출 - 화상/중독 데미지 주고 지속시간 1 줄임
    # stun은 여기서 안 처리함 - 행동할 때 소비하는 방식이라 타이밍이 다름
    _init_statuses(entity)
    expired = []

    for status, turns in list(entity['statuses'].items()):
        if turns <= 0:
            expired.append(status)
            continue

        if status == 'stun':
            continue  # stun은 _monster_turn_logic에서 따로 처리

        if status == 'burn':
            dmg = 5
            entity['current_hp'] = max(0, entity['current_hp'] - dmg)
            console.print(f"  [bold red]불 화상! {entity['name']}이(가) {dmg}의 피해를 입었습니다.[/bold red]")

        elif status == 'poison':
            dmg = turns  # 중독 데미지 = 현재 스택 수 (스택 쌓을수록 초반이 강함)
            entity['current_hp'] = max(0, entity['current_hp'] - dmg)
            console.print(f"  [bold green]중독! {entity['name']}이(가) {dmg}의 피해를 입었습니다. (남은 스택: {turns - 1})[/bold green]")

        entity['statuses'][status] -= 1
        if entity['statuses'][status] <= 0:
            expired.append(status)

    for s in expired:
        del entity['statuses'][s]


def _status_display(entity):
    # 상태이상을 한글 이름으로 변환해서 화면에 보여줄 문자열 만들기
    parts = []
    for key, val in entity.get('statuses', {}).items():
        if val > 0:
            korean_name = STATUS_INFO.get(key, {}).get('name', key.upper())
            parts.append(f"[bold yellow]{korean_name}({val})[/bold yellow]")
    return " ".join(parts)


def _get_intent_text(monster, action):
    # 다음 턴 몬스터 행동을 플레이어한테 미리 보여주는 인텐트 텍스트
    base_dmg = get_effective_stat(monster, 'atk')
    intent_map = {
        'normal':            f"[red]일반 공격[/red]       (약 {base_dmg} 피해)",
        'power':             f"[bold red]강타[/bold red]           (약 {int(base_dmg * 1.5)} 피해)",
        'quick':             f"[yellow]속공 선제[/yellow]     (약 {int(base_dmg * 0.8)} 피해)",
        'dark_slash':        f"[magenta]암흑 베기[/magenta]    (약 {int(base_dmg * 2.0)} 피해)",
        'fire_aoe':          f"[red]광역 화염[/red]       (약 {int(base_dmg * 0.7)} 피해 x 전원)",
        'aoe':               f"[red]광역 공격[/red]       (약 {int(base_dmg * 1.1)} 피해 x 전원)",
        'poison_bite':       f"[green]독 이빨[/green]        (약 {int(base_dmg * 0.6)} 피해 + 중독 2스택)",
        'weaken_slash':      f"[yellow]약화 베기[/yellow]     (약 {int(base_dmg * 0.8)} 피해 + 약화 2턴)",
        'vulnerable_strike': f"[magenta]취약 강타[/magenta]    (약 {base_dmg} 피해 + 취약 2턴)",
        'poison_aoe':        f"[green]독 안개[/green]        (전원 약 {int(base_dmg * 0.4)} 피해 + 중독 2스택)",
    }
    return intent_map.get(action, "행동 준비 중")


def _energy_display(char):
    # 과충전(후방 충전 후 스왑으로 mp 초과) 상태면 노란색으로 강조
    cur = char['current_energy']
    mp  = char['mp']
    if cur > mp:
        return f"EN [bold yellow]{cur}[/bold yellow]/[dim]{mp}[/dim]  [yellow]과충전![/yellow]"
    return f"EN [cyan]{cur}/{mp}[/cyan]"


def _hp_bar(cur, max_hp, length=20):
    ratio = max(cur, 0) / max(max_hp, 1)
    color = "green" if ratio > 0.5 else "yellow" if ratio > 0.25 else "red"
    filled = int(ratio * length)
    return f"[{color}]{'█' * filled}[/{color}][dim]{'░' * (length - filled)}[/dim]"


def draw_combat_screen(player, monster, turn, intent=None):
    # 매 입력마다 화면 새로 그림 - intent는 몬스터 다음 행동 예고
    console.clear()
    console.print(Panel(
        f" 턴 {turn}  |  {player.gold}G  |  {player.current_floor}층",
        box=box.HORIZONTALS, style="dim white"
    ))

    m_table = Table.grid(padding=(0, 1))
    m_table.add_column(width=30)
    m_table.add_column()
    m_table.add_row(
        f"[bold red]{monster['name']}[/bold red]",
        f"{_hp_bar(monster['current_hp'], monster['hp'])} [white]{monster['current_hp']}/{monster['hp']}[/white]"
    )
    m_table.add_row(
        f"[dim]ATK {monster.get('atk','?')}  SPD {monster.get('spd','?')}[/dim]",
        ""
    )
    m_status = _status_display(monster)
    if m_status:
        m_table.add_row("", f"상태: {m_status}")
    if intent:
        m_table.add_row("", f"[dim]예고:[/dim] {intent}")
    console.print(Panel(m_table, title="[red]ENEMY[/red]", box=box.ROUNDED, style="red"))

    p_table = Table.grid(padding=(0, 2))
    p_table.add_column(width=12)
    p_table.add_column(width=15)
    p_table.add_column()
    p_table.add_column()

    for i, char in enumerate(player.party):
        mark    = "[bold green]전방[/bold green]" if i == player.active_index else "[dim]  후방[/dim]"
        buffs   = _status_display(char)
        name_line = f"[bold]{char['name']}[/bold]" + (f"\n{buffs}" if buffs else "")
        p_table.add_row(
            mark,
            name_line,
            f"{_hp_bar(char['current_hp'], char['hp'])} {char['current_hp']}/{char['hp']}",
            _energy_display(char)
        )
    console.print(Panel(p_table, title="[green]PARTY[/green]", box=box.ROUNDED, style="green"))


def _check_player_alive(player):
    # 전방 캐릭터 사망 시 후방으로 자동 스왑, 둘 다 죽으면 False
    if player.active_char['current_hp'] > 0:
        return True

    other_index = 1 - player.active_index
    if player.party[other_index]['current_hp'] > 0:
        dead_name = player.active_char['name']
        player.active_index = other_index
        console.print(
            f"\n[bold red]{dead_name} 전사![/bold red] "
            f"[yellow]{player.active_char['name']}(으)로 긴급 교체![/yellow]"
        )
        time.sleep(1.5)
        return True

    return False  # 파티 전멸


def run_combat(player, monster):
    turn = 1
    player.init_combat_decks()
    _init_statuses(monster)

    # 전투 시작 시 유물 효과 적용 (poison_start, burn_start)
    poison_stacks = sum(r.get('effect', {}).get('poison_start', 0) for r in player.relics)
    if poison_stacks > 0:
        monster['statuses']['poison'] = poison_stacks
        console.print(f"[bold green]중독 유물 발동! {monster['name']}에게 중독 {poison_stacks}스택![/bold green]")
        time.sleep(0.8)

    burn_turns = sum(r.get('effect', {}).get('burn_start', 0) for r in player.relics)
    if burn_turns > 0:
        monster['statuses']['burn'] = max(monster['statuses'].get('burn', 0), burn_turns)
        console.print(f"[bold red]화염 유물 발동! {monster['name']}에게 화상 {burn_turns}턴![/bold red]")
        time.sleep(0.8)

    pattern = monster.get('pattern', ['normal'])

    while True:
        active = player.active_char
        player.reset_energy()
        player.draw_cards(active, 4)

        # hp_drain 유물 (피의 서약 등) - 전방 캐릭터 HP 소모
        # max(1, ...) 로 HP가 0 이하로는 안 내려가게 막음
        total_drain = sum(r.get('effect', {}).get('hp_drain', 0) for r in player.relics)
        if total_drain > 0 and active['current_hp'] > 1:
            active['current_hp'] = max(1, active['current_hp'] - total_drain)
            drain_names = ", ".join(r['name'] for r in player.relics if r.get('effect', {}).get('hp_drain', 0) > 0)
            console.print(f"  [dim red]{drain_names} — {active['name']} HP -{total_drain}[/dim red]")
            time.sleep(0.4)

        # (turn - 1)로 보정하는 이유: turn이 1부터 시작해서 그냥 쓰면 pattern[0]을 건너뜀
        current_action = pattern[(turn - 1) % len(pattern)]
        next_action    = pattern[turn % len(pattern)]

        # 선공 결정: quick 패턴이면 무조건 몬스터 선공, 아니면 SPD 비교
        monster_first = False
        if current_action == "quick":
            monster_first = True
            priority_msg = "[bold yellow]경고! 적이 속공 기습을 준비합니다![/bold yellow]"
        elif monster.get('spd', 5) > active.get('spd', 10):
            monster_first = True
            priority_msg = f"[bold red]적이 더 빠릅니다! (적:{monster.get('spd','?')} vs 나:{active.get('spd','?')})[/bold red]"
        elif monster.get('spd', 5) == active.get('spd', 10):
            # [v6] 동점이면 플레이어 선공 (기존에 메시지가 틀렸어서 수정함)
            priority_msg = f"[bold white]속도가 같습니다! 선공 우선 (나:{active.get('spd','?')} vs 적:{monster.get('spd','?')})[/bold white]"
        else:
            priority_msg = f"[bold green]내가 더 빠릅니다! (나:{active.get('spd','?')} vs 적:{monster.get('spd','?')})[/bold green]"

        if monster_first:
            current_intent = _get_intent_text(monster, current_action)
            draw_combat_screen(player, monster, turn, current_intent)
            console.print(f"  {priority_msg}")
            prev_index = player.active_index
            _monster_turn_logic(monster, player.active_char, player, current_action)
            if not _check_player_alive(player):
                return False
            # [v6] 긴급 스왑이 발생하면 새 전방 캐릭터한테 카드 드로우
            # 이거 없으면 손패가 없어서 카드 사용 불가 상태가 됨
            if player.active_index != prev_index:
                player.draw_cards(player.active_char, 4)

            next_intent = _get_intent_text(monster, next_action)
            if not _player_turn_logic(player, monster, turn, next_intent):
                return True
        else:
            current_intent = _get_intent_text(monster, current_action)
            draw_combat_screen(player, monster, turn, current_intent)
            console.print(f"  {priority_msg}")
            if not _player_turn_logic(player, monster, turn, current_intent):
                return True

            _monster_turn_logic(monster, player.active_char, player, current_action)
            if not _check_player_alive(player):
                return False

        # 턴 종료: 화상/중독 데미지 처리
        # back을 먼저 저장 - 전방 사망 후 스왑이 일어나도 원래 후방 캐릭터를 처리
        back_char = player.party[1 - player.active_index]

        process_turn_statuses(player.active_char)
        if not _check_player_alive(player):
            return False

        # 후방 캐릭터 상태이상도 처리 (광역기로 걸린 화상/중독 등)
        # 후방이 상태이상으로 사망해도 전투는 계속 (힐로 부활 가능)
        process_turn_statuses(back_char)

        process_turn_statuses(monster)
        if monster['current_hp'] <= 0:
            _victory_sequence(player, monster)
            return True

        turn += 1
        time.sleep(1)


def _player_turn_logic(player, monster, turn, intent):
    # 플레이어 행동 루프 - 턴 종료 선택하거나 몬스터 죽을 때까지 반복
    # 스왑은 턴당 1회만 가능 (긴급 교대 카드로 하는 스왑은 예외)
    # 몬스터 죽으면 False 반환 → run_combat에서 전투 종료 처리

    swap_used = False

    while True:
        active = player.active_char
        draw_combat_screen(player, monster, turn, intent)

        energy = active['current_energy']
        other  = player.party[1 - player.active_index]
        other_alive = other['current_hp'] > 0

        if swap_used:
            swap_label = "[dim]2. 스왑 (이미 사용)[/dim]"
        elif not other_alive:
            swap_label = f"[dim]2. 스왑 ({other['name']} 전사)[/dim]"
        else:
            swap_label = "[bold cyan]2.[/bold cyan] 스왑"

        console.print(
            f"\n  [bold cyan]1.[/bold cyan] 카드 사용 [dim](EN {energy} 남음)[/dim]   "
            f"{swap_label}   "
            f"[bold cyan]3.[/bold cyan] 턴 종료\n"
        )
        cmd = console.input("  선택: ").strip()

        if cmd == '1':
            result = _handle_card_use(player, monster, active)
            if result == 'swap_free':
                # 긴급 교대 카드 - swap_used 소비 없이 스왑
                other = player.party[1 - player.active_index]
                if other['current_hp'] > 0:
                    player.swap()
                    new_active = player.active_char
                    player.draw_cards(new_active, 4)
                else:
                    console.print(f"  [red]교체할 수 있는 아군이 없습니다![/red]")
                    time.sleep(0.6)
            turn_over = False

        elif cmd == '2':
            if swap_used:
                console.print("  [red]이미 이번 턴에 스왑했습니다![/red]")
                time.sleep(0.6)
                turn_over = False
            elif not other_alive:
                console.print(f"  [red]{other['name']}은(는) 전사해서 스왑할 수 없습니다.[/red]")
                time.sleep(0.6)
                turn_over = False
            else:
                player.swap()
                new_active = player.active_char
                player.draw_cards(new_active, 4)
                console.print(f"  [cyan]{new_active['name']}(으)로 교체되었습니다![/cyan]")
                swap_used = True
                time.sleep(0.8)
                turn_over = False

        elif cmd == '3':
            turn_over = True

        else:
            turn_over = False

        if monster['current_hp'] <= 0:
            _victory_sequence(player, monster)
            return False

        if turn_over:
            break

    return True


def _handle_card_use(player, monster, active):
    # 카드 선택 UI - 선택하면 효과 적용. 'swap_free' 또는 None 반환
    if not active['hand']:
        remaining = len(active['draw_pile'])
        console.print(f"\n  [red]손패가 없습니다.[/red] [dim](드로우 파일 잔여: {remaining}장)[/dim]")
        time.sleep(0.8)
        return False

    console.print("\n  [cyan]현재 손패[/cyan]")
    for i, card_name in enumerate(active['hand'], 1):
        card = assets.CARDS.get(card_name, {})
        console.print(f"    {i}. [bold]{card_name}[/bold] (EN:{card['cost']}) - [dim]{card['description']}[/dim]")
    console.print("    0. 뒤로가기")

    try:
        idx = int(console.input("\n  사용할 카드 번호: ")) - 1
        if idx == -1:
            return False

        card_name = active['hand'][idx]
        card = assets.CARDS[card_name]

        if active['current_energy'] < card['cost']:
            console.print("  [red]에너지가 부족합니다![/red]")
            time.sleep(0.8)
            return False

        active['current_energy'] -= card['cost']
        active['discard_pile'].append(active['hand'].pop(idx))
        result = _execute_card_effects(card, active, player, monster)
        time.sleep(1.2)
        return result

    except (ValueError, IndexError):
        return False


def _execute_card_effects(card, active, player, monster):
    # 카드 효과 적용. swap_free 카드면 'swap_free' 문자열 반환, 아니면 None 반환
    console.print(f"\n  [bold cyan]'{card['name']}' 발동![/bold cyan]")
    effect = card.get('effect')
    dur_bonus = sum(r.get('effect', {}).get('duration_bonus', 0) for r in player.relics)

    if card.get('damage_mult', 0) > 0:
        dmg = _calc_dmg(active, monster, card['damage_mult'])
        if card['target'] == 'enemy_all':
            monster['current_hp'] -= dmg
            console.print(f"  [bold red]광역 폭발! {monster['name']}에게 {dmg}의 피해![/bold red]")
        else:
            monster['current_hp'] -= dmg
            console.print(f"  [bold red]{monster['name']}에게 {dmg}의 피해![/bold red]")

    if effect == 'atk_up':
        for c in player.party:
            _init_statuses(c)
            c['statuses']['atk_up'] = max(c['statuses'].get('atk_up', 0), 3)
        console.print("  [yellow]파티 전체 공격력 상승! (3턴)[/yellow]")

    elif effect == 'def_up':
        _init_statuses(active)
        active['statuses']['def_up'] = max(active['statuses'].get('def_up', 0), 3)
        console.print(f"  [blue]{active['name']}의 방어막! (3턴)[/blue]")

    elif effect == 'weak':
        _init_statuses(monster)
        monster['statuses']['weak'] = max(monster['statuses'].get('weak', 0), 2 + dur_bonus)
        console.print(f"  [yellow]{monster['name']} 약화! 공격력 25% 감소 ({2 + dur_bonus}턴)[/yellow]")

    elif effect == 'vulnerable':
        _init_statuses(monster)
        monster['statuses']['vulnerable'] = max(monster['statuses'].get('vulnerable', 0), 2 + dur_bonus)
        console.print(f"  [magenta]{monster['name']} 취약! 받는 피해 50% 증가 ({2 + dur_bonus}턴)[/magenta]")

    elif effect == 'poison':
        _init_statuses(monster)
        monster['statuses']['poison'] = monster['statuses'].get('poison', 0) + 3
        total = monster['statuses']['poison']
        console.print(f"  [bold green]{monster['name']}에게 중독 3스택! (총 {total}스택)[/bold green]")

    elif effect == 'burn':
        _init_statuses(monster)
        monster['statuses']['burn'] = max(monster['statuses'].get('burn', 0), 3 + dur_bonus)
        console.print(f"  [red]{monster['name']}에게 화상! ({3 + dur_bonus}턴)[/red]")

    elif effect == 'stun':
        if monster.get('is_boss', False):
            console.print(f"  [dim]{monster['name']}은(는) 기절에 면역입니다![/dim]")
        elif random.random() < 0.5:
            _init_statuses(monster)
            monster['statuses']['stun'] = max(monster['statuses'].get('stun', 0), 1)
            console.print(f"  [bold yellow]{monster['name']} 기절![/bold yellow]")
        else:
            console.print(f"  [bold yellow]{monster['name']}이(가) 기절을 버텼습니다![/bold yellow]")
            time.sleep(0.5)

    if card.get('heal', 0) > 0:
        heal_amt = card['heal']
        if card['target'] == 'ally':
            console.print("  누구를 치료할까요? [1] 전사  [2] 마법사")
            try:
                t_idx = int(console.input("  대상: ")) - 1
                target = player.party[t_idx]
            except (ValueError, IndexError):
                target = active
            target['current_hp'] = min(target['hp'], target['current_hp'] + heal_amt)
            console.print(f"  [green]{target['name']}의 체력 {heal_amt} 회복![/green]")

    if effect == 'mp_restore':
        restore = random.randint(2, 3)
        active['current_energy'] += restore
        console.print(f"  [cyan]{active['name']} 에너지 +{restore}! (현재: {active['current_energy']})[/cyan]")

    elif effect == 'draw2':
        drawn = player.draw_cards_add(active, 2)
        console.print(f"  [cyan]{active['name']} — 카드 {drawn}장 추가 드로우![/cyan]")

    elif effect == 'cleanse':
        NEGATIVE = {'burn', 'poison', 'stun', 'vulnerable', 'weak'}
        alive = [c for c in player.party if c['current_hp'] > 0]
        if len(alive) == 1:
            target = alive[0]
        else:
            console.print(f"  해독 대상: [1] {player.party[0]['name']}  [2] {player.party[1]['name']}")
            try:
                t_idx = int(console.input("  대상: ")) - 1
                target = player.party[t_idx] if player.party[t_idx]['current_hp'] > 0 else alive[0]
            except (ValueError, IndexError):
                target = active
        neg = {k: v for k, v in target.get('statuses', {}).items() if k in NEGATIVE and v > 0}
        if not neg:
            console.print(f"  [dim]{target['name']}에게 제거할 상태이상이 없습니다.[/dim]")
        else:
            worst = max(neg, key=neg.get)
            del target['statuses'][worst]
            korean = STATUS_INFO.get(worst, {}).get('name', worst)
            console.print(f"  [green]{target['name']}의 {korean} 해제![/green]")

    elif effect == 'swap_free':
        return 'swap_free'

    return None


def _monster_turn_logic(monster, active, player, action):
    # 기절 상태면 행동 스킵하고 기절 1 소비
    # 기절을 턴 종료 틱다운이 아닌 행동 시 소비하는 이유:
    # "기절 걸었는데 다음 턴에 바로 공격함" 같은 타이밍 버그 방지
    _init_statuses(monster)

    if monster['statuses'].get('stun', 0) > 0:
        console.print(f"\n  [bold yellow]{monster['name']}은(는) 기절해 움직이지 못합니다![/bold yellow]")
        monster['statuses']['stun'] -= 1
        if monster['statuses']['stun'] <= 0:
            del monster['statuses']['stun']
        return

    if action == "poison_bite":
        dmg = _calc_dmg(monster, active, 0.6)
        active['current_hp'] -= dmg
        _init_statuses(active)
        active['statuses']['poison'] = active['statuses'].get('poison', 0) + 2
        console.print(f"\n  [bold green]{monster['name']}의 독 이빨![/bold green]")
        console.print(f"  [red]{active['name']}에게 {dmg} 피해![/red] [green]중독 2스택![/green]")
        time.sleep(1.2)
        return

    if action == "weaken_slash":
        dmg = _calc_dmg(monster, active, 0.8)
        active['current_hp'] -= dmg
        _init_statuses(active)
        active['statuses']['weak'] = max(active['statuses'].get('weak', 0), 2)
        console.print(f"\n  [bold yellow]{monster['name']}의 약화 베기![/bold yellow]")
        console.print(f"  [red]{active['name']}에게 {dmg} 피해![/red] [yellow]약화 2턴![/yellow]")
        time.sleep(1.2)
        return

    if action == "vulnerable_strike":
        dmg = _calc_dmg(monster, active, 1.0)
        active['current_hp'] -= dmg
        _init_statuses(active)
        active['statuses']['vulnerable'] = max(active['statuses'].get('vulnerable', 0), 2)
        console.print(f"\n  [bold magenta]{monster['name']}의 취약 강타![/bold magenta]")
        console.print(f"  [red]{active['name']}에게 {dmg} 피해![/red] [magenta]취약 2턴![/magenta]")
        time.sleep(1.2)
        return

    if action == "poison_aoe":
        console.print(f"\n  [bold green]{monster['name']}의 독 안개![/bold green]")
        for c in player.party:
            dmg = _calc_dmg(monster, c, 0.4)
            c['current_hp'] -= dmg
            _init_statuses(c)
            c['statuses']['poison'] = c['statuses'].get('poison', 0) + 2
            console.print(f"    {c['name']}에게 {dmg} 피해! [green]중독 2스택[/green]")
        time.sleep(1.2)
        return

    if action == "fire_aoe":
        console.print(f"\n  [bold red]{monster['name']}의 광역 화염![/bold red]")
        for c in player.party:
            dmg = _calc_dmg(monster, c, 0.7)
            c['current_hp'] -= dmg
            console.print(f"    {c['name']}에게 {dmg} 피해!")
        time.sleep(1.2)
        return

    if action == "aoe":
        console.print(f"\n  [bold red]{monster['name']}의 광역 공격![/bold red]")
        for c in player.party:
            dmg = _calc_dmg(monster, c, 1.1)
            c['current_hp'] -= dmg
            console.print(f"    {c['name']}에게 {dmg} 피해!")
        time.sleep(1.2)
        return

    mult_map = {
        "quick":      (0.8, f"[bold yellow]속공! {monster['name']}이 번개처럼 달려듭니다![/bold yellow]"),
        "power":      (1.5, f"[bold red]{monster['name']}의 강력한 강타![/bold red]"),
        "dark_slash": (2.0, f"[bold magenta]{monster['name']}의 암흑 베기![/bold magenta]"),
        "normal":     (1.0, f"[bold red]{monster['name']}의 공격![/bold red]"),
    }
    mult, msg = mult_map.get(action, mult_map["normal"])

    dmg = _calc_dmg(monster, active, mult)
    console.print(f"\n  {msg}")
    active['current_hp'] -= dmg
    console.print(f"  [red]{active['name']}에게 {dmg} 피해![/red]")
    time.sleep(1.2)


def _victory_sequence(player, monster):
    # [v6] 최소 20G 보장 (기존엔 15G×0.8=12G까지 내려갔음)
    console.clear()
    base = monster.get('reward_gold', 20)
    gold = max(20, random.randint(int(base * 0.8), int(base * 1.2)))
    player.gold += gold
    console.print(Panel(
        f"[bold green]승리! {monster['name']}을(를) 물리쳤습니다![/bold green]\n"
        f"획득: [yellow]+{gold}G[/yellow]   보유: [yellow]{player.gold}G[/yellow]",
        box=box.DOUBLE
    ))
    time.sleep(1.5)
    _card_reward_event(player)


def _card_reward_event(player):
    # [v6] 전방 캐릭터 고정에서 생존 캐릭터 중 랜덤으로 변경
    alive = [c for c in player.party if c['current_hp'] > 0]
    char = random.choice(alive)
    class_cards = [k for k, v in assets.CARDS.items() if v['class'] == char['name']]
    choices = random.sample(class_cards, min(3, len(class_cards)))

    console.print(f"\n[bold yellow]새로운 기술을 발견했습니다! ({char['name']})[/bold yellow]\n")
    for i, card_name in enumerate(choices, 1):
        card = assets.CARDS[card_name]
        console.print(f"  {i}. [cyan]{card['name']}[/] (EN:{card['cost']}) - {card['description']}")
    console.print("  0. 스킵")

    while True:
        cmd = console.input("\n번호 선택: ").strip()
        if cmd == '0':
            break
        if cmd in [str(j) for j in range(1, len(choices) + 1)]:
            new_card = choices[int(cmd) - 1]

            if len(char['deck']) >= 15:
                console.print("\n[red]덱이 꽉 찼습니다 (최대 15장). 버릴 카드를 선택하세요:[/red]")
                for idx, name in enumerate(char['deck'], 1):
                    console.print(f"  {idx}. {name}")
                try:
                    drop = int(console.input("번호: ")) - 1
                    char['deck'].pop(drop)
                except (ValueError, IndexError):
                    continue

            char['deck'].append(new_card)
            console.print(f"[bold green]'{new_card}' 카드가 덱에 추가되었습니다![/bold green]")
            break

    time.sleep(1)
