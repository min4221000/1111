# visuals.py - 화면 출력 유틸리티
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import time

console = Console()

def clear_screen():
    console.clear()

def print_header(floor, difficulty="보통"):
    header_text = Text(f"⚔️ 30 FLOORS - FLOOR {floor}  [{difficulty}] ⚔️", style="bold magenta")
    console.print(Panel(header_text, border_style="bright_blue", expand=True))


def print_typing_text(text, delay=0.02, style=None):
    """텍스트를 1글자씩 타이핑 효과로 출력 (AI 내레이션용)"""
    # 마크업이 없는 순수 텍스트 처리 - 각 문자를 순차 출력
    for i, char in enumerate(text):
        console.print(char, style=style, end='', highlight=False)
        time.sleep(delay)
    console.print()  # 마지막 개행

