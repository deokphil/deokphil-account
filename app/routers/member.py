import json
import random

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_member
from app.security import verify_password, create_access_token
from app import models

router = APIRouter(prefix="/member")
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
def member_login_group_list(request: Request, db: Session = Depends(get_db)):
    """1단계: 활성 그룹 목록을 보여주고 선택하게 함"""
    groups = (
        db.query(models.Group)
        .filter(models.Group.status == models.GroupStatus.ACTIVE)
        .order_by(models.Group.name)
        .all()
    )
    return templates.TemplateResponse(
        "member_login_groups.html", {"request": request, "groups": groups}
    )


@router.get("/login/{group_id}")
def member_login_form(
    request: Request,
    group_id: int,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """2단계: 선택한 그룹에서 이름 + PIN 입력"""
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return RedirectResponse(url="/member/login", status_code=303)

    return templates.TemplateResponse(
        "member_login_form.html", {"request": request, "group": group, "error": error}
    )


@router.post("/login")
def member_login_submit(
    group_id: int = Form(...),
    name: str = Form(...),
    pin: str = Form(...),
    db: Session = Depends(get_db),
):
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return RedirectResponse(url="/member/login", status_code=303)

    member = (
        db.query(models.Member)
        .filter(models.Member.group_id == group.id, models.Member.name == name.strip())
        .first()
    )
    if not member or not verify_password(pin, member.pin_hash):
        return RedirectResponse(
            url=f"/member/login/{group_id}?error=이름+또는+PIN이+올바르지+않습니다",
            status_code=303,
        )

    token = create_access_token({"sub": str(member.id), "type": "member"})

    response = RedirectResponse(url="/member", status_code=303)
    response.set_cookie(
        key="member_token", value=token, httponly=True, samesite="lax", max_age=60 * 60 * 12
    )
    return response


@router.get("")
def member_dashboard(
    request: Request,
    member=Depends(get_current_member),
    db: Session = Depends(get_db),
):
    if member is None:
        return RedirectResponse(url="/member/login", status_code=303)

    group = db.query(models.Group).filter(models.Group.id == member.group_id).first()

    my_transactions = (
        db.query(models.Transaction)
        .filter(models.Transaction.member_id == member.id)
        .order_by(models.Transaction.created_at.desc())
        .limit(20)
        .all()
    )

    # 그룹 내 전체 멤버 잔액 - 이름은 숨기고 순서도 섞어서 익명화
    all_balances = [
        m.balance for m in db.query(models.Member).filter(models.Member.group_id == group.id)
    ]
    random.shuffle(all_balances)
    anon_labels = [f"멤버{i+1}" for i in range(len(all_balances))]

    return templates.TemplateResponse(
        "member_dashboard.html",
        {
            "request": request,
            "member": member,
            "group": group,
            "my_transactions": my_transactions,
            "chart_labels_json": json.dumps(anon_labels),
            "chart_values_json": json.dumps(all_balances),
        },
    )


@router.get("/logout")
def member_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("member_token")
    return response
