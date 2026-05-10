# visuals.py
import time
import random
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import os

console = Console()

def clear_screen():
    console.clear()

def print_header(floor):
    header_text = Text(f"⚔️ 100 FLOORS - FLOOR {floor} ⚔️", style="bold magenta")
    console.print(Panel(header_text, border_style="bright_blue", expand=True))

def display_announcement(message, style="bold yellow"):
    console.print(f"\n[{style}]{message}[/]", justify="center")

def divider():
    console.print("-" * 50, style="dim")

# [수정] 누락되었던 주사위 애니메이션 함수 구현
def roll_dice_animation():
    console.print("\n[yellow]주사위를 굴립니다...[/yellow]")
    time.sleep(1.2)
    val = random.randint(1, 6)
    console.print(f"[bold green]🎲 주사위가 멈췄습니다... 결과는 [{val}]![/bold green]")
    return val