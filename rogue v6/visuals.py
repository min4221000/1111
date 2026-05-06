# visuals.py - 화면 출력 유틸리티
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

def clear_screen():
    console.clear()

def print_header(floor):
    header_text = Text(f"⚔️ 30 FLOORS - FLOOR {floor} ⚔️", style="bold magenta")
    console.print(Panel(header_text, border_style="bright_blue", expand=True))
