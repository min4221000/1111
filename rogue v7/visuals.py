# 화면 출력 유틸리티
# 타이핑 효과 텍스트는 print_typing_text 쓰기 일반 출력이랑 구분하려고 분리해둔 거
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
    # AI 내레이션용, 텍스트를 한 글자씩 타이핑 효과로 출력
    for i, char in enumerate(text):
        console.print(char, style=style, end='', highlight=False)
        time.sleep(delay)
    console.print() 
