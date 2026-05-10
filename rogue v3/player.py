# player.py
import assets
import copy
import random
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

class Player:
    def __init__(self):
        # 직업 선택 삭제: 전사와 마법사 고정
        self.party = [assets.get_class("전사"), assets.get_class("마법사")]
        for char in self.party:
            char['current_hp'] = char['hp']
            char['current_energy'] = 0
            char['draw_pile'] = []
            char['discard_pile'] = []
            char['hand'] = []

        self.active_index = 0
        self.gold = 100
        self.current_floor = 1

    @property
    def active_char(self):
        return self.party[self.active_index]

    def swap(self):
        self.active_index = 1 - self.active_index
        console.print(f"\n[cyan]🔄 캐릭터 교체! 현재 전방: {self.active_char['name']}[/cyan]")

    def init_combat_decks(self):
        for char in self.party:
            char['draw_pile'] = char['deck'][:]
            random.shuffle(char['draw_pile'])
            char['discard_pile'] = []
            char['hand'] = []

    def draw_cards(self, char, count=4):
        char['discard_pile'].extend(char['hand'])
        char['hand'] = []
        for _ in range(count):
            if not char['draw_pile']:
                if not char['discard_pile']: break
                char['draw_pile'] = char['discard_pile'][:]
                random.shuffle(char['draw_pile'])
                char['discard_pile'] = []
            char['hand'].append(char['draw_pile'].pop())

    def apply_natural_regen(self):
        for char in self.party:
            regen = 2 if char.get('type') == 'ranged' else 1
            char['current_energy'] = min(char['mp'], char['current_energy'] + regen)

    def show_status(self):
        table = Table.grid(padding=(0, 2))
        table.add_column(width=12); table.add_column(width=15); table.add_column()
        for i, c in enumerate(self.party):
            mark = "[bold green]▶ 전방[/bold green]" if i == self.active_index else "[dim]  후방[/dim]"
            hp = f"HP {c['current_hp']}/{c['hp']}"
            en = f"[bold cyan]⚡ EN: {c['current_energy']}/{c['mp']}[/bold cyan]"
            table.add_row(mark, f"[bold]{c['name']}[/bold]", f"{hp}  {en}")

        console.print(Panel(
            table, title=f"[white]🏰 {self.current_floor}층  💰 {self.gold}G[/white]", box=box.ROUNDED
        ))

    def show_detailed_status(self):
        console.clear()
        table = Table(title="📜 파티 상세 정보", box=box.ROUNDED, header_style="bold cyan", show_header=True)
        table.add_column("위치"); table.add_column("직업"); table.add_column("HP"); table.add_column("ATK"); table.add_column("DEF"); table.add_column("덱수량")
        for i, c in enumerate(self.party):
            pos = "[bold green]▶ 전방[/bold green]" if i == self.active_index else "[dim]  후방[/dim]"
            table.add_row(pos, c['name'], f"{c['current_hp']}/{c['hp']}", str(c['atk']), str(c['defense']), f"{len(c.get('deck',[]))}장")
        console.print(table)
        console.input("\n[Enter] 돌아가기")