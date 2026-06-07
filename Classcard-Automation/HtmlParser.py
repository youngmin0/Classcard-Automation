import json
import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By


def get_data(driver, output_path='data.json'):
    """
    현재 driver에 로드된 클래스카드 페이지에서 단어/뜻 데이터를 추출하여
    front(단어)/back(뜻) 리스트를 반환한다.

    output_path가 주어지면 그 경로로 data.json도 저장한다.
    output_path가 None이면 파일을 쓰지 않는다 (다계정 병렬 시 공유 파일 충돌 방지).

    HTML 내의 'var study_data = [...]' JavaScript 배열을 파싱해서
    front(단어)와 back(뜻)만 뽑아낸다.
    """
    if driver is None:
        print("[!] 드라이버가 준비되지 않았습니다.")
        return None
    
    try:
        html = driver.page_source
        
        # 1) study_data 배열을 정규식으로 추출
        # var study_data = [...]; 형태에서 [...] 부분만 꺼냄
        match = re.search(r'var\s+study_data\s*=\s*(\[.*?\]);', html, re.DOTALL)
        
        if not match:
            print("[!] study_data를 찾을 수 없습니다. 학습 페이지가 맞는지 확인하세요.")
            return None
        
        json_str = match.group(1)
        study_data = json.loads(json_str)
        
        # 2) front, back만 추려서 새 리스트 생성
        result = []
        for card in study_data:
            # back에 들어있는 \r\n 같은 개행 문자는 그대로 유지하거나
            # 공백으로 바꾸고 싶으면 .replace('\r\n', ' ') 추가
            result.append({
                "front": card.get("front", "").strip(),
                "back": card.get("back", "").strip()
            })
        
        # 3) data.json 파일로 저장 (output_path가 None이면 건너뜀)
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"[Ctrl + M] 데이터 추출 완료! 총 {len(result)}개 카드")
            print(f"    -> {output_path} 파일로 저장되었습니다.")
        else:
            print(f"데이터 추출 완료! 총 {len(result)}개 카드 (파일 저장 안 함)")

        return result
    
    except json.JSONDecodeError as e:
        print(f"[오류] JSON 파싱 실패: {e}")
        return None
    except Exception as e:
        print(f"[오류] 데이터 추출 중 문제 발생: {e}")
        return None
