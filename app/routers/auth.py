from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import verify_password, create_access_token
from app import models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
def login_form(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": error}
    )


@router.post("/login")
def login_submit(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == username).first()

    if not user or not verify_password(password, user.password_hash):
        return RedirectResponse(
            url="/login?error=아이디 또는 비밀번호가 올바르지 않습니다", status_code=303
        )

    token = create_access_token({"sub": str(user.id), "role": user.role.value})

    # 역할에 따라 이동할 대시보드 결정
    destination = "/superuser" if user.role == models.UserRole.SUPERUSER else "/admin"

    response = RedirectResponse(url=destination, status_code=303)
    response.set_cookie(
        key="access_token", value=token, httponly=True, samesite="lax", max_age=60 * 60 * 12
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response
