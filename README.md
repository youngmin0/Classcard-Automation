<a id="readme-top"></a>
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![Unlicense License][license-shield]][license-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/youngmin0/Classcard-Automation">
    <img src="https://play-lh.googleusercontent.com/howCUVHqn67CQ_1VuMAICY7FIwUGT-4c6_Tcii_9z0dE1_2ZN2vA8Ny1EMkJVYMGBQUw" alt="Classcard" width="80" height="80">
  </a>

  <h3 align="center">Classcard Automation</h3>

  <p align="center">
    클래스카드(Classcard)의 암기, 리콜, 스펠, 매칭/스크램블, 테스트 학습을 자동화하는 Python 스크립트입니다.
    세트·모드를 골라 돌리는 전체 자동화(선택 창)와 여러 계정 동시(병렬) 실행을 지원합니다.
    <br />
    <a href="https://github.com/youngmin0/Classcard-Automation"><strong>GitHub »</strong></a>
    <br />
    <br />
  </p>
</div>

<br />

## About The Project

이 프로젝트는 클래스카드의 반복적인 학습 과정(암기, 리콜, 스펠, 테스트)을 자동화하여, 학습 시간을 절약하기 위해 개발되었습니다.

Selenium을 사용하여 웹 브라우저를 제어하고, Pynput을 통해 글로벌 단축키를 지원합니다.

* **자동 로그인**: `.env` 파일의 ID/PW로 자동 로그인
* **다계정 병렬 실행**: `.env`에 여러 계정을 적으면(쉼표 구분) `python main.py` 한 번으로
  계정 수만큼 크롬 창이 열려 각각 로그인. 단축키 한 번이면 **모든 계정이 동시에** 같은 자동화를 수행
  (계정마다 다른 set이어도 각자 자기 단어장으로 동작).
  창은 데스크톱 레이아웃 유지를 위해 큰 크기로 계단식으로 겹쳐 띄웁니다. 포커스가 없거나 창이
  겹쳐도 백그라운드에서 정상 동작하니, **창 크기를 줄이지 마세요**(좁아지면 클래스카드가 모바일
  레이아웃으로 바뀌어 문장 테스트/리콜 등이 깨집니다).
* **암기(Memorize)**: 단어/문장 암기 자동화
* **리콜(Recall)**: 단어/문장 리콜 자동화
* **스펠(Spell)**: `data.json`의 정답 목록을 기반으로 자동으로 정답을 타이핑.
  전체 자동화에서는 선생님이 **필수로 지정한 단어 set**에서만 수행(자율이면 건너뜀)
* **테스트(Test, 단어)**: 단어 객관식 테스트 자동 풀이. `data.json` 기반 양방향(영↔한) 매칭으로
  정답 보기를 골라 입력. 항상 100점이 되지 않도록 목표 점수(기본 **90~100점 랜덤**, 설정 가능)에 맞춰
  일부 문항을 랜덤 오답 처리.
  탭/창 포커스를 잃어도 '이탈'로 잡히지 않아 **백그라운드 실행** 가능
* **테스트(Test, 문장)**: 문장 어순 배열 테스트 자동 풀이. 한글 문제 → `data.json`에서 영어 정답
  문장을 찾아 스크램블 단어를 어순대로 클릭. 실시간 채점에 대응하기 위해 **CDP 트러스티드 클릭**으로
  입력하며, 괄호 묶음 `(...)`·대소문자 중복(`The`/`the`)·구두점 차이를 모두 정규화해 매칭.
  목표 점수(기본 **100점**, 설정 가능)에 맞춰 랜덤 오답 처리. 단어 테스트와 동일하게 **백그라운드 실행** 가능
* **매칭(Matching, 단어)**: 영어↔한국어 카드 매칭 게임 자동 풀이. 페이지의 `card_list`를
  직접 읽어 짝을 찾아 클릭. 목표 점수(기본 **3000~5000점 랜덤**, 설정 가능)에 도달하면 게임 도중에
  자동으로 빠져나옴(점수 저장됨). **백그라운드 실행** 가능
* **스크램블(Scramble, 문장)**: 문장 어순 배열 게임 자동 풀이. 페이지의 `study_data`를
  읽어 한글 문제에 해당하는 영어 문장을 찾고, 단어 타일을 어순대로 클릭. 목표 점수
  (기본 **4000~5000점 랜덤**, 설정 가능)에 도달하면 빠져나옴(점수 저장됨). **백그라운드 실행** 가능
* **단어장 가져오기**: 현재 페이지에서 단어 데이터를 `data.json`으로 추출
* **전체 자동화(AutoAll)**: 단어장 목록 페이지에서 `Ctrl + A`를 누르면 **선택 창**이 뜹니다.
  브라우저에서 읽어온 **세트 목록**(체크박스, 전체 선택/해제 버튼), 수행할 **모드**
  (암기 / 리콜 / 스펠 / 매칭·스크램블 / 테스트), **점수 설정**을 고르고 시작하면
  체크한 세트만 맨 아래부터 위로 올라가며 처리합니다. 다계정이면 계정마다 창이 차례로 뜹니다.
  세트마다 단어/문장 자동 판별 → 학습구간을 '전체 카드 학습'으로 변경 → 단어장 자동 추출 →
  암기 → 리콜 → (필수면)스펠 → 매칭/스크램블 → 테스트 순으로 수행하며, 체크하지 않은 모드와
  이미 완료된 모드(통과 기준 이상)는 스킵합니다.
* **점수 설정**: 선택 창 아래쪽에서 단어 테스트 / 문장 테스트 / 매칭 / 스크램블 각각의
  **통과 기준**(셋홈 최고점수가 이 이상이면 완료로 보고 스킵)과 **목표 점수 하한~상한**
  (실제로 낼 점수, 세트마다 이 범위에서 랜덤)을 바꿀 수 있습니다. 값은 `settings.json`에 저장되어
  다음 실행에도 유지되고, 개별 모드 단축키에도 적용됩니다.

  | | 통과 기준 | 목표 하한 | 목표 상한 |
  |---|---|---|---|
  | 단어 테스트 (0~100) | 70 | 90 | 100 |
  | 문장 테스트 (0~100) | 90 | 100 | 100 |
  | 매칭 | 1000 | 3000 | 5000 |
  | 스크램블 | 4000 | 4000 | 5000 |
* **한 세트 자동화**: 셋홈(set 상세) 페이지를 열어둔 상태에서 `Ctrl + Alt + S`를 누르면
  모드/점수 선택 창(세트 목록 없음)이 뜨고, 그 한 set만 고른 모드로 수행하고 멈춤

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

* [![Selenium][Selenium-shield]][Selenium-url]
* [![Pynput][Pynput-shield]][Pynput-url]
* [![BeautifulSoup][BeautifulSoup-shield]][BeautifulSoup-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

로컬 환경에서 이 스크립트를 설정하고 실행하기 위한 단계입니다.

### Prerequisites

* **Python 3.x**
* **Google Chrome** 브라우저

### Installation

1. GitHub 저장소를 복제(Clone)합니다.
```sh
git clone https://github.com/youngmin0/Classcard-Automation.git
```
2. 프로젝트 폴더로 이동합니다.
```sh
cd Classcard-Automation
```
3. Python 라이브러리를 설치합니다.
```sh
pip install -r requirements.txt
```
4. `.env.example`을 복사하여 `.env` 파일을 만들고 클래스카드 ID/PW를 입력합니다.
```sh
cp Classcard-Automation/.env.example Classcard-Automation/.env
```
```
CLASSCARD_ID=내_아이디
CLASSCARD_PW=내_비밀번호
```
여러 계정을 동시에 돌리려면 쉼표(,)로 구분해 적습니다. (ID와 PW의 순서·개수를 맞출 것)
```
CLASSCARD_ID=계정1,계정2,계정3
CLASSCARD_PW=비번1,비번2,비번3
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

1. `start.bat`을 더블클릭하거나, 터미널에서 `main.py`를 실행합니다.
```sh
cd Classcard-Automation
python main.py
```
   프로그램이 띄운 크롬 창은 직접 닫지 마세요. 닫았다면 `Ctrl + Esc`로 종료 후 다시 실행합니다.
2. Chrome 브라우저가 열리고 자동으로 로그인됩니다. (`.env` 미설정 시 수동 로그인)
   - 여러 계정을 설정한 경우 계정 수만큼 창이 열리며, 아래 단축키는 **모든 계정에 동시에** 적용됩니다.
3. 자동화 방식 선택:
   - **개별 모드**: 학습 세트 페이지로 직접 이동한 뒤 `Ctrl + M`으로 단어 추출 → 원하는 모드 단축키 사용
   - **전체 자동화**: 단어장 목록 페이지(여러 set이 보이는 페이지)에서 `Ctrl + A` → 선택 창에서
     세트·모드·점수를 고르고 시작. 체크한 세트를 맨 아래부터 위로 순차 처리
4. 아래 단축키를 사용하여 자동화를 제어합니다.

| 단축키 | 기능 |
|--------|------|
| `Ctrl + A` | **전체 자동화** — 세트/모드/점수 선택 창 (단어장 목록 페이지에서) |
| `Ctrl + Alt + S` | **한 세트 자동화** — 모드/점수 선택 창 (열어둔 셋홈 페이지에서) |
| `Ctrl + I` | **암기** 자동화 시작 |
| `Ctrl + Y` | **리콜** 자동화 시작 |
| `Ctrl + X` | **스펠** 자동화 시작 |
| `Ctrl + B` | **문장 암기** 자동화 시작 |
| `Ctrl + Q` | **문장 리콜** 자동화 시작 |
| `Ctrl + Alt + G` | **단어 테스트** 자동화 시작 |
| `Ctrl + Alt + H` | **문장 테스트** 자동화 시작 |
| `Ctrl + Alt + J` | **단어 매칭** 자동화 시작 |
| `Ctrl + Alt + K` | **문장 스크램블** 자동화 시작 |
| `Ctrl + M` | **단어장 가져오기** (현재 페이지에서 데이터 추출) |
| `Ctrl + E` | 현재 자동화 **중지** |
| `Ctrl + Esc` | 프로그램 **전체 종료** (브라우저 닫힘) |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Roadmap

- [x] 자동 로그인 기능
- [x] 단어장 자동 추출 기능
- [x] 문장 암기/리콜 지원
- [x] 단어장 전체 자동화 (Ctrl + A)
- [x] 단어 테스트 자동화 (Ctrl + Alt + G) + 백그라운드 실행
- [x] 문장 테스트 자동화 (Ctrl + Alt + H) + 백그라운드 실행
- [x] 단어 매칭 자동화 (Ctrl + Alt + J) + 백그라운드 실행
- [x] 문장 스크램블 자동화 (Ctrl + Alt + K) + 백그라운드 실행
- [x] 다계정 동시(병렬) 실행
- [x] 전체 자동화 세트/모드/점수 선택 창 (Ctrl + A)

See the [open issues](https://github.com/youngmin0/Classcard-Automation/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Top contributors:

<a href="https://github.com/youngmin0/Classcard-Automation/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=youngmin0/Classcard-Automation" alt="contrib.rocks image" />
</a>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## License

Distributed under the Unlicense License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contact

youngmin0

Project Link: [https://github.com/youngmin0/Classcard-Automation](https://github.com/youngmin0/Classcard-Automation)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Acknowledgments

* [Img Shields](https://shields.io)
* [Choose an Open Source License](https://choosealicense.com)
* [Best-README-Template](https://github.com/othneildrew/Best-README-Template)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

[contributors-shield]: https://img.shields.io/github/contributors/youngmin0/Classcard-Automation.svg?style=for-the-badge
[contributors-url]: https://github.com/youngmin0/Classcard-Automation/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/youngmin0/Classcard-Automation.svg?style=for-the-badge
[forks-url]: https://github.com/youngmin0/Classcard-Automation/network/members
[stars-shield]: https://img.shields.io/github/stars/youngmin0/Classcard-Automation.svg?style=for-the-badge
[stars-url]: https://github.com/youngmin0/Classcard-Automation/stargazers
[issues-shield]: https://img.shields.io/github/issues/youngmin0/Classcard-Automation.svg?style=for-the-badge
[issues-url]: https://github.com/youngmin0/Classcard-Automation/issues
[license-shield]: https://img.shields.io/github/license/youngmin0/Classcard-Automation.svg?style=for-the-badge
[license-url]: https://github.com/youngmin0/Classcard-Automation/blob/master/LICENSE.txt
[Selenium-shield]: https://img.shields.io/badge/Selenium-43B02A?style=for-the-badge&logo=selenium&logoColor=white
[Selenium-url]: https://www.selenium.dev/
[Pynput-shield]: https://img.shields.io/badge/Pynput-informational?style=for-the-badge&logo=python&logoColor=white
[Pynput-url]: https://pynput.readthedocs.io/
[BeautifulSoup-shield]: https://img.shields.io/badge/BeautifulSoup-informational?style=for-the-badge&logo=python&logoColor=white
[BeautifulSoup-url]: https://www.crummy.com/software/BeautifulSoup/
