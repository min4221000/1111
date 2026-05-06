# world.py - 층 이벤트 결정, 상점, 랜덤 사건 처리
import random
import assets
import time
import combat
import visuals
import ai_manager
from rich.console import Console

console = Console()

# 마지막 상점이 몇 층이었는지 추적 (상점 간격 최소 3층 유지용)
last_shop_floor = 1


def generate_floor_event(floor):
    global last_shop_floor
    if floor == 1:
        return "shop"               # 1층은 항상 상점으로 시작
    if floor in [15, 30]:
        return "boss"
    if floor in [14, 16, 29]:      # 보스 전후 확정 상점
        last_shop_floor = floor
        return "shop"

    # 최소 3층 이상 지나야 상점 등장 가능 (연속 상점 방지)
    gap = floor - last_shop_floor
    if gap >= 3 and random.random() < 0.23:
        last_shop_floor = floor
        return "shop"

    return "combat" if random.random() < 0.75 else "event"


def handle_combat(player, floor):
    stage = assets.get_stage_by_floor(floor)
    if floor in [15, 30]:
        monster = assets.get_boss(floor)
    else:
        m_names = assets.get_stage_monsters(stage)
        monster = assets.get_monster(random.choice(m_names), floor)

    monster['current_hp'] = monster['hp']
    console.print(f"\n[bold red]🌑 야생의 {monster['name']}이(가) 나타났다![/bold red]")

    # [v6] 몬스터 개별 대사 출력 (assets.py에 speech 필드로 정의됨)
    if monster.get('speech'):
        console.print(f'  [italic dim]"{monster["speech"]}"[/italic dim]')

    # [v6] AI 내레이션 (API 없으면 fallback 대사 자동 출력)
    intro = ai_manager.get_battle_intro(monster['name'], stage)
    console.print(f"  [dim cyan]{intro}[/dim cyan]")
    time.sleep(1.5)

    result = combat.run_combat(player, monster)

    if result and floor in [15, 30]:
        player.heal_party(30)
        console.print(f"\n[bold green]✨ 보스 처치 보상! 파티 전원 HP 30 회복![/bold green]")
        time.sleep(1.2)

    return result


def handle_shop(player, floor):
    visuals.clear_screen()
    stage = assets.get_stage_by_floor(floor)
    # 구매/획득 이력 전체 제외 - 합성으로 소모된 유물도 다시 안 나옴
    shop_relics = assets.get_stage_relics(stage, count=3, exclude=player.purchased_relics)

    while True:
        console.print(f"🛒 [bold yellow][암시장 상점][/bold yellow] (보유: [yellow]{player.gold}G[/yellow])\n")

        # [v6] 파티 HP와 유물 현황 표시
        for c in player.party:
            hp_color = "red" if c['current_hp'] < c['hp'] * 0.25 else "yellow" if c['current_hp'] < c['hp'] * 0.5 else "green"
            status = "[dim]사망[/dim]" if c['current_hp'] <= 0 else f"[{hp_color}]{c['current_hp']}/{c['hp']} HP[/{hp_color}]"
            console.print(f"  {c['name']}: {status}")
        if player.relics:
            relic_line = "  💍 유물: " + " / ".join(f"[magenta]{r['name']}[/magenta]" for r in player.relics)
            console.print(relic_line)
        else:
            console.print("  💍 유물: [dim]없음[/dim]")
        console.print()

        idx = 1
        if shop_relics:
            for r in shop_relics:
                price = r.get('price', 80)
                desc = r.get('desc', "효과가 비밀에 싸여있습니다.")
                console.print(f"  {idx}. [bold magenta]💍 {r['name']}[/bold magenta] ([yellow]{price}G[/yellow])")
                console.print(f"     [dim italic]ㄴ 효과: {desc}[/dim italic]")
                idx += 1
        else:
            # [v6] 다 팔리면 매진 표시
            console.print("  [bold red]⚠️  매진! 모든 상품이 소진되었습니다.[/bold red]\n")

        console.print(f"  {idx}. ❤️ [bold red]파티 전원 HP 40 회복[/bold red] (40G)")
        console.print("  0. 떠나기")

        choice = console.input("\n선택: ").strip()
        if choice == '0': break
        try:
            c_idx = int(choice)
            if shop_relics and 1 <= c_idx < idx:
                selected = shop_relics[c_idx - 1]
                if player.gold >= selected['price']:
                    if player.add_relic(selected):
                        player.gold -= selected['price']
                        shop_relics.pop(c_idx - 1)
                        console.print(f"[bold green]✔ {selected['name']} 구매 완료![/]")
                else:
                    console.print("[red]골드가 부족합니다![/]")
            elif c_idx == idx:
                if player.gold >= 40:
                    player.gold -= 40
                    player.heal_party(40)
                    console.print("[bold green]❤️ 체력이 회복되었습니다![/]")
                else:
                    console.print("[red]골드가 부족합니다![/]")
        except ValueError:
            pass
        time.sleep(1.2)
        visuals.clear_screen()


