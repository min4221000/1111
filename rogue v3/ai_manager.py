# ai_manager.py
import time

try:
    import google.generativeai as genai
    from config import GEMINI_API_KEY, MODEL_NAME
    from assets import STAGE_INFO
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
    AI_AVAILABLE = True
except Exception:
    AI_AVAILABLE = False
    STAGE_INFO = {
        1: {"persona": "친절하고 몽환적인 안내자"},
        2: {"persona": "냉혹하고 분석적인 감시자"},
        3: {"persona": "파괴적이고 거친 전사"},
        4: {"persona": "오만한 신의 대리인"},
        5: {"persona": "광기 어린 목소리"}
    }

# Fallback 대사 모음
FALLBACKS = {
    "narrative": [
        "어둠 속에서 알 수 없는 기운이 느껴집니다.",
        "운명이 당신의 발걸음을 지켜보고 있습니다.",
        "이 선택이 당신의 마지막이 될 수도 있습니다.",
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

import random

def _fallback(category):
    return random.choice(FALLBACKS[category])

def _call_api(prompt):
    if not AI_AVAILABLE:
        return None
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return None

def get_narrative(situation, stage, job):
    """일반 상황 묘사"""
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = f"""
[역할] 너는 로그라이크 게임의 내레이터 '{persona}'이다.
[상황] {situation} (플레이어 직업: {job})
[제약] 수치(HP -10 등)는 절대 언급하지 말 것. 반드시 두 문장 이내로 답할 것.
"""
    return _call_api(prompt) or _fallback("narrative")

def get_event_narrative(event_name, choice, result, stage):
    """사건 결과 묘사"""
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = f"""
[역할] {persona}
[상황] 플레이어가 '{event_name}'에서 '{choice}'를 선택함. 결과: '{result}'
[제약] 수치는 언급하지 말 것. 두 문장 이내로 결과를 묘사할 것.
"""
    return _call_api(prompt) or _fallback("event")

def get_battle_intro(monster_name, stage):
    """전투 시작 등장 대사"""
    persona = STAGE_INFO.get(stage, STAGE_INFO[1])['persona']
    prompt = f"""
[역할] {persona}
[상황] '{monster_name}'이(가) 등장했다.
[제약] 두 문장 이내로 위협적인 등장 대사를 만들 것.
"""
    return _call_api(prompt) or _fallback("battle")
