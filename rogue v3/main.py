# main.py
import world
import visuals
from player import Player

def main():
    visuals.clear_screen()
    print("🐍 30 Floors of Python (Core Version) 🐍")
    print("\n기본 파티(전사, 마법사)로 던전 탐험을 시작합니다...\n")
    input("시작하려면 [Enter]를 누르세요.")
    
    player = Player()
    
    # 30층까지 간소화된 루프
    while player.current_floor <= 30:
        visuals.clear_screen()
        visuals.print_header(player.current_floor)
        player.show_status()
        
        ready = False
        while not ready:
            print(f"\n--- {player.current_floor}층 입구 ---")
            cmd = input("[Enter] 진입 | [S] 스왑 | [I] 상세정보 | [Q] 종료: ").lower()
            
            if cmd == 's':
                player.swap()
                player.show_status()
            elif cmd == 'i':
                player.show_detailed_status() 
                visuals.clear_screen()
                visuals.print_header(player.current_floor)
                player.show_status()
            elif cmd == 'q':
                print("게임을 종료합니다.")
                return
            else:
                ready = True
        
        event_type = world.generate_floor_event(player.current_floor)
        
        if event_type == "boss" or event_type == "combat":
            win = world.handle_combat(player, player.current_floor)
            if not win:
                print("\n💀 파티가 전멸했습니다... 게임 오버.")
                return
        elif event_type == "shop":
            world.handle_shop(player, player.current_floor)
        elif event_type == "event":
            world.handle_random_event(player, player.current_floor)
            
        player.current_floor += 1
        
    print("\n🎉 축하합니다! 30층 보스를 물리치고 게임을 클리어하셨습니다! 🎉")

if __name__ == "__main__":
    main()