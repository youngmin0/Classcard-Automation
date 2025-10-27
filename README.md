<a id="readme-top"></a>
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![Unlicense License][license-shield]][license-url]



<br />
<div align="center">
  <a href="https://github.com/youngmin0/Classcard-Automation">
  </a>

  <h3 align="center">Classcard-Automation</h3>

  <p align="center">
    클래스카드(Classcard)의 암기, 리콜, 스펠 학습을 자동화하는 Python 스크립트입니다.
    <br />
    <br />
    <a href="https://github.com/youngmin0/Classcard-Automation/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    &middot;
    <a href="https://github.com/youngmin0/Classcard-Automation/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>



<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details



## About The Project

이 프로젝트는 클래스카드의 반복적인 학습 과정(암기, 리콜, 스펠)을 자동화하여, 학습 시간을 절약하기 위해 개발되었습니다.

Selenium을 사용하여 웹 브라우저를 제어하고, PyAutoGUI로 키보드 및 마우스 입력을 시뮬레이션하며, Pynput을 통해 글로벌 단축키를 지원합니다.

Here's why:
* 🤖 **암기(Memorize) 모드**: 스페이스바 입력을 자동화합니다.
* 🖱️ **리콜(Recall) 모드**: 정답 요소를 자동으로 클릭합니다.
* ⌨️ **스펠(Spell) 모드**: `data.json`의 정답 목록을 기반으로 자동으로 정답을 타이핑합니다.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



### Built With

이 프로젝트는 다음의 주요 라이브러리를 사용하여 빌드되었습니다.

* [![Selenium][Selenium-shield]][Selenium-url]
* [![PyAutoGUI][PyAutoGUI-shield]][PyAutoGUI-url]
* [![Pynput][Pynput-shield]][Pynput-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>



## Getting Started

로컬 환경에서 이 스크립트를 설정하고 실행하기 위한 단계입니다.

### Prerequisites

스크립트 실행을 위해 다음 프로그램과 라이브러리가 필요합니다.

* **Python 3.x**
* **Google Chrome** 브라우저
* **ChromeDriver**: 사용 중인 Chrome 브라우저와 버전이 일치해야 합니다.
* Python 라이브러리 설치:
    ```sh
    pip install selenium pyautogui pynput
    ```

### Installation

1.  GitHub 저장소를 복제(Clone)합니다.
    ```sh
    git clone [https://github.com/youngmin0/Classcard-Automation.git](https://github.com/youngmin0/Classcard-Automation.git)
    ```
2.  프로젝트 폴더로 이동합니다.
    ```sh
    cd Classcard-Automation
    ```
3.  Python 라이브러리를 설치합니다.
    ```sh
    pip install selenium pyautogui pynput
    ```
4.  **ChromeDriver**를 준비합니다.
    * [Chrome 드라이버 다운로드](https://chromedriver.chromium.org/downloads)
    * 다운로드한 `chromedriver.exe` 파일을 `main.py`가 있는 프로젝트 폴더에 복사합니다.
5.  **(필수) `data.json` 정답 파일을 생성합니다.**
    * 클래스카드 학습 세트의 '인쇄' 버튼 > '단어와 뜻' 선택 > 인쇄 미리보기로 이동합니다.
    * `F12`를 눌러 개발자 도구를 열고 'Console' 탭으로 이동합니다.
    * 콘솔에 `JSON.stringify(card_list)` 를 입력하고 실행합니다.
    * 출력된 `[...]` 형태의 텍스트 전체를 복사하여, 프로젝트 폴더에 `data.json` 파일을 만들고 붙여넣기 (인코딩: UTF-8) 후 저장합니다.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



## Usage

1.  터미널에서 `main.py`를 실행합니다.
    ```sh
    python main.py
    ```
2.  자동으로 Chrome 브라우저가 열리면, 클래스카드에 **수동으로 로그인**합니다.
3.  자동화를 원하는 학습 세트 (암기, 리콜, 스펠) 페이지로 이동하여 학습을 시작합니다.
4.  아래 단축키를 사용하여 자동화를 제어합니다.

*  `Ctrl + I` : **암기** 자동화 시작
*  `Ctrl + Y` : **리콜** 자동화 시작
*  `Ctrl + X` : **스펠** 자동화 시작
*  `Ctrl + E` : 현재 자동화 **중지**
*  `Esc` : 프로그램 **전체 종료**

<p align="right">(<a href="#readme-top">back to top</a>)</p>



## Roadmap

- [ ] `data.json` 자동 생성 기능
- [ ] GUI 인터페이스 추가
- [ ] 다른 학습 모드(매칭 등) 지원

See the [open issues](https://github.com/youngmin0/Classcard-Automation/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>



## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

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
* [Font Awesome](https://fontawesome.com)

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
[product-screenshot]: images/screenshot.png
[Selenium-shield]: https://img.shields.io/badge/Selenium-43B02A?style=for-the-badge&logo=selenium&logoColor=white
[Selenium-url]: https://www.selenium.dev/
[PyAutoGUI-shield]: https://img.shields.io/badge/PyAutoGUI-informational?style=for-the-badge&logo=python&logoColor=white
[PyAutoGUI-url]: https://pyautogui.readthedocs.io/
[Pynput-shield]: https://img.shields.io/badge/Pynput-informational?style=for-the-badge&logo=python&logoColor=white
[Pynput-url]: https://pynput.readthedocs.io/
