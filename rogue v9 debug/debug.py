# debug.py - 치트/디버그/테스트 실행기
# 상점, 랜덤 사건, 보스, 랜덤 전투방을 원하는 층에서 바로 띄워봄
# 실제 main.py 루프는 안 돔, 이벤트 단발 실행 + 내레이션 포함
import assets
import world
import visuals
import ai_manager
from player import Player
from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()


def setup_player(floor, gold, cheat_stats):
    # 테스트용 플레이어 셋업, 골드/스탯/층 자유롭게 조정
    p = Player()
    p.current_floor = floor
    p.gold = gold
    if cheat_stats:
        for c in p.party:
            c['hp'] += 200
            c['current_hp'] = c['hp']
            c['atk'] += 50
            c['mp'] += 5
    return p


def pick_floor(default=1):
    raw = console.input(f"\n층 번호 입력 (1~30, Enter=기본 {default}): ").strip()
    if not raw:
        return default
    try:
        f = int(raw)
        if 1 <= f <= 30:
            return f
    except ValueError:
        pass
    console.print("[red]잘못된 입력, 기본값 사용[/red]")
    return default


def run_floor_narrative(player):
    # main.py와 동일하게 층 진입 내레이션 출력
    try:
        console.print()
        ai_manager.get_floor_narrative(
            player.current_floor,
            assets.get_stage_by_floor(player.current_floor),
            player.party[player.active_index]['name']
        )
    except Exception as e:
        console.print(f"[yellow]내레이션 오류: {e}[/yellow]")


def test_shop(player):
    floor = pick_floor(default=player.current_floor)
    player.current_floor = floor
    visuals.clear_screen()
    console.print(Panel(f"[bold yellow]🛒 상점 테스트 — {floor}층[/bold yellow]", style="yellow", box=box.DOUBLE))
    run_floor_narrative(player)
    world.handle_shop(player, floor)


def test_event(player):
    floor = pick_floor(default=player.current_floor)
    player.current_floor = floor
    visuals.clear_screen()
    console.print(Panel(f"[bold cyan]🌀 랜덤 사건 테스트 — {floor}층[/bold cyan]", style="cyan", box=box.DOUBLE))
    run_floor_narrative(player)
    world.handle_random_event(player, floor)


def test_boss(player):
    console.print("\n[bold]보스 층 선택[/bold]")
    console.print("  1. 15층 보스")
    console.print("  2. 30층 보스")
    cmd = console.input("선택 (Enter=15): ").strip()
    floor = 30 if cmd == '2' else 15
    player.current_floor = floor
    visuals.clear_screen()
    console.print(Panel(f"[bold red]👑 보스 전투 테스트 — {floor}층[/bold red]", style="red", box=box.DOUBLE))
    run_floor_narrative(player)
    win = world.handle_combat(player, floor)
    console.print(f"\n[bold]결과: {'승리' if win else '패배'}[/bold]")


def test_combat(player):
    floor = pick_floor(default=player.current_floor)
    if floor in (15, 30):
        console.print("[yellow]주의: 15/30층은 보스 층입니다. 일반 전투로 강제 진행합니다.[/yellow]")
    player.current_floor = floor
    visuals.clear_screen()
    console.print(Panel(f"[bold red]⚔  랜덤 전투 테스트 — {floor}층[/bold red]", style="red", box=box.DOUBLE))
    run_floor_narrative(player)
    # handle_combat이 floor in [15,30]일 때 보스로 분기하므로,
    # 보스 층에서도 일반 전투를 보고 싶으면 임시로 다른 층 번호 사용
    test_floor = floor
    if floor in (15, 30):
        test_floor = floor - 1  # 같은 스테이지의 일반 몬스터 풀 사용
    win = world.handle_combat(player, test_floor)
    console.print(f"\n[bold]결과: {'승리' if win else '패배'}[/bold]")


