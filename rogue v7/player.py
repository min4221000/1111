# player.py - 플레이어 상태 관리 (파티, 덱, 유물, 골드)
# 합성 조합은 assets.RELIC_SYNTHESIS에 정의되어 있고 _check_synthesis에서 자동 처리함
import assets
import random
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

class Player:
    #플레이어 기본 상태
    def __init__(self):
        self.party = [assets.get_class("전사"), assets.get_class("마법사")]
        self.relics = []

        for char in self.party:
            char['current_hp'] = char['hp']
            char['current_energy'] = 0
            char['draw_pile'] = []
            char['discard_pile'] = []
            char['hand'] = []

        self.active_index = 0  # 0번이 전방(전사), 1번이 후방(마법사)으로 시작
        self.gold = 100
        self.current_floor = 1
        # 합성으로 소모된 유물도 여기 들어감, 상점에서 같은 유물 다시 나오는 거 막으려고
        self.purchased_relics = set()

    @property
    def active_char(self):
        return self.party[self.active_index]

    def swap(self):
        self.active_index = 1 - self.active_index
        console.print(f"\n[cyan]🔄 캐릭터 교체! 현재 전방: [bold]{self.active_char['name']}[/bold][/cyan]")

    def init_combat_decks(self):
        # 전투 시작할 때만 호출해줘, 덱 셔플이랑 상태이상 초기화 담당
        bonus = 0
        for r in self.relics:
            bonus += r.get('effect', {}).get('bonus_energy', 0)
        for char in self.party:
            char['draw_pile'] = char['deck'][:]
            random.shuffle(char['draw_pile'])
            char['discard_pile'] = []
            char['hand'] = []
            char['statuses'] = {}  # 이전 전투 상태이상 초기화
            char['current_energy'] = char['mp'] + bonus

    def draw_cards(self, char, count=4):
        # 기존 손패 버린패로 보내고 새로 뽑음, 턴 시작이나 스왑할 때 씀
        # 드로우 파일 비면 버린패 섞어서 재활용
        char['discard_pile'].extend(char['hand'])
        char['hand'] = []

        for _ in range(count):
            if not char['draw_pile']:
                if not char['discard_pile']:
                    break  # 뽑을 카드 자체가 없을 때
                char['draw_pile'] = char['discard_pile'][:]
                random.shuffle(char['draw_pile'])
                char['discard_pile'] = []
            char['hand'].append(char['draw_pile'].pop())

    def draw_cards_add(self, char, count):
        # 손패 유지한 채로 추가로 뽑음, '집중' 카드 전용
        # draw_cards()랑 목적이 달라서 함수 분리함, 합치면 헷갈림
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
        # 전방은 매 턴 mp로 완전 초기화
        # 후방은 매 턴 +1씩 충전, 최대 mp×2까지 (오래 후방에 둘수록 꺼냈을 때 강해짐)
        # 후방이 죽은 상태면 충전 안 함, 힐로 살려도 과충전 없이 복귀하게 하려고
        bonus = 0
        for r in self.relics:
            bonus += r.get('effect', {}).get('bonus_energy', 0)
        front = self.active_char
        back  = self.party[1 - self.active_index]

        front['current_energy'] = front['mp'] + bonus

        if back['current_hp'] <= 0:
            back['current_energy'] = 0  # 죽은 상태면 0 유지, 부활해도 과충전 없음
        else:
            overcharge_cap = (back['mp'] + bonus) * 2
            back['current_energy'] = min(overcharge_cap, back['current_energy'] + 1)

    def heal_party(self, amount):
        # 죽은 캐릭터도 힐 대상에 포함됨, 힐로 부활 가능하게 설계한 거라 의도된 동작임
        for char in self.party:
            char['current_hp'] = min(char['hp'], char['current_hp'] + amount)

    def add_relic(self, relic):
        # 유물 슬롯 최대 4개, 꽉 찼으면 하나 버리고 추가
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
        # 유물 효과 중 즉시 반영하는 스탯만 처리
        # bonus_energy, poison_start, hp_drain 같은 동적 키는 전투 중 매 턴 계산하는 방식이라 여기서 처리 안 함
        DYNAMIC_KEYS = ('bonus_energy', 'poison_start', 'hp_drain', 'duration_bonus', 'burn_start', 'dodge_chance')
        for key, val in effect.items():
            #여기서 처리될거 안 될거 구분
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
        # 합성 가능한 조합 없어질 때까지 반복, 연쇄 합성도 여기서 처리됨
        while True:
            #복사
            relic_names = [r['name'] for r in self.relics]
            found = False
            #찾고 합성하고 제거 추가
            for materials, result in assets.RELIC_SYNTHESIS.items():
                mat1, mat2 = materials
                if mat1 not in relic_names or mat2 not in relic_names:
                    continue

                for i in range(len(self.relics)):
                    if self.relics[i]['name'] == mat1:
                        self.relics.pop(i)
                        break

                for i in range(len(self.relics)):
                    if self.relics[i]['name'] == mat2:
                        self.relics.pop(i)
                        break

                self.relics.append(result)
                console.print(f"\n[bold yellow]✨ 유물 공명(Synthesis) 발생!![/bold yellow]")
                console.print(f"[bold white]{mat1} + {mat2} → [magenta]{result['name']}[/magenta] 합성 성공![/bold white]")
                self._apply_relic_stats(result.get('effect', {}))
                found = True
                break  # 합성 1회 후 목록 다시 확인

            if not found:
                break  # 더 이상 합성 가능한 조합 없음

    def load_from_save(self, data):
        # relics는 add_relic 거치지 않고 직접 할당함, 경유하면 스탯이 중복 적용돼서
        self.current_floor    = data['floor']
        self.gold             = data['gold']
        self.active_index     = data['active_index']
        self.purchased_relics = set(data['purchased_relics'])
        self.relics           = data['relics']

        for i, saved in enumerate(data['party']):
            char = self.party[i]
            char['hp']             = saved['hp']
            char['current_hp']     = saved['current_hp']
            char['atk']            = saved['atk']
            char['spd']            = saved['spd']
            char['mp']             = saved['mp']
            char['deck']           = saved['deck']
            char['statuses']       = {}
            char['draw_pile']      = []
            char['discard_pile']   = []
            char['hand']           = []
            char['current_energy'] = 0
    #상태창 UI
    def show_status(self):
        table = Table(title="🛡️ 파티 현황", box=box.ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("위치", justify="center", width=10)
        table.add_column("직업", justify="center", width=12)
        table.add_column("HP", justify="center", width=15)
        table.add_column("ATK", justify="center", width=8)
        table.add_column("SPD", justify="center", width=8)
        table.add_column("덱", justify="center", width=8)

        for i, c in enumerate(self.party):
            pos = "[bold green]▶ 전방[/bold green]" if i == self.active_index else "[dim]  후방[/dim]"
            if c['current_hp'] < c['hp'] * 0.25:
                hp_color = "red"
            elif c['current_hp'] < c['hp'] * 0.5:
                hp_color = "yellow"
            else:
                hp_color = "white"
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
        # I 키 눌렀을 때 보이는 상세 정보 화면
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
    #유물 조합
    def show_synthesis_book(self):
        owned_names = {r['name'] for r in self.relics}

        console.print(Panel("[bold yellow]📖 유물 조합 사전[/bold yellow]", style="yellow", box=box.DOUBLE))
        console.print()

        for (mat1, mat2), result in assets.RELIC_SYNTHESIS.items():
            has_mat1 = mat1 in owned_names
            has_mat2 = mat2 in owned_names
            is_done  = result['name'] in owned_names

            if is_done:
                icon   = "[bold green]✅[/bold green]"
                status = "[bold green]완성[/bold green]"
            elif has_mat1 and has_mat2:
                icon   = "[bold yellow]⚡[/bold yellow]"
                status = "[bold yellow]지금 합성 가능![/bold yellow]"
            else:
                icon   = "[dim]❌[/dim]"
                missing = ", ".join(
                    (f"[dim]{m}[/dim]" for m in (mat1, mat2) if m not in owned_names)
                )
                status = f"[dim]미완성 — 없는 재료: {missing}[/dim]"

            # 가진 재료는 밝게, 없는 재료는 흐리게
            mat1_str = f"[magenta]{mat1}[/magenta]" if has_mat1 else f"[dim]{mat1}[/dim]"
            mat2_str = f"[magenta]{mat2}[/magenta]" if has_mat2 else f"[dim]{mat2}[/dim]"

            console.print(f"  {icon}  {mat1_str} + {mat2_str} → [bold yellow]{result['name']}[/bold yellow]  {status}")
            console.print(f"      [dim italic]{result.get('desc', '')}[/dim italic]")
            console.print()

        console.input("[Enter]를 눌러 돌아가기...")
