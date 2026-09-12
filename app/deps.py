"""
쿠키(access_token)에 담긴 JWT를 읽어 현재 로그인한 User를 반환.
로그인 안 되어 있으면 None을 반환 (라우트에서 직접 리다이렉트 처리).
"""
from fastapi import Request, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import decode_access_token
from app import models


def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    return db.query(models.User).filter(models.User.id == int(user_id)).first()


def get_current_member(request: Request, db: Session = Depends(get_db)):
    """멤버용 쿠키(member_token)에서 현재 로그인한 Member를 반환"""
    token = request.cookies.get("member_token")
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload or payload.get("type") != "member":
        return None

    member_id = payload.get("sub")
    if not member_id:
        return None

    return db.query(models.Member).filter(models.Member.id == int(member_id)).first()
