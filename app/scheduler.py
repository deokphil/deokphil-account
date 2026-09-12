"""
비활성 그룹 자동 관리 스케줄러.

- ACTIVE 그룹 중 last_active_at이 ARCHIVE_AFTER_DAYS 이상 지난 그룹 -> ARCHIVED로 전환
- ARCHIVED 그룹 중 archived_at이 DELETE_AFTER_ARCHIVE_DAYS 이상 지난 그룹 -> 완전 삭제

기본값은 6개월(180일) 후 아카이브, 아카이브 후 30일 유예 뒤 삭제.
테스트를 위해 환경변수로 기간을 조절할 수 있습니다.
"""
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app import models

ARCHIVE_AFTER_DAYS = int(os.getenv("ARCHIVE_AFTER_DAYS", "180"))
DELETE_AFTER_ARCHIVE_DAYS = int(os.getenv("DELETE_AFTER_ARCHIVE_DAYS", "30"))


def run_inactive_group_check():
    """비활성 그룹을 아카이브하고, 유예기간이 지난 아카이브 그룹을 삭제"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # 1) ACTIVE -> ARCHIVED
        archive_cutoff = now - timedelta(days=ARCHIVE_AFTER_DAYS)
        to_archive = (
            db.query(models.Group)
            .filter(
                models.Group.status == models.GroupStatus.ACTIVE,
                models.Group.last_active_at < archive_cutoff,
            )
            .all()
        )
        for group in to_archive:
            group.status = models.GroupStatus.ARCHIVED
            group.archived_at = now
            print(f"[스케줄러] 그룹 '{group.name}' 비활성으로 아카이브됨")

        # 2) ARCHIVED -> 완전 삭제 (유예기간 경과)
        delete_cutoff = now - timedelta(days=DELETE_AFTER_ARCHIVE_DAYS)
        to_delete = (
            db.query(models.Group)
            .filter(
                models.Group.status == models.GroupStatus.ARCHIVED,
                models.Group.archived_at < delete_cutoff,
            )
            .all()
        )
        for group in to_delete:
            member_ids = [
                m.id for m in db.query(models.Member.id).filter(models.Member.group_id == group.id)
            ]
            if member_ids:
                db.query(models.Transaction).filter(
                    models.Transaction.member_id.in_(member_ids)
                ).delete(synchronize_session=False)
                db.query(models.Member).filter(models.Member.group_id == group.id).delete(
                    synchronize_session=False
                )
            db.query(models.GroupAdminAssignment).filter(
                models.GroupAdminAssignment.group_id == group.id
            ).delete(synchronize_session=False)
            print(f"[스케줄러] 그룹 '{group.name}' 유예기간 만료로 완전 삭제됨")
            db.delete(group)

        db.commit()
    finally:
        db.close()


def start_scheduler():
    """앱 시작 시 스케줄러를 등록하고 시작. 매일 1회(자정) 실행."""
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(run_inactive_group_check, "cron", hour=0, minute=0, id="inactive_group_check")
    scheduler.start()
    return scheduler
