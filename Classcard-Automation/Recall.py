import time
import pyautogui


##       f12 콘솔에 아래 명령어 입력       ##########################################################
# let a=document.getElementsByClassName("answer"); for (var i=0;i<a.length;i++) {
# 	a[i].classList.add("show-answer");
# }
##################################################################################################



# ================= 사용자 설정 부분 =================

# (1) 노란색을 감지할 세 좌표 (x, y)
#     화면에서 미리 마우스 좌표를 확인해 아래에 넣어 주세요.
COORD_TOP    = (1949, 949)   # 예시: 맨 위 위치
COORD_MIDDLE = (1949, 1051)   # 예시: 중간 위치
COORD_BOTTOM = (1949, 1146)   # 예시: 맨 밑 위치2

# (2) “아까 알려준 노란색” RGB 값
#     제공해주신 첫 번째 이미지에서 추출한 대표 픽셀값 중 하나를 사용했습니다.
#     (129, 211, 51) 은 진한 노란-녹색 계열이므로, 이 값에 ± 허용 오차를 둡니다.
TARGET_YELLOW   = (146, 205, 74)  # RGB

# (3) 색상 비교 허용 오차 (0~255)
#     R·G·B 각각이 ±30 이내면 같은 노란색으로 인식합니다.
#     필요에 따라 조정하세요 (예: ±20 ~ ±50 사이가 무난).
COLOR_TOLERANCE = 30

# (4) 루프 실행 간격 (초)
SLEEP_INTERVAL = 3.5

# ====================================================


def get_pixel_color(x, y):
    """
    화면에서 (x, y) 좌표 픽셀의 RGB 값을 읽어와서 반환합니다.
    pyautogui.screenshot(region=(x, y, 1, 1)) 을 사용하여 1x1 픽셀 이미지를 얻고,
    getpixel((0,0)) 으로 RGB 값을 추출합니다. (RGBA 중 RGB만 사용)
    """
    img = pyautogui.screenshot(region=(x, y, 1, 1))
    return img.getpixel((0, 0))[:3]  # (R, G, B)


def color_matches(target_rgb, sample_rgb, tol=0):
    """
    두 RGB 튜플(target_rgb, sample_rgb)을 tol 오차 내에서 비교하여 True/False를 반환합니다.
    tol = 0 이면 완벽 일치만, tol > 0 이면 각 채널 차이가 tol 이내라면 True.
    """
    r1, g1, b1 = target_rgb
    r2, g2, b2 = sample_rgb
    return (
        abs(r1 - r2) <= tol and
        abs(g1 - g2) <= tol and
        abs(b1 - b2) <= tol
    )


def main():
    print("=== 3초마다 세 좌표에서 노란색 감지 → 1/2/3 키 입력 프로그램 ===")
    print("좌표(상→중→하):", COORD_TOP, COORD_MIDDLE, COORD_BOTTOM)
    print("목표 노란색:", TARGET_YELLOW, "허용 오차:", COLOR_TOLERANCE)
    print("종료하려면 터미널에서 Ctrl+C 를 누르세요.\n")

    try:
        while True:
            # 1) 세 좌표의 픽셀 색상 읽기
            color_top    = get_pixel_color(*COORD_TOP)
            color_mid    = get_pixel_color(*COORD_MIDDLE)
            color_bottom = get_pixel_color(*COORD_BOTTOM)

            # 2) 각 좌표가 노란색인지 검사하여, 매칭되는 위치에 해당하는 키 입력
            if color_matches(TARGET_YELLOW, color_top, COLOR_TOLERANCE):
                print(f"[감지] TOP 좌표 {COORD_TOP} → 색 {color_top} ≒ 노란색 → 키 '1' 입력")
                pyautogui.press('1')

            elif color_matches(TARGET_YELLOW, color_mid, COLOR_TOLERANCE):
                print(f"[감지] MID 좌표 {COORD_MIDDLE} → 색 {color_mid} ≒ 노란색 → 키 '2' 입력")
                pyautogui.press('2')

            elif color_matches(TARGET_YELLOW, color_bottom, COLOR_TOLERANCE):
                print(f"[감지] BOTTOM 좌표 {COORD_BOTTOM} → 색 {color_bottom} ≒ 노란색 → 키 '3' 입력")
                pyautogui.press('3')

            else:
                # 세 좌표 중 어느 곳도 노란색이 아니면 건너뜀
                print(f"[미감지] 세 좌표 색상 → {color_top}, {color_mid}, {color_bottom}")

            # 3) 다음 검사 전 대기
            time.sleep(SLEEP_INTERVAL)

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")


if __name__ == "__main__":
    main()