def cheat_menu(player):
    while True:
        console.print(Panel(
            f"[bold]현재 상태[/bold]\n"
            f"  층: {player.current_floor}  /  골드: {player.gold}G  /  유물: {len(player.relics)}/4",
            style="green", box=box.ROUNDED
        ))
        console.print("  [bold cyan]1.[/bold cyan] 골드 +1000")
        console.print("  [bold cyan]2.[/bold cyan] 파티 풀회복")
        console.print("  [bold cyan]3.[/bold cyan] 파티 ATK +20")
        console.print("  [bold cyan]4.[/bold cyan] 파티 HP +100")
        console.print("  [bold cyan]5.[/bold cyan] 층 변경")
        console.print("  [bold cyan]6.[/bold cyan] 파티 상태 보기")
        console.print("  [bold cyan]0.[/bold cyan] 돌아가기")
        cmd = console.input("선택: ").strip()
        if cmd == '1':
            player.gold += 1000
            console.print("[green]+1000G[/green]")
        elif cmd == '2':
            player.heal_party(9999)
            console.print("[green]파티 풀회복[/green]")
        elif cmd == '3':
            for c in player.party:
                c['atk'] += 20
            console.print("[green]파티 ATK +20[/green]")
        elif cmd == '4':
            for c in player.party:
                c['hp'] += 100
                c['current_hp'] += 100
            console.print("[green]파티 HP +100[/green]")
        elif cmd == '5':
            player.current_floor = pick_floor(default=player.current_floor)
        elif cmd == '6':
            player.show_detailed_status()
        elif cmd == '0':
            break


def main_menu():
    visuals.clear_screen()
    console.print(Panel(
        "[bold magenta]🛠  SubCal Rogue — 디버그/테스트 실행기  🛠[/bold magenta]\n"
        "[dim]상점·랜덤 사건·보스·랜덤 전투를 단발로 테스트합니다.[/dim]",
        style="magenta", box=box.DOUBLE
    ))

    # 난이도/AI 한 번만 셋업
    ai_manager.prompt_api_key()

    console.print("\n[bold yellow]── 초기 셋업 ──[/bold yellow]")
    console.print("  난이도 스케일 적용 (몬스터 강도)")
    console.print("  1. 노말 (0.07)   2. 하드 (0.10)   Enter=하드")
    cmd = console.input("선택: ").strip()
    floor_scale = 0.07 if cmd == '1' else 0.10
    assets.FLOOR_SCALE = floor_scale

    cheat_raw = console.input("치트 스탯(HP+200/ATK+50/MP+5) 적용? (y/N): ").strip().lower()
    cheat_stats = cheat_raw == 'y'

    gold_raw = console.input("시작 골드 (Enter=999): ").strip()
    try:
        gold = int(gold_raw) if gold_raw else 999
    except ValueError:
        gold = 999

    player = setup_player(floor=1, gold=gold, cheat_stats=cheat_stats)

    while True:
        console.print()
        console.rule("[bold]디버그 메뉴[/bold]", style="magenta")
        console.print(f"[dim]층: {player.current_floor} / 골드: {player.gold}G / 난이도: {floor_scale}[/dim]")
        console.print("  [bold cyan]1.[/bold cyan] 🛒 상점 테스트")
        console.print("  [bold cyan]2.[/bold cyan] 🌀 랜덤 사건 테스트")
        console.print("  [bold cyan]3.[/bold cyan] 👑 보스 전투 테스트 (15/30층)")
        console.print("  [bold cyan]4.[/bold cyan] ⚔  랜덤 전투 테스트")
        console.print("  [bold cyan]5.[/bold cyan] 🃏 치트 메뉴 (골드/스탯/층)")
        console.print("  [bold cyan]6.[/bold cyan] 🎲 층 자동 판정 (generate_floor_event)")
        console.print("  [bold cyan]0.[/bold cyan] 종료")

        cmd = console.input("\n선택: ").strip()
        if cmd == '1':
            test_shop(player)
        elif cmd == '2':
            test_event(player)
        elif cmd == '3':
            test_boss(player)
        elif cmd == '4':
            test_combat(player)
        elif cmd == '5':
            cheat_menu(player)
        elif cmd == '6':
            floor = pick_floor(default=player.current_floor)
            ev = world.generate_floor_event(floor)
            console.print(f"[bold]{floor}층 → 판정 결과: [yellow]{ev}[/yellow][/bold]")
        elif cmd == '0':
            console.print("[dim]디버그 종료.[/dim]")
            return


if __name__ == "__main__":
    main_menu()
