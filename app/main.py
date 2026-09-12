import os

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import SessionLocal
from app import models
from app.security import hash_password
from app.routers import auth, superuser, admin, member
from app.scheduler import start_scheduler, run_inactive_group_check

APP_NAME = os.getenv("APP_NAME", "덕필 계좌 관리 시스템")

app = FastAPI(title=APP_NAME)

# 정적 파일(css 등) 서빙
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# HTML 템플릿 엔진
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router)
app.include_router(superuser.router)
app.include_router(admin.router)
app.include_router(member.router)


def seed_superuser():
    """.env에 지정된 최초 수퍼유저 계정이 없으면 자동 생성"""
    username = os.getenv("SUPERUSER_USERNAME")
    password = os.getenv("SUPERUSER_PASSWORD")
    if not username or not password:
        return

    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.username == username).first()
        if existing:
            return
        superuser = models.User(
            username=username,
            password_hash=hash_password(password),
            role=models.UserRole.SUPERUSER,
        )
        db.add(superuser)
        db.commit()
        print(f"[초기 설정] 수퍼유저 계정 생성됨: {username}")
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    """앱 시작 시 수퍼유저 시드 + 스케줄러 시작.
    테이블 생성/변경은 이제 Alembic 마이그레이션으로 관리합니다.
    (서버 실행 전에 `alembic upgrade head`를 먼저 실행해야 합니다)"""
    seed_superuser()
    app.state.scheduler = start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler:
        scheduler.shutdown(wait=False)


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "app_name": APP_NAME},
    )


@app.get("/health")
def health_check():
    """Render 등 배포 환경에서 서비스 생존 확인용"""
    return {"status": "ok", "app": APP_NAME}
