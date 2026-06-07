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
    클래스카드(Classcard)의 암기, 리콜, 스펠, 테스트 학습을 자동화하는 Python 스크립트입니다.
    단어장 전체 자동 학습(전체 자동화)과 여러 계정 동시(병렬) 실행을 지원합니다.
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
  (계정마다 다른 set이어도 각자 자기 단어장으로 동작)
* **암기(Memorize)**: 단어/문장 암기 자동화
* **리콜(Recall)**: 단어/문장 리콜 자동화
* **스펠(Spell)**: `data.json`의 정답 목록을 기반으로 자동으로 정답을 타이핑.
  전체 자동화에서는 선생님이 **필수로 지정한 단어 set**에서만 수행(자율이면 건너뜀)
* **테스트(Test, 단어)**: 단어 객관식 테스트 자동 풀이. `data.json` 기반 양방향(영↔한) 매칭으로
  정답 보기를 골라 입력. 항상 100점이 되지 않도록 일부 문항은 랜덤 오답 처리(단, **70점 초과 보장**).
  탭/창 포커스를 잃어도 '이탈'로 잡히지 않아 **백그라운드 실행** 가능
* **테스트(Test, 문장)**: 문장 어순 배열 테스트 자동 풀이. 한글 문제 → `data.json`에서 영어 정답
  문장을 찾아 스크램블 단어를 어순대로 클릭. 실시간 채점에 대응하기 위해 **CDP 트러스티드 클릭**으로
  입력하며, 괄호 묶음 `(...)`·대소문자 중복(`The`/`the`)·구두점 차이를 모두 정규화해 매칭.
  0~1개만 랜덤 오답 처리(**90점 패스 기준** 안전 통과). 단어 테스트와 동일하게 **백그라운드 실행** 가능
* **매칭(Matching, 단어)**: 영어↔한국어 카드 매칭 게임 자동 풀이. 페이지의 `card_list`를
  직접 읽어 짝을 찾아 클릭. 목표 점수(**1000~2000점 랜덤**)에 도달하면 게임 도중에
  자동으로 빠져나옴(필수 1000점 충족, 점수 저장됨). **백그라운드 실행** 가능
* **스크램블(Scramble, 문장)**: 문장 어순 배열 게임 자동 풀이. 페이지의 `study_data`를
  읽어 한글 문제에 해당하는 영어 문장을 찾고, 단어 타일을 어순대로 클릭. 목표 점수
  (**4000~5000점 랜덤**)에 도달하면 빠져나옴(필수 4000점 충족, 점수 저장됨). **백그라운드 실행** 가능
* **단어장 가져오기**: 현재 페이지에서 단어 데이터를 `data.json`으로 추출
* **전체 자동화(AutoAll)**: 단어장 목록 페이지에서 맨 아래 set부터 위로 올라가며
  단어/문장 자동 판별 → 학습구간을 '전체 카드 학습'으로 변경 → `data.json` 자동 업데이트 →
  암기 → 리콜 → 스펠 → 매칭/스크램블 → 테스트를 차례로 수행
  (단어 set은 (필수면)스펠+매칭+단어 테스트, 문장 set은 스크램블+문장 테스트).
  이미 완료된 모드와 set은 자동으로 스킵
  (테스트는 최고점수가 단어 70점 / 문장 90점, 매칭은 1000점 / 스크램블은 4000점 이상이면 스킵)
* **한 세트 자동화**: 셋홈(set 상세) 페이지를 열어둔 상태에서 `Ctrl + Alt + S`를 누르면
  그 한 set만 전체 모드(암기→리콜→(필수면)스펠→매칭/스크램블→테스트)를 수행하고 멈춤

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

1. 터미널에서 `main.py`를 실행합니다.
```sh
cd Classcard-Automation
python main.py
```
2. Chrome 브라우저가 열리고 자동으로 로그인됩니다. (`.env` 미설정 시 수동 로그인)
   - 여러 계정을 설정한 경우 계정 수만큼 창이 열리며, 아래 단축키는 **모든 계정에 동시에** 적용됩니다.
3. 자동화 방식 선택:
   - **개별 모드**: 학습 세트 페이지로 직접 이동한 뒤 `Ctrl + M`으로 단어 추출 → 원하는 모드 단축키 사용
   - **전체 자동화**: 단어장 목록 페이지(여러 set이 보이는 페이지)에서 `Ctrl + A` 한 번. 맨 아래 set부터 위로 순차 처리
4. 아래 단축키를 사용하여 자동화를 제어합니다.

| 단축키 | 기능 |
|--------|------|
| `Ctrl + A` | **전체 자동화** 시작 (단어장 목록 페이지에서) |
| `Ctrl + Alt + S` | **한 세트 자동화** 시작 (열어둔 셋홈 페이지에서) |
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
- [ ] GUI 인터페이스 추가

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
