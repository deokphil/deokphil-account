from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.security import hash_password
from app.scheduler import run_inactive_group_check
from app import models

router = APIRouter(prefix="/superuser")
templates = Jinja2Templates(directory="app/templates")


def require_superuser(user):
    """수퍼유저가 아니면 None 반환 -> 라우트에서 로그인 페이지로 리다이렉트"""
    if user is None or user.role != models.UserRole.SUPERUSER:
        return False
    return True


@router.get("")
def dashboard(
    request: Request,
    info: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_superuser(user):
        return RedirectResponse(url="/login", status_code=303)

    groups = (
        db.query(models.Group)
        .filter(models.Group.status == models.GroupStatus.ACTIVE)
        .order_by(models.Group.created_at.desc())
        .all()
    )
    archived_groups = (
        db.query(models.Group)
        .filter(models.Group.status == models.GroupStatus.ARCHIVED)
        .order_by(models.Group.archived_at.desc())
        .all()
    )
    admins = db.query(models.User).filter(models.User.role == models.UserRole.ADMIN).all()

    # 관리자별 담당 그룹 목록(id, name) 준비
    admin_assigned_groups = {}
    for a in admins:
        rows = (
            db.query(models.Group.id, models.Group.name)
            .join(models.GroupAdminAssignment, models.GroupAdminAssignment.group_id == models.Group.id)
            .filter(models.GroupAdminAssignment.user_id == a.id)
            .all()
        )
        admin_assigned_groups[a.id] = rows

    return templates.TemplateResponse(
        "superuser_dashboard.html",
        {
            "request": request,
            "user": user,
            "groups": groups,
            "archived_groups": archived_groups,
            "admins": admins,
            "admin_assigned_groups": admin_assigned_groups,
            "info": info,
        },
    )


@router.post("/groups")
def create_group(
    name: str = Form(...),
    economy_type: str = Form(...),
    seed_money: float = Form(0),
    allow_negative_balance: bool = Form(False),
    currency_label: str = Form("원"),
    theme_color: str = Form("#2f6f4f"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_superuser(user):
        return RedirectResponse(url="/login", status_code=303)

    group = models.Group(
        name=name,
        economy_type=models.EconomyType(economy_type),
        seed_money=seed_money,
        allow_negative_balance=allow_negative_balance,
        currency_label=currency_label,
        theme_color=theme_color,
    )
    db.add(group)
    db.commit()

    return RedirectResponse(url="/superuser", status_code=303)


@router.post("/admins")
def create_admin(
    username: str = Form(...),
    password: str = Form(...),
    group_id: int = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_superuser(user):
        return RedirectResponse(url="/login", status_code=303)

    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        return RedirectResponse(url="/superuser?error=이미+존재하는+아이디입니다", status_code=303)

    admin_user = models.User(
        username=username,
        password_hash=hash_password(password),
        role=models.UserRole.ADMIN,
    )
    db.add(admin_user)
    db.flush()  # admin_user.id 확보

    assignment = models.GroupAdminAssignment(user_id=admin_user.id, group_id=group_id)
    db.add(assignment)
    db.commit()

    return RedirectResponse(url="/superuser", status_code=303)


@router.post("/groups/{group_id}/delete")
def delete_group(
    group_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_superuser(user):
        return RedirectResponse(url="/login", status_code=303)

    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return RedirectResponse(url="/superuser", status_code=303)

    member_ids = [
        m.id for m in db.query(models.Member.id).filter(models.Member.group_id == group_id)
    ]

    # 연관 데이터(거래내역 -> 멤버 -> 관리자배정) 순서로 먼저 삭제 후 그룹 삭제
    if member_ids:
        db.query(models.Transaction).filter(
            models.Transaction.member_id.in_(member_ids)
        ).delete(synchronize_session=False)
        db.query(models.Member).filter(models.Member.group_id == group_id).delete(
            synchronize_session=False
        )
    db.query(models.GroupAdminAssignment).filter(
        models.GroupAdminAssignment.group_id == group_id
    ).delete(synchronize_session=False)

    db.delete(group)
    db.commit()

    return RedirectResponse(url="/superuser?info=그룹이+삭제되었습니다", status_code=303)


@router.post("/admins/{admin_id}/delete")
def delete_admin(
    admin_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_superuser(user):
        return RedirectResponse(url="/login", status_code=303)

    admin_user = (
        db.query(models.User)
        .filter(models.User.id == admin_id, models.User.role == models.UserRole.ADMIN)
        .first()
    )
    if not admin_user:
        return RedirectResponse(url="/superuser", status_code=303)

    db.query(models.GroupAdminAssignment).filter(
        models.GroupAdminAssignment.user_id == admin_id
    ).delete(synchronize_session=False)
    db.delete(admin_user)
    db.commit()

    return RedirectResponse(url="/superuser?info=관리자+계정이+삭제되었습니다", status_code=303)


@router.post("/admins/{admin_id}/password")
def change_admin_password(
    admin_id: int,
    new_password: str = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_superuser(user):
        return RedirectResponse(url="/login", status_code=303)

    admin_user = (
        db.query(models.User)
        .filter(models.User.id == admin_id, models.User.role == models.UserRole.ADMIN)
        .first()
    )
    if not admin_user:
        return RedirectResponse(url="/superuser", status_code=303)

    admin_user.password_hash = hash_password(new_password)
    db.commit()

    return RedirectResponse(url="/superuser?info=관리자+비밀번호가+변경되었습니다", status_code=303)


@router.post("/groups/{group_id}/reactivate")
def reactivate_group(
    group_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_superuser(user):
        return RedirectResponse(url="/login", status_code=303)

    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return RedirectResponse(url="/superuser", status_code=303)

    from datetime import datetime

    group.status = models.GroupStatus.ACTIVE
    group.archived_at = None
    group.last_active_at = datetime.utcnow()
    db.commit()

    return RedirectResponse(url="/superuser?info=그룹이+복구되었습니다", status_code=303)


@router.post("/run-inactive-check")
def manual_inactive_check(user=Depends(get_current_user)):
    if not require_superuser(user):
        return RedirectResponse(url="/login", status_code=303)

    run_inactive_group_check()

    return RedirectResponse(url="/superuser?info=비활성+그룹+점검을+실행했습니다", status_code=303)


@router.post("/admins/{admin_id}/assign-group")
def assign_group_to_admin(
    admin_id: int,
    group_id: int = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_superuser(user):
        return RedirectResponse(url="/login", status_code=303)

    admin_user = (
        db.query(models.User)
        .filter(models.User.id == admin_id, models.User.role == models.UserRole.ADMIN)
        .first()
    )
    if not admin_user:
        return RedirectResponse(url="/superuser", status_code=303)

    existing = (
        db.query(models.GroupAdminAssignment)
        .filter(
            models.GroupAdminAssignment.user_id == admin_id,
            models.GroupAdminAssignment.group_id == group_id,
        )
        .first()
    )
    if not existing:
        db.add(models.GroupAdminAssignment(user_id=admin_id, group_id=group_id))
        db.commit()

    return RedirectResponse(url="/superuser?info=그룹이+추가+배정되었습니다", status_code=303)


@router.post("/admins/{admin_id}/unassign-group")
def unassign_group_from_admin(
    admin_id: int,
    group_id: int = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not require_superuser(user):
        return RedirectResponse(url="/login", status_code=303)

    db.query(models.GroupAdminAssignment).filter(
        models.GroupAdminAssignment.user_id == admin_id,
        models.GroupAdminAssignment.group_id == group_id,
    ).delete(synchronize_session=False)
    db.commit()

    return RedirectResponse(url="/superuser?info=그룹+배정이+해제되었습니다", status_code=303)
