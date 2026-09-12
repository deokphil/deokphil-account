# 덕필 계좌 관리 시스템

카드 게임/학급 그룹의 계좌(잔액)와 거래 내역을 관리하는 미니 은행 앱.
최종 배포 목표: `https://deokphil.onrender.com`

## 1단계: 윈도우 + VS Code 개발 환경 세팅

### 1) 필수 프로그램 설치
- **Python 3.10 이상** (3.10.8이면 충분): https://www.python.org/downloads/ 에서 설치
  - 설치 화면에서 **"Add Python to PATH"** 체크박스 반드시 체크
- **VS Code**: https://code.visualstudio.com/
- VS Code 실행 후 확장(Extensions)에서 **"Python"** (Microsoft 제공) 설치

### 2) 프로젝트 폴더 열기
1. 압축을 푼 `deokphil-account` 폴더를 원하는 위치(예: `C:\projects\`)에 둡니다.
2. VS Code에서 `파일 > 폴더 열기`로 이 폴더를 엽니다.

### 3) 가상환경(venv) 생성 및 활성화
VS Code 상단 메뉴 `터미널 > 새 터미널`을 열고 아래 명령을 순서대로 입력합니다.

```powershell
python -m venv .venv
.venv\Scripts\activate
```

터미널 프롬프트 앞에 `(.venv)`가 붙으면 성공입니다.

> 만약 "이 시스템에서 스크립트 실행이 금지되어 있습니다" 오류가 나오면,
> PowerShell을 관리자 권한으로 열어 아래 명령을 한 번만 실행하세요.
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

### 4) 패키지 설치

```powershell
pip install -r requirements.txt
```

### 5) 환경변수 파일 생성

`.env.example` 파일을 복사해서 같은 위치에 `.env` 라는 이름으로 저장합니다.
로컬 개발 단계에서는 내용을 그대로 두어도 됩니다 (SQLite 자동 사용).

### 6) 서버 실행

```powershell
uvicorn app.main:app --reload
```

터미널에 아래와 같이 뜨면 정상 실행된 것입니다.

```
Uvicorn running on http://127.0.0.1:8000
```

### 7) 브라우저에서 확인

- 메인 화면: http://127.0.0.1:8000
- API 자동 문서(Swagger): http://127.0.0.1:8000/docs
- 서버 상태 확인: http://127.0.0.1:8000/health

메인 화면 상단에 **"덕필 계좌 관리 시스템"** 타이틀이 보이면 1단계 완료입니다.

## 현재 폴더 구조

```
deokphil-account/
├── app/
│   ├── main.py          # FastAPI 앱 진입점
│   ├── database.py      # DB 연결 설정 (SQLite ↔ Postgres 자동 전환)
│   ├── models.py        # 데이터 모델 (User, Group, Member, Transaction 등)
│   ├── routers/          # (다음 단계에서 추가될 API 라우트)
│   ├── templates/        # HTML 화면
│   └── static/           # CSS
├── requirements.txt
├── .env.example
└── README.md
```

## 2단계: 수퍼유저 로그인 및 그룹/관리자 생성

`.env` 파일의 `SUPERUSER_USERNAME` / `SUPERUSER_PASSWORD` 값으로 최초 수퍼유저 계정이
서버 시작 시 자동 생성됩니다 (기본값: `admin` / `changeme123`).

1. `http://127.0.0.1:8000/login` 에서 위 계정으로 로그인
2. 수퍼유저 대시보드에서 **그룹 생성** (제로섬/개방형 선택, 시드머니, 단위 지정)
3. 같은 화면에서 **그룹 관리자 계정 생성** (담당 그룹 선택)
4. 로그아웃 후 방금 만든 관리자 계정으로 재로그인하면 `/admin`으로 이동 시도
   (3단계에서 실제 관리자 대시보드를 만들 예정이라 현재는 페이지가 아직 없습니다)

> 운영 배포 전에는 반드시 `.env`의 `SUPERUSER_PASSWORD`와 `SECRET_KEY`를
> 무작위 문자열로 교체하세요.

## 3단계: 그룹 관리자 대시보드 (멤버/거래 관리)

2단계에서 만든 관리자 계정으로 로그인하면 `/admin`으로 이동합니다.

1. 담당 그룹 탭을 클릭해서 선택
2. **멤버 추가**: 이름 + 4자리 PIN 입력 → 그룹의 시드머니로 초기 잔액 생성
3. **거래 기록**: 멤버 선택 → 유형 선택(제로섬 그룹은 WIN/LOSE, 개방형 그룹은 GRANT/SPEND, 공통으로 ADJUST) → 금액 입력
4. 멤버 잔액표와 최근 거래 내역이 실시간으로 갱신됩니다

**검증된 동작**:
- 제로섬(CLOSED) 그룹: 한 멤버가 따고 다른 멤버가 잃어도 전체 잔액 합계는 항상 유지됨
- 음수 잔액 비허용 그룹: 잔액이 부족한 출금 시도는 거부되고 에러 메시지 표시
- 관리자는 본인이 배정된 그룹의 데이터만 조회/수정 가능

## 4단계: 멤버 로그인 및 잔액 조회, 익명/실명 막대그래프

- 메인 화면의 **"멤버"** 카드를 누르면 `/member/login`으로 이동
- **1단계**: 활성 그룹 목록이 리스트로 표시됨 → 원하는 그룹 클릭
- **2단계**: 선택한 그룹에서 **이름 + PIN**만 입력 (그룹코드를 외우거나 입력할 필요 없음)
- 로그인하면 본인 잔액, 본인 거래내역, **우리 그룹 전체 잔액 분포(익명 막대그래프)**를 볼 수 있음
- 익명 그래프는 이름 대신 "멤버1, 멤버2..." 로 표시되고 순서도 매번 섞임 (누가 누군지 알 수 없음)
- 관리자 대시보드에는 같은 그래프가 **실명**으로 표시됨 (관리자는 이미 이름을 알고 있으므로)

## 추가 기능: 관리자의 멤버 PIN 재설정

관리자 대시보드의 멤버 잔액 표 오른쪽에 "PIN 재설정" 칸이 추가되었습니다.
새 4자리 PIN을 입력하고 "변경"을 누르면 즉시 반영되며, 이전 PIN으로는 더 이상 로그인할 수 없습니다.
멤버가 PIN을 잊어버렸을 때 사용하시면 됩니다.

## 추가 기능: 삭제 및 비밀번호 변경

**수퍼유저 대시보드**
- 그룹 목록에서 "삭제" 버튼 → 해당 그룹과 소속 멤버·거래내역이 모두 함께 삭제됨 (확인창 표시)
- 관리자 목록에서 "삭제" 버튼 → 관리자 계정 및 그룹 배정 정보 삭제
- 관리자 목록에서 새 비밀번호 입력 후 "변경" → 즉시 반영

**그룹 관리자 대시보드**
- 멤버 잔액 표에서 "삭제" 버튼 → 해당 멤버와 거래내역 삭제 (확인창 표시)
- PIN 재설정은 기존과 동일

> ⚠️ 제로섬(CLOSED) 그룹에서 멤버를 삭제하면 그 멤버가 가지고 있던 잔액만큼
> 그룹 전체 합계가 줄어듭니다 (판돈이 그룹 밖으로 사라지는 셈). 신중히 사용하세요.

## 5단계: 비활성 그룹 자동 아카이브 스케줄러

- 매일 자정(UTC) 자동으로 백그라운드 점검이 실행됩니다 (`app/scheduler.py`)
- **180일**(약 6개월)간 활동(멤버 추가/거래 기록)이 없는 그룹 → 자동으로 **아카이브(ARCHIVED)** 상태로 전환
- 아카이브된 지 **30일**이 더 지나면 → 완전 삭제 (멤버, 거래내역 포함)
- 수퍼유저 대시보드에 "아카이브된 그룹" 섹션이 추가되어 유예기간 내에 **복구**하거나 **즉시 삭제**할 수 있음
- "지금 점검 실행" 버튼으로 자정까지 기다리지 않고 바로 점검을 실행해볼 수도 있음

기간은 `.env`에서 조절 가능합니다 (테스트 시 짧게 설정 가능):
```
ARCHIVE_AFTER_DAYS=180
DELETE_AFTER_ARCHIVE_DAYS=30
```

## 추가 기능: 한 관리자가 여러 그룹 관리

- 관리자 목록의 "담당 그룹" 칸에 배정된 그룹들이 태그로 표시됨 (× 클릭 시 배정 해제)
- "그룹 추가 배정" 칸에서 다른 그룹을 선택해 "추가"를 누르면 그 관리자가 추가로 담당하게 됨
- 관리자가 로그인하면 담당하는 모든 그룹이 대시보드 상단에 탭으로 표시되고, 탭을 눌러 그룹을 전환하며 관리 가능

## 추가 개선: 그래프 위치 및 색상

- 관리자/멤버 대시보드 모두 막대그래프를 화면 맨 아래로 이동
- 기본적으로 숨겨져 있고 **"그래프 보기"** 버튼을 눌러야 표시됨 (다시 누르면 숨김)
- 잔액이 **음수인 멤버의 막대는 빨간색**, 양수는 초록색으로 구분 표시

## 추가 기능: 그룹별 스킨 색상

- 그룹 생성 폼에 색상 선택기가 추가됨 → 선택한 색이 그 그룹의 "포인트 색상"이 됨
- 관리자 대시보드, 멤버 대시보드, 멤버 로그인 화면 등 해당 그룹과 관련된 모든 화면에 이 색이 강조색으로 적용됨
- 여러 그룹을 담당하는 관리자의 탭 목록, 멤버 로그인 시 그룹 목록에도 색상 점으로 구분 표시

> ⚠️ **DB 스키마 변경 주의**: `groups` 테이블에 `theme_color` 컬럼이 새로 추가되었습니다.
> 기존 `deokphil.db` 파일이 있다면 `no such column: groups.theme_color` 에러가 날 수 있습니다.
> 테스트 데이터라면 서버를 끄고 `deokphil.db` 파일을 삭제한 뒤 재시작하세요.

## 추가: Alembic 마이그레이션 도입

지금까지는 모델(`app/models.py`)이 바뀔 때마다 `deokphil.db`를 삭제하고 다시 만들어야 했는데,
이제는 **Alembic**으로 스키마 변경 이력을 관리합니다. 더 이상 DB를 통째로 지울 필요가 없습니다.

### 최초 1회 설정 (또는 새 환경에서 처음 받았을 때)

```powershell
pip install -r requirements.txt
alembic upgrade head
```

`alembic upgrade head`가 `deokphil.db`를 만들고 필요한 테이블을 전부 생성합니다.
(기존에 `deokphil.db`가 있었다면 삭제 후 실행하세요. 딱 한 번만 하면 됩니다.)

이후 서버 실행은 기존과 동일합니다.

```powershell
uvicorn app.main:app --reload --reload-dir app
```

### 앞으로 모델(`app/models.py`)을 수정했을 때

제가 모델을 변경한 새 코드를 드리면, 아래 순서로 반영하시면 됩니다.

```powershell
alembic revision --autogenerate -m "설명 (예: add theme color)"
alembic upgrade head
```

- 1번째 명령이 `migrations/versions/` 안에 변경사항을 담은 새 마이그레이션 파일을 만들고
- 2번째 명령이 실제 DB에 그 변경사항을 적용합니다

기존 데이터(그룹, 멤버, 거래내역 등)는 그대로 유지된 채 스키마만 안전하게 바뀝니다.

### 참고

- `alembic current` : 지금 DB가 어느 버전인지 확인
- `alembic history` : 지금까지의 마이그레이션 이력 확인
- Render 배포 시에도 서버 시작 전에 `alembic upgrade head`를 한 번 실행해주면 됩니다 (Postgres에도 동일하게 동작)

## 6단계: Neon Postgres 연동 + Render 배포

### 1) Neon에서 무료 Postgres 만들기

1. https://neon.tech 접속 후 가입 (GitHub 계정으로 로그인 가능)
2. "Create a project" → 이름 아무거나 (예: `deokphil-db`)
3. 생성되면 대시보드에 **Connection string**이 보임. 이런 형식입니다.
   ```
   postgresql://neondb_owner:xxxxxx@ep-xxxx.aws.neon.tech/neondb?sslmode=require
   ```
4. 이 문자열을 복사해두세요

> Supabase를 선호하신다면 https://supabase.com 에서 프로젝트 생성 후 Settings → Database에서
> 같은 방식으로 연결 문자열을 받을 수 있습니다. 이후 과정은 동일합니다.

### 2) 로컬에서 먼저 Postgres로 테스트 (배포 전 검증)

`.env` 파일의 `DATABASE_URL`을 방금 받은 연결 문자열로 잠깐 바꿔서 테스트해보는 걸 권장합니다.

```
DATABASE_URL=postgresql://neondb_owner:xxxxxx@ep-xxxx.aws.neon.tech/neondb?sslmode=require
```

```powershell
alembic upgrade head
uvicorn app.main:app --reload --reload-dir app
```

브라우저에서 평소처럼 로그인/그룹생성이 잘 되면 성공입니다. 확인 후 로컬 개발은 다시
SQLite로 되돌려도 되고, 계속 Neon으로 개발해도 됩니다 (계정당 무료 한도 내에서 자유).

### 3) GitHub에 코드 올리기

Render는 GitHub 저장소와 연결해서 배포합니다. 아직 저장소가 없다면:

```powershell
git init
git add .
git commit -m "initial commit"
```

GitHub에서 새 저장소(예: `deokphil-account`)를 만들고 안내에 따라 push 하세요.

> `.env` 파일은 `.gitignore`에 이미 포함되어 있어 실수로 올라가지 않습니다. 비밀번호/키가
> 코드에 직접 적혀있지 않은지 한번 확인해주세요.

### 4) Render 웹서비스 생성

1. https://render.com 가입 (GitHub 계정으로 가능)
2. Dashboard → **New +** → **Web Service**
3. 방금 만든 GitHub 저장소 선택
4. 아래와 같이 설정:

| 항목 | 값 |
|---|---|
| Name | `deokphil` (가능하면 이 이름으로 → `deokphil.onrender.com`) |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |

5. **Environment Variables** 섹션에서 아래 값들을 추가:

| Key | Value |
|---|---|
| `DATABASE_URL` | Neon에서 받은 연결 문자열 |
| `SECRET_KEY` | 무작위 긴 문자열 (예: `python -c "import secrets; print(secrets.token_hex(32))"` 로 생성) |
| `SUPERUSER_USERNAME` | 원하는 관리자 아이디 |
| `SUPERUSER_PASSWORD` | 강력한 비밀번호로 변경 (changeme123 금지) |
| `APP_NAME` | `덕필 계좌 관리 시스템` |
| `ARCHIVE_AFTER_DAYS` | `180` |
| `DELETE_AFTER_ARCHIVE_DAYS` | `30` |

6. **Create Web Service** 클릭 → 빌드/배포 로그가 자동으로 흐름
7. 완료되면 `https://deokphil.onrender.com` (또는 배정된 주소)으로 접속 확인

### 5) 배포 후 확인 사항

- 첫 접속 시 무료 플랜은 슬립 상태에서 깨어나느라 몇십 초 걸릴 수 있습니다 (다음 요청부터는 빠름)
- 수퍼유저 계정으로 로그인해서 그룹 생성 → 관리자 생성 → 로그아웃 → 관리자 로그인까지 확인
- 이후 모델을 변경한 새 코드를 받으면: 로컬에서 `alembic revision --autogenerate` 후
  GitHub에 push만 하면, Render가 재배포하면서 Start Command의 `alembic upgrade head`가
  자동으로 실행되어 운영 DB도 함께 최신 스키마로 반영됩니다

## 추가 기능: 같은 그룹 내 멤버 이름 중복 방지

- 그룹 관리자가 이미 존재하는 이름으로 멤버를 또 만들려고 하면 "이미 같은 이름의 멤버가 있습니다" 에러가 뜨고 생성이 차단됩니다
- DB 레벨에서도 제약조건(`group_id` + `name` 조합 고유)이 걸려있어 이중으로 안전합니다
- 단, **다른 그룹**끼리는 같은 이름을 써도 됩니다 (멤버 로그인 시 그룹을 먼저 선택하므로 문제없음)

> 이번 변경은 새 마이그레이션 파일(`migrations/versions/`)이 함께 들어있으니
> 압축을 통째로 적용하셨다면 아래 한 줄만 실행하면 됩니다.
> ```powershell
> alembic upgrade head
> ```
> (이미 중복된 이름의 멤버가 있는 그룹이 있다면 마이그레이션이 실패할 수 있습니다.
> 그런 경우 먼저 관리자 대시보드에서 중복된 멤버 중 하나를 삭제한 뒤 다시 시도하세요.)

## 진행 상황 정리

1. ✅ 윈도우 + VS Code 로컬 개발 환경
2. ✅ 수퍼유저 로그인, 그룹/관리자 생성·삭제·비밀번호 변경
3. ✅ 그룹 관리자 대시보드 (멤버 추가/삭제, 거래 관리, PIN 재설정)
4. ✅ 멤버 로그인 및 잔액 조회, 익명/실명 막대그래프
5. ✅ 비활성 그룹 자동 아카이브 스케줄러
6. ✅ Alembic 마이그레이션
7. ✅ Neon/Supabase Postgres 연동 및 Render 배포 안내 (실제 배포는 사용자가 진행)
