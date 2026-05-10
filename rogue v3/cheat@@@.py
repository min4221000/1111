# test_force.py
# 상점, 사건, 전투를 강제 실행하는 테스트 스크립트
# 사용법: python test_force.py

import sys
sys.path.insert(0, '.')  # 같은 폴더의 모듈 import

from player import Player
import world
import visuals

def main():
    player = Player()
    print("=" * 50)
    print("🛠️  강제 실행 테스트")
    print("=" * 50)
    print()
    print("  1. 상점 강제 실행")
    print("  2. 사건 강제 실행")
    print("  3. 전투 강제 실행 (1층 몬스터)")
    print("  4. 보스 전투 (15층)")
    print("  0. 종료")
    print()

    while True:
        cmd = input("선택: ").strip()
        
        if cmd == "1":
            print("\n--- 상점 강제 실행 ---")
            world.handle_shop(player, player.current_floor)
        elif cmd == "2":
            print("\n--- 사건 강제 실행 ---")
            world.handle_random_event(player, player.current_floor)
        elif cmd == "3":
            print("\n--- 전투 강제 실행 (1층) ---")
            win = world.handle_combat(player, 1)
            print(f"결과: {'승리!' if win else '패배...'}")
        elif cmd == "4":
            print("\n--- 보스 전투 강제 실행 (15층) ---")
            win = world.handle_combat(player, 15)
            print(f"결과: {'승리!' if win else '패배...'}")
        elif cmd == "0":
            break
        
        print()
        player.show_status()
        print()

if __name__ == "__main__":
    main()