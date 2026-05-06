# player.py - 플레이어 상태 전체 관리 (파티, 덱, 유물, 골드 등)
import assets
import random
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

class Player:
    def __init__(self):
        self.party = [assets.get_class("전사"), assets.get_class("마법사")]
        self.relics = []

        for char in self.party:
            char['current_hp'] = char['hp']
            char['current_energy'] = 0
            char['draw_pile'] = []
            char['discard_pile'] = []
            char['hand'] = []

        self.active_index = 0  # 0=전사(전방), 1=마법사(후방) 로 시작
        self.gold = 100
        self.current_floor = 1
        self.purchased_relics = set()  # 합성으로 소모된 유물도 포함, 상점 중복 방지용

    @property
    def active_char(self):
        return self.party[self.active_index]

    def swap(self):
        self.active_index = 1 - self.active_index
        console.print(f"\n[cyan]🔄 캐릭터 교체! 현재 전방: [bold]{self.active_char['name']}[/bold][/cyan]")

    def init_combat_decks(self):
        # 전투 시작할 때만 호출 - 덱 셔플, 상태이상 초기화
        # bonus_energy 유물이 있으면 시작 에너지에 반영
        bonus = sum(r.get('effect', {}).get('bonus_energy', 0) for r in self.relics)
        for char in self.party:
            char['draw_pile'] = char['deck'][:]
            random.shuffle(char['draw_pile'])
            char['discard_pile'] = []
            char['hand'] = []
            char['statuses'] = {}  # 이전 전투에서 남은 상태이상 초기화
            char['current_energy'] = char['mp'] + bonus

    def draw_cards(self, char, count=4):
        # 기존 손패는 버린패로 보내고 새로 뽑음 (턴 시작/스왑 때 사용)
        # 드로우 파일이 비면 버린패를 섞어서 재활용
        char['discard_pile'].extend(char['hand'])
        char['hand'] = []

        for _ in range(count):
            if not char['draw_pile']:
                if not char['discard_pile']:
                    break  # 뽑을 카드가 아예 없을 때
                char['draw_pile'] = char['discard_pile'][:]
                random.shuffle(char['draw_pile'])
                char['discard_pile'] = []
            char['hand'].append(char['draw_pile'].pop())

    def draw_cards_add(self, char, count):
        # 손패 유지하면서 추가로 뽑음 - "집중" 카드 전용
        # draw_cards()랑 나눈 이유: 목적이 완전히 달라서 같은 함수로 합치면 헷갈림
        drawn = 0
        for _ in range(count):
            if not char['draw_pile']:
                if not char['discard_pile']:
                    break
                char['draw_pile'] = char['discard_pile'][:]
                random.shuffle(char['draw_pile'])
                char['discard_pile'] = []
            char['hand'].append(char['draw_pile'].pop())
            drawn += 1
        return drawn

    def reset_energy(self):
        # 전방: 매 턴 mp로 완전 초기화
        # 후방: 매 턴 +1씩 충전 (최대 mp×2까지) - 오래 후방에 둘수록 꺼낼 때 강해짐
        # [v6] 후방이 사망 중이면 충전 안 함 (힐로 살려도 과충전 에너지 없이 복귀)
        bonus = sum(r.get('effect', {}).get('bonus_energy', 0) for r in self.relics)
        front = self.active_char
        back  = self.party[1 - self.active_index]

        front['current_energy'] = front['mp'] + bonus

        if back['current_hp'] <= 0:
            back['current_energy'] = 0  # 사망 중엔 매 턴 0으로 유지 → 부활해도 과충전 없음
        else:
            overcharge_cap = (back['mp'] + bonus) * 2
            back['current_energy'] = min(overcharge_cap, back['current_energy'] + 1)

    def heal_party(self, amount):
        # 사망한 캐릭터도 힐 대상에 포함됨 (부활 가능 - 의도된 설계)
        for char in self.party:
            char['current_hp'] = min(char['hp'], char['current_hp'] + amount)

    def add_relic(self, relic):
        # 유물 슬롯 최대 4개 - 꽉 찼으면 하나 버리고 추가
        if len(self.relics) >= 4:
            console.print("\n[bold yellow]유물 슬롯이 가득 찼습니다 (최대 4개). 버릴 유물을 선택하세요:[/bold yellow]")
            for i, r in enumerate(self.relics, 1):
                console.print(f"  {i}. [magenta]{r['name']}[/magenta] — [dim]{r.get('desc', '')}[/dim]")
            console.print("  0. 획득 포기")

            while True:
                try:
                    choice = int(console.input("선택: ").strip())
                    if choice == 0:
                        console.print("[dim]획득을 포기했습니다.[/dim]")
                        return False
                    if 1 <= choice <= len(self.relics):
                        discarded = self.relics.pop(choice - 1)
                        console.print(f"[dim]{discarded['name']}을(를) 버렸습니다.[/dim]")
                        break
                except ValueError:
                    pass

        self.relics.append(relic)
        self.purchased_relics.add(relic['name'])
        console.print(f"\n[bold yellow]유물 획득: {relic['name']}![/bold yellow]")
        self._apply_relic_stats(relic.get('effect', {}))
        self._check_synthesis()
        return True

    def _apply_relic_stats(self, effect):
        # 유물 효과 중 즉시 반영할 스탯만 적용
        # bonus_energy 등 동적 키는 전투 중 매 턴 계산하는 방식이라 여기서 처리 안 함
        DYNAMIC_KEYS = ('bonus_energy', 'poison_start', 'hp_drain', 'duration_bonus', 'burn_start')
        for key, val in effect.items():
            if key in DYNAMIC_KEYS:
                continue
            elif key == 'hp':
                for char in self.party:
                    char['hp'] += val
                    char['current_hp'] += val
            elif key in ('atk', 'spd', 'mp'):
                for char in self.party:
                    char[key] = char.get(key, 0) + val

    def _check_synthesis(self):
        # 합성 가능한 조합이 없을 때까지 반복 (연쇄 합성 대응)
        while True:
            relic_names = [r['name'] for r in self.relics]
            found = False

            for materials, result in assets.RELIC_SYNTHESIS.items():
                mat1, mat2 = materials
                if mat1 not in relic_names or mat2 not in relic_names:
                    continue

                # mat1 인덱스 찾기
                idx1 = 0
                for i, r in enumerate(self.relics):
                    if r['name'] == mat1:
                        idx1 = i
                        break
                self.relics.pop(idx1)

                # pop 후 목록 갱신, mat2 인덱스 찾기
                idx2 = 0
                for i, r in enumerate(self.relics):
                    if r['name'] == mat2:
                        idx2 = i
                        break
                self.relics.pop(idx2)

                self.relics.append(result)
                console.print(f"\n[bold yellow]✨ 유물 공명(Synthesis) 발생!![/bold yellow]")
                console.print(f"[bold white]{mat1} + {mat2} → [magenta]{result['name']}[/magenta] 합성 성공![/bold white]")
                self._apply_relic_stats(result.get('effect', {}))
                found = True
                break  # 합성 1회 후 목록 다시 확인

            if not found:
                break  # 더 이상 합성 가능한 조합 없음

    def show_status(self):
        # [v6] SPD 컬럼 추가 - 전투 선공/후공 판단할 때 참고용
        table = Table(title="🛡️ 파티 현황", box=box.ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("위치", justify="center", width=10)
        table.add_column("직업", justify="center", width=12)
        table.add_column("HP", justify="center", width=15)
        table.add_column("ATK", justify="center", width=8)
        table.add_column("SPD", justify="center", width=8)
        table.add_column("덱", justify="center", width=8)

        for i, c in enumerate(self.party):
            pos = "[bold green]▶ 전방[/bold green]" if i == self.active_index else "[dim]  후방[/dim]"
            hp_color = "red" if c['current_hp'] < c['hp'] * 0.25 else "yellow" if c['current_hp'] < c['hp'] * 0.5 else "white"
            table.add_row(
                pos,
                c['name'],
                f"[{hp_color}]{c['current_hp']}/{c['hp']}[/]",
                str(c['atk']),
                str(c.get('spd', '?')),
                f"{len(c.get('deck', []))}장"
            )
        console.print(table)
        console.print(f"  [yellow]보유 골드: {self.gold}G[/yellow]   [dim]유물: {len(self.relics)}/4[/dim]")

    def show_detailed_status(self):
        # I 키 누르면 보이는 상세 정보 화면
        console.print(Panel(f"[bold white]Floor {self.current_floor} - 탐험가 기록부[/bold white]", style="blue", box=box.DOUBLE))
        self.show_status()

        console.print("\n[bold yellow]🃏 캐릭터별 보유 카드 덱 (Deck List)[/bold yellow]")
        for c in self.party:
            card_counts = {}
            for card_name in c.get('deck', []):
                card_counts[card_name] = card_counts.get(card_name, 0) + 1
            console.print(f"\n [cyan]{c['name']}[/cyan] 덱 ({len(c.get('deck', []))}장):")
            for name, count in card_counts.items():
                card = assets.CARDS.get(name, {})
                count_str = f" [dim]x{count}[/dim]" if count > 1 else ""
                desc = card.get('description', '')
                console.print(f"   • [bold]{name}[/bold]{count_str} (EN:{card.get('cost', '?')}) [dim]{desc}[/dim]")

        console.print("\n[bold yellow]💍 보유 중인 유물 (Inventory)[/bold yellow]")
        if self.relics:
            for r in self.relics:
                desc = r.get('desc', '특별한 효과가 없습니다.')
                console.print(f" • [bold magenta]{r['name']}[/bold magenta]: [italic white]{desc}[/italic white]")
        else:
            console.print(" [dim]보유 중인 유물이 없습니다.[/dim]")

        console.print("\n[bold yellow]📖 상태이상 효과 안내[/bold yellow]")
        for key, info in assets.STATUS_INFO.items():
            console.print(f" • [bold cyan]{info['name']}[/bold cyan]: [dim]{info['desc']}[/dim]")

        console.input("\n[Enter]를 눌러 던전으로 돌아가기...")