def handle_random_event(player, floor):
    visuals.clear_screen()
    stage = assets.get_stage_by_floor(floor)
    event = assets.get_random_event()
    console.print(f"🌀 [bold cyan][사건 발생] {event['name']}[/bold cyan]  [yellow]{player.gold}G[/yellow]")
    console.print(f"📜 {event['description']}\n")
    for i, opt in enumerate(event['choices'], 1):
        console.print(f"  {i}. {opt['text']}")

    while True:
        try:
            res = console.input("\n선택: ").strip()
            idx = int(res) - 1
            if 0 <= idx < len(event['choices']):
                sel = event['choices'][idx]
                console.print(f"\n✨ {sel.get('result_text', '결과가 나타납니다.')}")
                _apply_effect(player, sel['effect'])
                # [v6] AI 사건 결과 묘사
                narrative = ai_manager.get_event_narrative(
                    event['name'], sel['text'], sel.get('result_text', ''), stage
                )
                console.print(f"  [dim cyan]{narrative}[/dim cyan]")
                break
        except ValueError:
            pass
    time.sleep(2)


def _apply_effect(player, effect):
    # elif가 아닌 if를 연속으로 쓰는 이유:
    # 하나의 effect 딕셔너리에 여러 키가 동시에 있을 수 있음
    # 예: {"party_hp": -10, "give_card": "마나 회복"}
    # elif로 쓰면 두 번째 효과가 무시됨

    if 'gold' in effect:
        # 골드는 chance 무관하게 항상 지급 (함정 여부와 독립)
        player.gold = max(0, player.gold + effect['gold'])

    if 'party_hp' in effect:
        # chance는 party_hp(함정)에만 적용
        chance = effect.get('chance', 1.0)
        if random.random() < chance:
            hp_val = effect['party_hp']
            for c in player.party:
                c['current_hp'] = max(0, min(c['hp'], c['current_hp'] + hp_val))
            if hp_val < 0:
                console.print(f"[bold red]함정 발동! 파티 전원 HP {hp_val}![/bold red]")
        else:
            console.print("[green]다행히 함정은 없었습니다.[/green]")

    if 'party_atk' in effect:
        val = effect['party_atk']
        for c in player.party:
            c['atk'] = max(1, c['atk'] + val)
        sign = f"+{val}" if val > 0 else str(val)
        console.print(f"[yellow]파티 ATK {sign} (영구)[/yellow]")

    if 'gamble' in effect:
        g   = effect['gamble']
        bet = g.get('bet', 0)
        if player.gold < bet:
            console.print("[red]골드가 부족합니다![/red]")
        else:
            player.gold -= bet
            if random.random() < g.get('win_chance', 0.5):
                win_gold = int(bet * g.get('win_mult', 2))
                player.gold += win_gold
                console.print(f"[bold green]당첨! +{win_gold}G 획득! (보유: {player.gold}G)[/bold green]")
                if 'win_bonus' in g:
                    _apply_effect(player, g['win_bonus'])
            else:
                console.print(f"[bold red]꽝! {bet}G를 잃었습니다. (보유: {player.gold}G)[/bold red]")

    if 'gamble_stat' in effect:
        g = effect['gamble_stat']
        if random.random() < g.get('win_chance', 0.5):
            console.print("[bold green]행운이 따릅니다![/bold green]")
            _apply_effect(player, g.get('win_effect', {}))
        else:
            console.print("[bold red]불운이 찾아왔습니다![/bold red]")
            _apply_effect(player, g.get('lose_effect', {}))

    if 'give_card' in effect:
        card_name = effect['give_card']
        card = assets.CARDS.get(card_name)
        if not card:
            return
        console.print(f"\n[bold yellow]'{card_name}' 카드를 획득했습니다![/bold yellow]")
        console.print(f"[dim]{card['description']}[/dim]")
        console.print("  누구의 덱에 추가할까요?")
        for i, c in enumerate(player.party, 1):
            console.print(f"  {i}. {c['name']} (현재 {len(c['deck'])}장)")
        try:
            t_idx = int(console.input("선택: ").strip()) - 1
            target = player.party[t_idx]
        except (ValueError, IndexError):
            target = player.party[0]

        if len(target['deck']) >= 15:
            console.print(f"\n[red]{target['name']}의 덱이 꽉 찼습니다. 버릴 카드를 선택하세요:[/red]")
            for i, name in enumerate(target['deck'], 1):
                console.print(f"  {i}. {name}")
            try:
                drop = int(console.input("번호: ").strip()) - 1
                target['deck'].pop(drop)
            except (ValueError, IndexError):
                pass

        target['deck'].append(card_name)
        console.print(f"[bold green]{target['name']}의 덱에 '{card_name}' 추가 완료![/bold green]")
