# main.py - 게임 시작점, 전체 루프 관리
import assets
import world
import visuals
import save_load
import ai_manager
from player import Player
from rich.console import Console

console = Console()

# 난이도 표시 이름 (헤더에 표시용)
DIFFICULTY_NAMES = {0.07: "쉬움", 0.10: "보통", 0.14: "어려움"}


def start_menu():
    visuals.clear_screen()
    console.print("[bold magenta]🐍 30 Floors of Python 🐍[/bold magenta]\n")
    console.print("  [bold cyan]1.[/bold cyan] 새 게임")
    if save_load.save_exists():
        console.print("  [bold cyan]2.[/bold cyan] 이어하기")
    console.print("  [bold cyan]0.[/bold cyan] 종료")

    while True:
        cmd = console.input("\n선택: ").strip()
        if cmd == '1':
            return 'new'
        if cmd == '2' and save_load.save_exists():
            return 'load'
        if cmd == '0':
            return 'quit'


def select_difficulty():
    console.print("\n[bold yellow]── 난이도 선택 ──[/bold yellow]")
    console.print("  [bold cyan]1.[/bold cyan] 쉬움    — 몬스터 층당 [green]7%[/green] 성장  (30층 HP×3.1)")
    console.print("  [bold cyan]2.[/bold cyan] 보통    — 몬스터 층당 [yellow]10%[/yellow] 성장 (30층 HP×4.0) ← 기본")
    console.print("  [bold cyan]3.[/bold cyan] 어려움  — 몬스터 층당 [red]14%[/red] 성장  (30층 HP×5.2)")

    scale_map = {'1': 0.07, '2': 0.10, '3': 0.14}
    while True:
        cmd = console.input("\n선택: ").strip()
        if cmd in scale_map:
            return scale_map[cmd]


def main():
    choice = start_menu()
    if choice == 'quit':
        return

    player = Player()
    floor_scale = 0.10  # 기본값

    if choice == 'new':
        floor_scale = select_difficulty()
        assets.FLOOR_SCALE = floor_scale
        console.print(f"\n[bold green]난이도: {DIFFICULTY_NAMES[floor_scale]}[/bold green]")

    elif choice == 'load':
        data = save_load.load_game()
        if data:
            player.load_from_save(data)
            world.last_shop_floor = data.get('last_shop_floor', 1)
            floor_scale = data.get('floor_scale', 0.10)
            assets.FLOOR_SCALE = floor_scale
            console.print(f"\n[bold green]💾 {player.current_floor}층에서 이어합니다! "
                          f"(난이도: {DIFFICULTY_NAMES.get(floor_scale, '보통')})[/bold green]")
        else:
            console.print("[red]세이브 파일을 불러올 수 없습니다. 새 게임을 시작합니다.[/red]")
            floor_scale = select_difficulty()
            assets.FLOOR_SCALE = floor_scale

    console.input("\n시작하려면 [Enter]를 누르세요.")

    while player.current_floor <= 30:
        visuals.clear_screen()
        visuals.print_header(player.current_floor, DIFFICULTY_NAMES.get(floor_scale, '보통'))
        player.show_status()

        # 층 진입 전 메뉴 - 스왑이나 상세 정보 확인 가능
        ready = False
        while not ready:
            console.print(f"\n[bold]--- {player.current_floor}층 입구 ---[/bold]")
            cmd = console.input("[Enter] 진입 | [S] 스왑 | [I] 상세정보 | [R] 조합사전 | [V] 저장 | [Q] 종료: ").lower()

            if cmd == 's':
                other = player.party[1 - player.active_index]
                if other['current_hp'] <= 0:
                    console.print(f"[red]{other['name']}은(는) 전사해서 교체할 수 없습니다.[/red]")
                else:
                    player.swap()
                player.show_status()
            elif cmd == 'i':
                player.show_detailed_status()
                visuals.clear_screen()
                visuals.print_header(player.current_floor, DIFFICULTY_NAMES.get(floor_scale, '보통'))
                player.show_status()
            elif cmd == 'r':
                player.show_synthesis_book()
                visuals.clear_screen()
                visuals.print_header(player.current_floor, DIFFICULTY_NAMES.get(floor_scale, '보통'))
                player.show_status()
            elif cmd == 'v':
                save_load.save_game(player, world.last_shop_floor, floor_scale)
                console.print("[bold green]💾 저장되었습니다![/bold green]")
            elif cmd == 'q':
                save_load.save_game(player, world.last_shop_floor, floor_scale)
                console.print("[dim]게임을 저장하고 종료합니다.[/dim]")
                return
            else:
                ready = True

        # 층 진입 AI 내레이션
        try:
            floor_narrative = ai_manager.get_floor_narrative(
                player.current_floor,
                assets.get_stage_by_floor(player.current_floor),
                player.party[player.active_index]['name']
            )
            console.print()
            visuals.print_typing_text(floor_narrative, delay=0.06, style="bright_cyan")
        except Exception as e:
            console.print(f"[bold yellow]내레이션 생성 중 오류: {e} — 계속 진행합니다.[/bold yellow]")

        event_type = world.generate_floor_event(player.current_floor)

        if event_type in ("boss", "combat"):
            win = world.handle_combat(player, player.current_floor)
            if not win:
                console.print("\n[bold red]💀 파티가 전멸했습니다... 게임 오버.[/bold red]")
                save_load.delete_save()
                return
        elif event_type == "shop":
            world.handle_shop(player, player.current_floor)
        elif event_type == "event":
            world.handle_random_event(player, player.current_floor)

        # 층 완료 후 자동 저장
        save_load.save_game(player, world.last_shop_floor, floor_scale)
        player.current_floor += 1

    console.print("\n[bold yellow]🎉 축하합니다! 30층 보스를 물리치고 게임을 클리어하셨습니다! 🎉[/bold yellow]")
    save_load.delete_save()


if __name__ == "__main__":
    main()
