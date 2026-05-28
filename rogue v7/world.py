# world.py - 층 이벤트 결정, 상점, 랜덤 사건 처리
import random
import assets
import time
import combat
import visuals
import ai_manager
from rich.console import Console
from rich.panel import Panel
from rich import box

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

    # choose monster safely with fallbacks and warnings
    if floor in [15, 30]:
        try:
            monster = assets.get_boss(floor)
        except Exception as e:
            console.print(f"[bold red]경고:[/bold red] 보스 데이터를 불러오는 중 오류 발생: {e}")
            monster = {"name": f"보스_오류_{floor}", "hp": 30, "atk": 5, "spd": 5, "pattern": ["normal"]}
    else:
        m_names = assets.get_stage_monsters(stage)
        if not m_names:
            console.print(f"[bold yellow]경고: 해당 스테이지({stage})에 등록된 몬스터가 없습니다. 기본 몬스터로 대체합니다.[/bold yellow]")
            # fallback to all monsters
            try:
                m_names = list(assets.MONSTERS.keys())
            except Exception:
                m_names = ["고블린"]
        try:
            chosen = random.choice(m_names)
            monster = assets.get_monster(chosen, floor)
        except Exception as e:
            console.print(f"[bold red]경고:[/bold red] 몬스터 생성 중 오류 발생: {e}")
            monster = {"name": "몬스터_오류", "hp": 30, "atk": 5, "spd": 5, "pattern": ["normal"]}

    # ensure monster hp field exists
    if 'hp' not in monster:
        console.print(f"[bold yellow]경고: 몬스터 데이터에 HP 정보가 없습니다. hp=30으로 초기화합니다.[/bold yellow]")
        monster['hp'] = 30
    monster['current_hp'] = monster.get('current_hp', monster['hp'])

    # 등장 연출 — Rule 구분선으로 시작
    console.print()
    console.rule(f"[bold red] ⚔  {monster['name']} 등장  ⚔ [/bold red]", style="dim red")
    console.print()

    # 몬스터 대사 — 말풍선 Panel
    if monster.get('speech'):
        console.print(Panel(
            f'[italic yellow]  "{monster["speech"]}"[/italic yellow]',
            border_style="dim yellow",
            box=box.ROUNDED,
            padding=(0, 1)
        ))
        console.print()

    # AI 내레이션 — 구분된 서술 Panel
    try:
        if floor in [15, 30]:
            intro = ai_manager.get_boss_narrative(monster['name'], stage)
        else:
            intro = ai_manager.get_battle_intro(monster['name'], stage)
        console.print(Panel(
            "",
            title="[bold bright_blue]전투 상황[/bold bright_blue]",
            border_style="bright_blue",
            box=box.MINIMAL,
            padding=(1, 1)
        ))
        visuals.print_typing_text(intro, delay=0.06, style="bright_cyan")
    except Exception as e:
        console.print(f"[bold yellow]내레이션 생성 중 오류: {e} — 계속 진행합니다.[/bold yellow]")
    time.sleep(0.5)


    # Validate player decks to prevent init_combat_decks crashing
    for c in player.party:
        if 'deck' not in c or not c['deck']:
            console.print(f"[bold yellow]경고: {c.get('name','캐릭터')}의 덱이 비어있거나 존재하지 않습니다. 기본 카드로 채웁니다.[/bold yellow]")
            try:
                c['deck'] = list(assets.CARDS.keys())[:8]
            except Exception:
                c['deck'] = ["강타", "강타", "강타"]

    try:
        result = combat.run_combat(player, monster)
    except Exception as e:
        # On error, show warning and continue (assume victory to keep demo flow)
        console.print(Panel(f"[bold red]전투 실행 중 오류 발생:[/bold red]\n{e}\n\n[dim]전투가 정상적으로 진행되지 않았습니다. 경고를 출력하고 전투를 자동으로 종료합니다.[/dim]", title="경고", style="red"))
        console.print("[bold yellow]경고: 전투 오류로 인해 몬스터를 자동으로 처치합니다.[/bold yellow]")
        try:
            # best-effort: apply rewards if possible
            player.heal_party(0)
        except Exception:
            pass
        result = True

    if result and floor in [15, 30]:
        try:
            player.heal_party(30)
            console.print(f"\n[bold green]✨ 보스 처치 보상! 파티 전원 HP 30 회복![/bold green]")
            time.sleep(1.2)
        except Exception:
            pass

    return result


def handle_shop(player, floor):
    visuals.clear_screen()
    stage = assets.get_stage_by_floor(floor)
    # 구매/획득 이력 전체 제외 - 합성으로 소모된 유물도 다시 안 나옴
    shop_relics = assets.get_stage_relics(stage, count=3, exclude=player.purchased_relics)
    try:
        shop_narrative = ai_manager.get_shop_narrative(stage)
        console.print(Panel(
            "",
            title="[bold bright_green]상점 입장[/bold bright_green]",
            border_style="bright_green",
            box=box.MINIMAL,
            padding=(1, 1)
        ))
        visuals.print_typing_text(shop_narrative, delay=0.06, style="bright_green")
        console.print()
    except Exception as e:
        console.print(f"[bold yellow]상점 내레이션 생성 중 오류: {e} — 계속 진행합니다.[/bold yellow]")

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
        console.print("  0. 떠나기   [dim][R] 조합 사전[/dim]")

        choice = console.input("\n선택: ").strip()
        if choice == '0': break
        if choice.lower() == 'r':
            player.show_synthesis_book()
            visuals.clear_screen()
            continue
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
                console.print("\n[bold bright_cyan]▸ 상황이 전개됩니다...[/bold bright_cyan]")
                visuals.print_typing_text(narrative, delay=0.06, style="bright_cyan")
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
