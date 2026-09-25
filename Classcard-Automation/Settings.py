import json
import os

# 점수 관련 설정. settings.json(이 파일과 같은 폴더)에 저장되어 프로그램을 다시 켜도 유지된다.
# *_pass: 셋홈에서 이 점수 이상이면 완료로 보고 스킵.  *_min/*_max: 실제로 낼 목표 점수 범위(랜덤).
_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')

DEFAULTS = {
    'test_pass': 70, 'test_min': 90, 'test_max': 100,              # 단어 테스트 (0~100점)
    'sent_test_pass': 90, 'sent_test_min': 100, 'sent_test_max': 100,  # 문장 테스트 (0~100점)
    'match_pass': 1000, 'match_min': 3000, 'match_max': 5000,      # 매칭 (단어)
    'scramble_pass': 4000, 'scramble_min': 4000, 'scramble_max': 5000,  # 스크램블 (문장)
}

# 화면 표시용: (행 이름, 키 접두어, 상한값)
GROUPS = [
    ('단어 테스트', 'test', 100),
    ('문장 테스트', 'sent_test', 100),
    ('매칭', 'match', None),
    ('스크램블', 'scramble', None),
]

_values = dict(DEFAULTS)


def load():
    global _values
    try:
        with open(_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _values = dict(DEFAULTS)
        for k in DEFAULTS:
            if isinstance(data.get(k), int):
                _values[k] = data[k]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        _values = dict(DEFAULTS)
    return dict(_values)


def save(values):
    global _values
    _values = dict(DEFAULTS)
    _values.update({k: int(v) for k, v in values.items() if k in DEFAULTS})
    try:
        with open(_PATH, 'w', encoding='utf-8') as f:
            json.dump(_values, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[!] settings.json 저장 실패: {e}")


def get(key):
    return _values.get(key, DEFAULTS[key])


def validate(values):
    """입력값 검사. 문제가 있으면 안내 문자열, 없으면 None."""
    for label, prefix, limit in GROUPS:
        try:
            p = int(values[f'{prefix}_pass'])
            lo = int(values[f'{prefix}_min'])
            hi = int(values[f'{prefix}_max'])
        except (KeyError, TypeError, ValueError):
            return f"{label}: 숫자를 입력하세요."
        if min(p, lo, hi) < 0:
            return f"{label}: 0 이상이어야 합니다."
        if limit is not None and max(p, lo, hi) > limit:
            return f"{label}: {limit} 이하여야 합니다."
        if lo > hi:
            return f"{label}: 하한이 상한보다 큽니다."
    return None


load()
