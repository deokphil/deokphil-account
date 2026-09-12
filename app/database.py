"""
데이터베이스 연결 설정.

로컬 개발: DATABASE_URL 환경변수가 없으면 SQLite 파일(deokphil.db)을 사용.
Render 배포: DATABASE_URL 환경변수에 Neon/Supabase의 Postgres 연결 문자열을 넣으면
             코드 수정 없이 자동으로 그쪽으로 연결됨.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()  # .env 파일을 읽어서 환경변수로 등록

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./deokphil.db")

# 일부 서비스(Heroku 등)는 postgres:// 형식을 주는데, SQLAlchemy 2.0은 postgresql://만 인식함
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite는 멀티스레드 접속을 위해 connect_args가 필요하지만
# Postgres는 필요 없으므로 분기 처리
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """요청마다 DB 세션을 열고 끝나면 닫아주는 FastAPI 의존성 함수"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
