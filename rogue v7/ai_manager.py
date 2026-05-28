# ai_manager.py - AI 내레이션 담당 (OpenAI)
# API 없어도 게임은 정상 실행됨 (fallback 대사로 자동 대체)
import random

# fallback 대사 - API 실패하거나 키 없을 때 여기서 랜덤 출력
FALLBACKS = {
    "narrative": [
        "어둠 속에서 알 수 없는 기운이 느껴집니다.",
        "운명이 당신의 발걸음을 지켜보고 있습니다.",
        "이 선택이 당신의 마지막이 될 수도 있습니다.",
    ],
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

# OpenAI API 설정
# pip install openai 후 아래에 키 직접 입력
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_API_KEY_HERE")  # 환경변수에서 키 읽어오기, 없으면 플레이스홀더
MODEL_NAME = "gpt-4o-mini"  # 가장 저렴한 모델

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
    STAGE_INFO = {
        1: {"persona": "인간의 말을 배운 숲의 오래된 정령, 고풍스럽고 약간 조롱하는 말투"},
        2: {"persona": "사람의 언어를 구사하는 지하 감시자, 냉정하고 위협적인 짐승 같은 존재"},
    }


def _fallback(category):
    return random.choice(FALLBACKS[category])


def _call_api(prompt):
    if not AI_AVAILABLE:
        return None
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.8
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        err = str(e)
        if "401" in err or "authentication" in err.lower():
            print("[AI] ⚠️  인증 실패(401) — API 키 확인 필요")
        elif "429" in err or "rate" in err.lower():
            pass  # 429는 자주 나와서 조용히 처리
        return None


def get_narrative(situation, stage, job):
    # 층 진입 등 일반 상황 묘사 (현재 미사용 - 필요하면 main.py에서 호출)
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = (
        f"[역할] 너는 로그라이크 게임의 내레이터 '{persona}'이다.\n"
        f"[상황] {situation} (플레이어 직업: {job})\n"
        f"[제약] 수치(HP -10 등)나, 나(내레이터,정령)에 대해선 절대 언급하지 말 것. "
        f"두 문장 이내로, 반드시 '~다'로 끝나는 한국어 서술체로 상황을 묘사할 것."
    )
    return _call_api(prompt) or _fallback("narrative")


def get_floor_narrative(floor, stage, job):
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = (
        f"[역할] {persona}\n"
        f"[상황] 플레이어가 {floor}층에 진입한다. 현재 직업은 {job}이다.\n"
        f"[제약] 두 문장 이내로, 반드시 '~다'로 끝나는 한국어 서술체로 층 진입 분위기를 묘사할 것."
    )
    return _call_api(prompt) or _fallback("floor")


def get_shop_narrative(stage):
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = (
        f"[역할] {persona}\n"
        f"[상황] 플레이어가 상점에 들어섰다.\n"
        f"[제약] 두 문장 이내로, 반드시 '~다'로 끝나는 한국어 서술체로 상점 분위기를 묘사할 것."
    )
    return _call_api(prompt) or _fallback("shop")


def get_boss_narrative(boss_name, stage):
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = (
        f"[역할] {persona}\n"
        f"[상황] 보스 '{boss_name}'이(가) 나타났다.\n"
        f"[제약] 두 문장 이내로, 반드시 '~다'로 끝나는 한국어 서술체로 보스의 압도적인 존재감을 묘사할 것."
    )
    return _call_api(prompt) or _fallback("boss")


def get_event_narrative(event_name, choice, result, stage):
    # 사건 선택 후 결과 묘사 - world.py handle_random_event에서 호출
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = (
        f"[역할] {persona}\n"
        f"[상황] 플레이어가 '{event_name}'에서 '{choice}'를 선택함. 결과: '{result}'\n"
        f"[제약] 수치는 언급하지 말 것. "
        f"두 문장 이내로, 반드시 '~다'로 끝나는 한국어 서술체로 결과를 묘사할 것."
    )
    return _call_api(prompt) or _fallback("event")


def get_battle_intro(monster_name, stage):
    # 전투 시작 시 몬스터 등장 내레이션 - world.py handle_combat에서 호출
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = (
        f"[역할] {persona}\n"
        f"[상황] '{monster_name}'이(가) 등장했다.\n"
        f"[제약] 두 문장 이내로, 반드시 '~다'로 끝나는 한국어 서술체로 위협적인 등장 장면을 묘사할 것."
    )
    return _call_api(prompt) or _fallback("battle")