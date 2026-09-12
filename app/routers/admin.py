from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.security import hash_password
from app import models

import json

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def get_assigned_group_ids(user, db: Session) -> list[int]:
    """이 관리자가 담당하는 그룹 id 목록. 수퍼유저는 전체 그룹 담당으로 취급."""
    if user.role == models.UserRole.SUPERUSER:
        return [g.id for g in db.query(models.Group.id).all()]
    rows = (
        db.query(models.GroupAdminAssignment.group_id)
        .filter(models.GroupAdminAssignment.user_id == user.id)
        .all()
    )
    return [r[0] for r in rows]


def require_admin(user):
    if user is None or user.role not in (models.UserRole.ADMIN, models.UserRole.SUPERUSER):
        return False
    return True


@router.get("")
def dashboard(
    request: Request,
    group_id: int | None = None,
    error: str | None = None,
    info: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_admin(user):
        return RedirectResponse(url="/login", status_code=303)

    assigned_ids = get_assigned_group_ids(user, db)
    my_groups = (
        db.query(models.Group).filter(models.Group.id.in_(assigned_ids)).all()
        if assigned_ids
        else []
    )

    selected_group = None
    members = []
    recent_transactions = []

    if group_id and group_id in assigned_ids:
        selected_group = db.query(models.Group).filter(models.Group.id == group_id).first()
        members = (
            db.query(models.Member)
            .filter(models.Member.group_id == group_id)
            .order_by(models.Member.name)
            .all()
        )
        recent_transactions = (
            db.query(models.Transaction)
            .filter(models.Transaction.group_id == group_id)
            .order_by(models.Transaction.created_at.desc())
            .limit(20)
            .all()
        )

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "user": user,
            "my_groups": my_groups,
            "selected_group": selected_group,
            "members": members,
            "recent_transactions": recent_transactions,
            "error": error,
            "info": info,
            "chart_labels_json": json.dumps([m.name for m in members]),
            "chart_values_json": json.dumps([m.balance for m in members]),
        },
    )


@router.post("/members")
def create_member(
    group_id: int = Form(...),
    name: str = Form(...),
    pin: str = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_admin(user):
        return RedirectResponse(url="/login", status_code=303)

    assigned_ids = get_assigned_group_ids(user, db)
    if group_id not in assigned_ids:
        return RedirectResponse(url="/admin?error=담당+그룹이+아닙니다", status_code=303)

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    existing_member = (
        db.query(models.Member)
        .filter(models.Member.group_id == group_id, models.Member.name == name.strip())
        .first()
    )
    if existing_member:
        return RedirectResponse(
            url=f"/admin?group_id={group_id}&error=이미+같은+이름의+멤버가+있습니다",
            status_code=303,
        )

    member = models.Member(
        group_id=group_id,
        name=name,
        pin_hash=hash_password(pin),
        balance=group.seed_money,
    )
    db.add(member)

    # 초기 시드머니를 거래 내역에도 남김
    db.flush()
    db.add(
        models.Transaction(
            member_id=member.id,
            group_id=group_id,
            type=models.TransactionType.INITIAL,
            amount=group.seed_money,
            memo="최초 등록 시드머니",
            created_by=user.id,
        )
    )
    db.commit()

    from datetime import datetime
    group.last_active_at = datetime.utcnow()
    db.commit()

    return RedirectResponse(url=f"/admin?group_id={group_id}", status_code=303)


@router.post("/transactions")
def create_transaction(
    member_id: int = Form(...),
    type: str = Form(...),
    amount: float = Form(...),
    memo: str = Form(""),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_admin(user):
        return RedirectResponse(url="/login", status_code=303)

    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        return RedirectResponse(url="/admin?error=멤버를+찾을+수+없습니다", status_code=303)

    group = db.query(models.Group).filter(models.Group.id == member.group_id).first()

    assigned_ids = get_assigned_group_ids(user, db)
    if group.id not in assigned_ids:
        return RedirectResponse(url="/admin?error=담당+그룹이+아닙니다", status_code=303)

    tx_type = models.TransactionType(type)

    # 거래 유형에 따라 잔액에 더할 부호 있는 금액 계산
    signed_amount = amount
    if tx_type in (models.TransactionType.LOSE, models.TransactionType.SPEND):
        signed_amount = -abs(amount)
    elif tx_type in (models.TransactionType.WIN, models.TransactionType.GRANT):
        signed_amount = abs(amount)
    # ADJUST는 입력한 부호(양수/음수)를 그대로 사용

    new_balance = member.balance + signed_amount

    if not group.allow_negative_balance and new_balance < 0:
        return RedirectResponse(
            url=f"/admin?group_id={group.id}&error=잔액이+부족합니다+(음수+잔액+비허용+그룹)",
            status_code=303,
        )

    member.balance = new_balance

    db.add(
        models.Transaction(
            member_id=member.id,
            group_id=group.id,
            type=tx_type,
            amount=signed_amount,
            memo=memo,
            created_by=user.id,
        )
    )

    from datetime import datetime
    group.last_active_at = datetime.utcnow()

    db.commit()

    return RedirectResponse(url=f"/admin?group_id={group.id}", status_code=303)


@router.post("/members/{member_id}/pin")
def change_member_pin(
    member_id: int,
    new_pin: str = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_admin(user):
        return RedirectResponse(url="/login", status_code=303)

    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        return RedirectResponse(url="/admin?error=멤버를+찾을+수+없습니다", status_code=303)

    assigned_ids = get_assigned_group_ids(user, db)
    if member.group_id not in assigned_ids:
        return RedirectResponse(url="/admin?error=담당+그룹이+아닙니다", status_code=303)

    member.pin_hash = hash_password(new_pin)
    db.commit()

    return RedirectResponse(
        url=f"/admin?group_id={member.group_id}&info=PIN이+변경되었습니다", status_code=303
    )


@router.post("/members/{member_id}/delete")
def delete_member(
    member_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_admin(user):
        return RedirectResponse(url="/login", status_code=303)

    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        return RedirectResponse(url="/admin?error=멤버를+찾을+수+없습니다", status_code=303)

    group_id = member.group_id
    assigned_ids = get_assigned_group_ids(user, db)
    if group_id not in assigned_ids:
        return RedirectResponse(url="/admin?error=담당+그룹이+아닙니다", status_code=303)

    db.query(models.Transaction).filter(models.Transaction.member_id == member_id).delete(
        synchronize_session=False
    )
    db.delete(member)
    db.commit()

    return RedirectResponse(
        url=f"/admin?group_id={group_id}&info=멤버가+삭제되었습니다", status_code=303
    )
