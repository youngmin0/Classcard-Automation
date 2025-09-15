import time
import pyautogui

# ================= 사용자 설정 부분 =================

# (1) 초록색을 감지할 세 좌표 (x, y)
COORD  = (960, 1173)

# (2) 초록색 RGB 값
TARGET_YELLOW   = (146, 205, 74) 

# (3) 색상 비교 허용 오차 (0~255)
COLOR_TOLERANCE = 30

# (4) 루프 실행 간격 (초)
SLEEP_INTERVAL = 0.5

# ====================================================


def get_pixel_color(x, y):
    img = pyautogui.screenshot(region=(x, y, 1, 1))
    return img.getpixel((0, 0))[:3]  # (R, G, B)


def color_matches(target_rgb, sample_rgb, tol=0):
    r1, g1, b1 = target_rgb
    r2, g2, b2 = sample_rgb
    return (
        abs(r1 - r2) <= tol and
        abs(g1 - g2) <= tol and
        abs(b1 - b2) <= tol
    )


def main():
    print("=== 3초마다 세 좌표에서 초록색 감지 → 1/2/3 키 입력 프로그램 ===")
    print("좌표:", COORD)
    print("목표 초록색:", TARGET_YELLOW, "허용 오차:", COLOR_TOLERANCE)
    print("종료하려면 터미널에서 Ctrl+C 를 누르세요.\n")

    try:
        while True:
            # 1) 세 좌표의 픽셀 색상 읽기
            color = get_pixel_color(*COORD)

            # 2) 각 좌표가 초록색인지 검사하여, 매칭되는 위치에 해당하는 키 입력
            if color_matches(TARGET_YELLOW, color, COLOR_TOLERANCE):
                print(f"[감지] TOP 좌표 {COORD} → 색 {color} ≒ 초록색 → 키 'shift' 입력")
                pyautogui.press('space')
                time.sleep(0.2)
                pyautogui.hotkey('shift', 'enter')
            else:
                # 세 좌표 중 어느 곳도 초록색이 아니면 건너뜀
                print(f"[미감지] 세 좌표 색상 → {color}")

            # 3) 다음 검사 전 대기
            time.sleep(SLEEP_INTERVAL)

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")

if __name__ == "__main__":
    main()
