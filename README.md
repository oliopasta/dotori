# Dotori Bot (도토리 봇) 🐿️

Discord와 Telegram을 연동하여 발로란트(VALORANT), 리그 오브 레전드(LoL)의 경기 일정 및 전적 정보를 제공하는 봇입니다.

## 📋 목차

* [주요 기능]
* [기술 스택]
* [설치 및 실행 방법]
* [환경 변수 설정]
* [사용법]
* [프로젝트 구조]

## ✨ 주요 기능

### Telegram 봇 명령어

#### `/val`

* 발로란트(VALORANT) 예정 경기 일정을 조회합니다.
* 1군 팀(VCT) 경기만 필터링하여 표시합니다.
* 현재 진행 중인 경기(Live)와 예정된 경기를 구분합니다.
* 경기 시간은 한국 시간(KST) 기준입니다.

#### `/vct`

* 현재 진행 중인 VCT 시즌의 대진표(Bracket) 이미지를 조회합니다.
* Pacific, Americas, EMEA, China, Masters/Champions 중 선택 가능합니다.

#### `/lol`

* 리그 오브 레전드(LoL) 예정 경기 일정을 조회합니다.
* 지원 리그: LCK, MSI, Worlds 등 주요 국제전.
* Bo3/Bo5 경기 형식 및 당일 경기 밑줄 표시.

#### `/stat [닉네임]#[태그]`

* 발로란트 플레이어의 전적을 상세 조회합니다.
* 최근 경쟁전 10경기 승패/KDA/점수 변동(RR).
* 현재 티어, K/D, ACS(평균 전투 점수) 통계 제공.
* 시즌 종료일까지 남은 기간 표시.

### Discord 봇

* `/stat [닉네임]#[태그]` 슬래시 커맨드를 지원합니다.
* Telegram 봇과 데이터를 공유하며 백그라운드에서 실행됩니다.

## 🛠 기술 스택

* **Python 3.8+**
* **discord.py**: Discord 봇 프레임워크
* **python-telegram-bot**: Telegram 봇 프레임워크
* **aiohttp**: 비동기 API 요청 처리
* **playwright**: VCT 대진표 스크린샷 캡처 (Headless Browser)
* **python-dotenv**: 환경 변수 관리

## 🚀 설치 및 실행 방법

### 1. 저장소 클론 (Clone)

```bash
git clone https://github.com/your-username/dotori-bot.git
cd dotori-bot

```

### 2. 필수 패키지 설치

`requirements.txt`를 사용하여 필요한 라이브러리를 설치합니다.

```bash
pip install -r requirements.txt

```

### 3. Playwright 브라우저 설치

대진표 캡처 기능을 위해 브라우저 엔진 설치가 필요합니다.

```bash
playwright install chromium

```

### 4. 환경 변수 설정 (.env)

1. 프로젝트 폴더에 있는 `.env.example` 파일의 이름을 `.env`로 변경합니다.
2. `.env` 파일을 열어 각 API 키를 입력합니다. (자세한 내용은 [환경 변수 설정](https://www.google.com/search?q=%23-%ED%99%98%EA%B2%BD-%EB%B3%80%EC%88%98-%EC%84%A4%EC%A0%95) 섹션 참고)

### 5. 봇 실행

```bash
python Dotori.py

```

## 🔐 환경 변수 설정

이 프로젝트는 보안을 위해 `.env` 파일을 사용합니다. **절대 `.env` 파일을 GitHub에 업로드하지 마세요.**

`.env` 파일 형식:

```env
# Discord Settings
DISCORD_TOKEN=여기에_디스코드_봇_토큰_입력

# Telegram Settings
TELEGRAM_TOKEN=여기에_텔레그램_봇_토큰_입력

# API Keys
HENRIK_API_KEY=여기에_HENRIK_VALORANT_API_KEY_입력
LOL_API_KEY=여기에_RIOT_LOL_API_KEY_입력

```

### 키 발급처

* **Discord Token**: [Discord Developer Portal](https://discord.com/developers/applications)
* **Telegram Token**: Telegram의 [@BotFather](https://t.me/botfather)
* **Henrik API Key**: [HenrikDev API](https://api.henrikdev.xyz/dashboard/)
* **LoL API Key**: [Riot Developer Portal](https://vickz84259.github.io/lolesports-api-docs/)

## 📖 사용법

### Telegram

봇 채팅방에서 아래 명령어를 입력하세요.
* `/help`: 봇 전체 명령어 확인
* `/val`: 발로란트 경기 일정 확인
* `/vct`: 대진표 이미지 선택 및 조회
* `/lol`: 롤 경기 일정 확인
* `/stat 이름#태그`: 전적 검색 (예: `/stat 닉네임#KR1`)

### Discord

채팅창에 `/`를 입력하여 슬래시 커맨드를 사용하세요.

* `/stat player:이름#태그`: 전적 검색

## 📂 프로젝트 구조

```text
📦 dotori-bot
 ┣ 📜 .env                # (비공개) 실제 API 키가 저장된 파일
 ┣ 📜 .env.example        # (공개) 환경 변수 템플릿 파일
 ┣ 📜 .gitignore          # Git 업로드 제외 설정
 ┣ 📜 requirements.txt    # 의존성 패키지 목록
 ┗ 📜 Dotori.py           # 봇 메인 소스 코드

```

## ⚠️ 문제 해결

**Q. `ModuleNotFoundError: No module named ...` 오류가 나요.**
A. `pip install -r requirements.txt` 명령어로 패키지를 모두 설치했는지 확인하세요.

**Q. 대진표(`/vct`)가 작동하지 않아요.**
A. `playwright install chromium` 명령어를 실행하여 브라우저를 설치해야 합니다.

**Q. API 오류가 발생해요.**
A. `.env` 파일에 키가 올바르게 입력되었는지, 공백이 포함되지 않았는지 확인하세요.

---

**License**
This project is open source. Feel free to contribute!
