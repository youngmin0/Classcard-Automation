import time
import json
import pyautogui
import pytesseract
import os

# ========================= 사용자 설정 부분 =========================

# 1. Tesseract OCR 설치 경로 설정
#    Windows 기본 경로: 'C:/Program Files/Tesseract-OCR/tesseract.exe'
#    설치된 경로를 확인하고 정확하게 입력해주세요. (백슬래시'\' 대신 슬래시'/' 사용)
pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files/Tesseract-OCR/tesseract.exe'

# 2. 화면에서 문제 영역을 캡처할 범위 (x, y, 너비, 높이)
#    그림판 등을 이용해 문제의 뜻이 표시되는 영역의 시작점(x,y)과
#    너비(width), 높이(height)를 미리 측정해서 입력합니다.
#    이 영역 안에 글씨가 꽉 차도록 정확하게 지정해야 인식률이 올라갑니다.
QUESTION_REGION = (859, 618, 2006-859, 816-618) # (x, y, width, height) 예시 값

# 3. 정답 입력창을 클릭할 좌표 (x, y)
#    마찬가지로 정답을 입력하는 칸의 좌표를 지정합니다.
INPUT_BOX_COORD = (1129, 1077) # (x, y) 예시 값

# ====================================================================

def create_answer_dict():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'data.json')
        with open(json_path, 'r', encoding='utf-8') as file:
            card_list = json.load(file)
        # 클래스카드 데이터는 'back'이 뜻, 'front'가 단어입니다.
        answer_dict = {item['back']: item['front'] for item in card_list}
        print("정답 딕셔너리 생성 완료! 총", len(answer_dict), "개의 단어가 로드되었습니다.")
        return answer_dict
    except json.JSONDecodeError:
        print("JSON 데이터 형식이 잘못되었습니다. 복사한 데이터를 확인해주세요.")
        return None

def read_text_from_screen(region, i=0):
    """화면의 특정 영역을 캡처하고 OCR로 텍스트를 읽어옴."""
    screenshot = pyautogui.screenshot(region=region)
    # OCR 인식률을 높이기 위해 이미지를 회색으로 변환.
    grayscale_img = screenshot.convert('L')
    config6 = r'--oem 3 --psm 6'
    config7 = r'--oem 3 --psm 7'
    config_arr = [config6, config7]
    
    text = pytesseract.image_to_string(grayscale_img, lang='kor+eng', config=config_arr[i])
    # 인식된 텍스트의 불필요한 공백이나 줄바꿈을 제거.
    return text.strip()

def main():
    answer_dict = create_answer_dict()
    if not answer_dict:
        return

    print("\n 자동화를 시작합니다. (종료하려면 Ctrl+C를 누르세요)")
    print("---------------------------------------------------------")
    
    try:
        while True:
            # 1. 화면에서 문제 텍스트 읽기
            print("1. 문제 영역에서 텍스트를 읽는 중...")
            question_text1 = read_text_from_screen(QUESTION_REGION)
            question_text1 = question_text1.replace('ㆍ','·').strip()
            question_text1 = question_text1.replace(':',';').strip()
            question_text2 = read_text_from_screen(QUESTION_REGION, 1)
            question_text2= question_text2.replace('ㆍ','·').strip()
            question_text2 = question_text2.replace(':',';').strip()
            
            if not question_text1 and not question_text2:
                print("   -> 텍스트를 인식하지 못했습니다. 2초 후 재시도합니다.")
                time.sleep(2)
                continue
            print(f"   -> 인식된 텍스트: '{question_text1}' 또는 '{question_text2}'")

            # 2. 딕셔너리에서 정답 찾기
            found_key = None
            for key in answer_dict.keys():
                # OCR 텍스트에서 공백을 제거하고, 딕셔너리 키에서 공백을 제거한 후 비교
                if ''.join(question_text1.split()) in ''.join(key.split()) or ''.join(question_text2.split()) in ''.join(key.split()):
                    found_key = key
                    break
            
            if found_key:
                answer = answer_dict[found_key]
                print(f"2. 정답을 찾았습니다! -> '{answer}'")

                # 3. 정답 입력 및 제출
                print("3. 정답을 입력합니다...")
                pyautogui.click(INPUT_BOX_COORD)
                time.sleep(0.2)
                pyautogui.write(answer, interval=0.05)
                time.sleep(0.2)
                pyautogui.press('enter')
                time.sleep(1.5)
                pyautogui.press('space')
                print("---------------------------------------------------------")
                time.sleep(2.5)
            else:
                print("2. 딕셔너리에서 정답을 찾지 못했습니다. OCR이 부정확할 수 있습니다.")
                print("---------------------------------------------------------")
                time.sleep(2.5)

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n오류가 발생했습니다: {e}")

if __name__ == "__main__":

    main()