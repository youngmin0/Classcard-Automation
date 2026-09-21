import time
from selenium.common.exceptions import NoSuchWindowException


# 완료 판정 결과
_NOT_DONE = 0
_END_SCREEN = 1   # 종료 화면(#study_end)이 떠 있음
_ALL_KNOWN = 2    # 학습 화면 상단 카운터(✓ known | total)가 다 참 = 1회독(100%) 완료

# 주의: `.next-repeat-percent`는 진행률이 아니라 종료 화면의 '200%까지 반복' 버튼 안 고정 텍스트라
# 완료 판정에 쓸 수 없다. 실제 진행은 `.known_count` / `.total_count` 카운터로 본다.
_DONE_JS = r'''
    var btns = document.querySelectorAll(".btn-study-end-repeat");
    for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent !== null) return 1;
    }
    if (document.querySelectorAll("#study_end.active").length > 0) return 1;

    function visibleInt(sel) {
        var els = document.querySelectorAll(sel);
        for (var i = 0; i < els.length; i++) {
            if (els[i].offsetParent === null) continue;
            var v = parseInt(els[i].textContent);
            if (!isNaN(v)) return v;
        }
        return -1;
    }
    var total = visibleInt(".total_count");
    var known = visibleInt(".known_count");
    if (total <= 0 || known < 0) return 0;
    if (known >= total) return 2;

    // 다 찬 순간을 폴링이 놓치면 카운터가 0으로 돌아가며 2회독(200%)이 시작된다.
    // 절반 넘게 찼던 카운터가 줄어들면 1회독이 끝난 것으로 판정한다.
    var peak = window.__cc_known_peak || 0;
    if (peak * 2 >= total && known < peak) return 2;
    if (known > peak) window.__cc_known_peak = known;
    return 0;
'''


def reset_progress(driver):
    """모드 시작 시 카운터 최댓값 기록을 초기화."""
    try:
        driver.execute_script('window.__cc_known_peak = 0;')
    except NoSuchWindowException:
        raise
    except Exception:
        pass


def check_step2_success_and_stop(driver, stop_event):
    """완료 종료 판단: 종료 화면(`.btn-study-end-repeat` visible / `#study_end.active`) 또는
    카운터 known_count >= total_count (1회독 완료) 또는 카운터가 최댓값에서 감소(2회독 시작).
    완료면 set 페이지로 복귀 후 stop. 종료 화면에서 SPACE가 눌리면 200% 반복이 시작되므로
    호출자는 키 입력 전에 반드시 이 함수를 먼저 확인해야 한다."""
    try:
        done = driver.execute_script(_DONE_JS)
        if not done:
            return False
        if done == _ALL_KNOWN:
            # 마지막 카드 학습 기록이 서버에 저장될 시간을 준다
            time.sleep(1.0)
        driver.execute_script(
            'var a = document.querySelectorAll("#study_end.active .study-header a"); if (a.length) a[0].click();'
        )
        driver.execute_script(
            'var a = document.querySelectorAll(".btn-top-menu a"); if (a.length) a[0].click();'
        )
        time.sleep(0.5)
        driver.execute_script(
            'var a = document.querySelectorAll(".close_o"); if (a.length) a[0].click();'
        )
        stop_event.set()
        return True
    except NoSuchWindowException:
        raise
    except Exception:
        return False
