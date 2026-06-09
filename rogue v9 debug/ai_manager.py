# AI 내레이션 담당 (openai)
# API 없어도 게임 정상 실행 없으면 아래 FALLBACKS에서 랜덤 대사 뽑아씀
import random
import time
from rich.console import Console as _Console
_console = _Console()

# API 실패하거나 키 없을 때 여기서 랜덤 출력
FALLBACKS = {
    "floor": [
        "이번 층에는 더 깊은 위협이 자리하고 있습니다.",
        "바람이 차갑게 불며 다음 도전이 다가옵니다.",
        "발걸음이 무거워지지만, 계속 나아가야 합니다.",
    ],
    "shop": [
        "상점 속 진열품이 당신의 운명을 바꿀지도 모릅니다.",
        "골드와 선택이 교차하는 순간입니다.",
        "여기서의 선택이 다음 전투를 좌우할 것입니다.",
    ],
    "boss": [
        "최종 결전이 눈앞입니다. 숨을 고르세요.",
        "보스의 존재가 주위를 압도합니다.",
        "이곳에서 모든 것이 결정됩니다.",
    ],
    "event": [
        "선택의 대가가 몸을 타고 흐릅니다.",
        "결과는 이미 정해져 있었습니다.",
        "무언가가 변했습니다.",
    ],
    "battle": [
        "적이 어둠 속에서 모습을 드러냈습니다.",
        "전투가 시작됩니다. 살아남으십시오.",
        "위험한 존재가 당신 앞을 막아섭니다.",
    ]
}
# pip install openai
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_API_KEY_HERE")
MODEL_NAME = "gpt-4o-mini"

try:
    from openai import OpenAI
    from assets import STAGE_INFO

    if OPENAI_API_KEY == "YOUR_API_KEY_HERE" or not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY에 실제 키를 입력하세요")

    client = OpenAI(api_key=OPENAI_API_KEY)
    AI_AVAILABLE = True
    print(f"[AI] ✅ OpenAI 준비 완료 (모델: {MODEL_NAME})")

except Exception as e:
    AI_AVAILABLE = False
    print(f"[AI] ⚠️  AI 비활성화 — 원인: {e}")
    # asset import 실패해도 persona는 여기서 직접 정의해서 fallback 문구 쓸 수 있게 함
    STAGE_INFO = {
        1: {"persona": "인간의 말을 배운 숲의 오래된 정령, 고풍스럽고 약간 조롱하는 말투"},
        2: {"persona": "사람의 언어를 구사하는 지하 감시자, 냉정하고 위협적인 짐승 같은 존재"},
    }

def prompt_api_key():
    global AI_AVAILABLE, client
    key = input("OpenAI API 키 입력 (Enter 스킵): ").strip()
    if not key:
        return
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        AI_AVAILABLE = True
        print("[AI] ✅ API 키 설정 완료")
    except Exception as e:
        print(f"[AI] ⚠️  키 설정 실패 — {e}")

def _fallback(category):
    return random.choice(FALLBACKS[category])

def _stream_print(prompt, fallback_category, style=None):
    if AI_AVAILABLE:
        try:
            stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.8,
                stream=True,
                timeout=8
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                for char in delta:
                    _console.print(char, end="", highlight=False, style=style)
                    time.sleep(0.03)
            _console.print()
            return
        except Exception as e:
            err = str(e)
            if "401" in err or "authentication" in err.lower():
                print("[AI] ⚠️  인증 실패(401) — API 키 확인 필요")
    for char in _fallback(fallback_category):
        _console.print(char, style=style, end='', highlight=False)
        time.sleep(0.02)
    _console.print()

_VOICE = "한 문장, '~다' 마감. 층 번호·직업명·수치 등 입력된 정보를 그대로 옮기지 말 것. 감각과 분위기로만."

def get_floor_narrative(floor, stage, job):
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = (
        f"너는 {persona}.\n"
        f"{job}이 {floor}층으로 내려선다. 이 층의 공기와 예감을 느끼며 한마디 해라.\n"
        f"{_VOICE}"
    )
    _stream_print(prompt, "floor", style="bright_cyan")

def get_shop_narrative(stage):
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = (
        f"너는 {persona}.\n"
        f"전투 사이, 암시장에 발을 들였다. 이 잠깐의 숨통을 느끼며 한마디 해라.\n"
        f"{_VOICE}"
    )
    _stream_print(prompt, "shop", style="bright_green")

def get_boss_narrative(boss_name, stage):
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = (
        f"너는 {persona}.\n"
        f"보스 '{boss_name}' 등장. 이 결전의 무게감을 느끼며 한마디 해라.\n"
        f"{_VOICE}"
    )
    _stream_print(prompt, "boss", style="bright_cyan")

def get_event_narrative(event_name, choice, result, stage):
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = (
        f"너는 {persona}.\n"
        f"'{event_name}' 상황에서 '{choice}'를 택했고, '{result}'. 그 선택의 여운으로 한마디 해라.\n"
        f"{_VOICE}"
    )
    _stream_print(prompt, "event", style="bright_cyan")

def get_battle_intro(monster_name, stage):
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = (
        f"너는 {persona}.\n"
        f"적 '{monster_name}' 출현. 이 조우의 긴장감으로 한마디 해라.\n"
        f"{_VOICE}"
    )
    _stream_print(prompt, "battle", style="bright_cyan")
