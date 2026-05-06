# main.py - 게임 시작점, 전체 루프 관리
import world
import visuals
from player import Player
from rich.console import Console

console = Console()

def main():
    visuals.clear_screen()
    console.print("[bold magenta]🐍 30 Floors of Python (Core Version) 🐍[/bold magenta]")
    console.print("\n[dim]기본 파티(전사, 마법사)로 던전 탐험을 시작합니다...[/dim]\n")
    console.input("시작하려면 [Enter]를 누르세요.")

    player = Player()

    while player.current_floor <= 30:
        visuals.clear_screen()
        visuals.print_header(player.current_floor)
        player.show_status()

        # 층 진입 전 메뉴 - 스왑이나 상세 정보 확인 가능
        ready = False
        while not ready:
            console.print(f"\n[bold]--- {player.current_floor}층 입구 ---[/bold]")
            cmd = console.input("[Enter] 진입 | [S] 스왑 | [I] 상세정보 | [Q] 종료: ").lower()

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
                visuals.print_header(player.current_floor)
                player.show_status()
            elif cmd == 'q':
                console.print("[dim]게임을 종료합니다.[/dim]")
                return
            else:
                ready = True

        event_type = world.generate_floor_event(player.current_floor)

        if event_type in ("boss", "combat"):
            win = world.handle_combat(player, player.current_floor)
            if not win:
                console.print("\n[bold red]💀 파티가 전멸했습니다... 게임 오버.[/bold red]")
                return
        elif event_type == "shop":
            world.handle_shop(player, player.current_floor)
        elif event_type == "event":
            world.handle_random_event(player, player.current_floor)

        player.current_floor += 1

    console.print("\n[bold yellow]🎉 축하합니다! 30층 보스를 물리치고 게임을 클리어하셨습니다! 🎉[/bold yellow]")

if __name__ == "__main__":
    main()
