"""
덕필 계좌 관리 시스템 - 데이터 모델

역할: 수퍼유저 / 그룹관리자 / 멤버
그룹 경제 유형: CLOSED(제로섬, 카드게임형) / OPEN(개방형, 달란트 시장형)
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Enum as SAEnum, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base


def now_utc():
    return datetime.utcnow()


class UserRole(str, enum.Enum):
    SUPERUSER = "SUPERUSER"
    ADMIN = "ADMIN"


class EconomyType(str, enum.Enum):
    CLOSED = "CLOSED"   # 제로섬 (카드게임)
    OPEN = "OPEN"        # 개방형 (달란트 시장 등)


class GroupStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class TransactionType(str, enum.Enum):
    WIN = "WIN"           # 제로섬: 땀
    LOSE = "LOSE"         # 제로섬: 잃음
    GRANT = "GRANT"       # 개방형: 지급/보상
    SPEND = "SPEND"       # 개방형: 구매/차감
    TRANSFER = "TRANSFER"  # 멤버 간 이동 (공통)
    ADJUST = "ADJUST"     # 관리자 정정 (공통)
    INITIAL = "INITIAL"   # 초기 시드머니 (공통)


class User(Base):
    """수퍼유저 / 그룹 관리자 계정"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.ADMIN)
    created_at = Column(DateTime, default=now_utc)

    assignments = relationship("GroupAdminAssignment", back_populates="user")


class Group(Base):
    """카드게임 그룹 또는 학급 등, 관리 단위"""
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    group_code = Column(String(20), unique=True, nullable=False,
                         default=lambda: uuid.uuid4().hex[:8].upper())

    economy_type = Column(SAEnum(EconomyType), nullable=False, default=EconomyType.CLOSED)
    seed_money = Column(Float, nullable=False, default=0)
    allow_negative_balance = Column(Boolean, nullable=False, default=True)
    currency_label = Column(String(20), nullable=False, default="원")
    theme_color = Column(String(7), nullable=False, default="#2f6f4f")  # 그룹별 스킨 색상 (hex)

    status = Column(SAEnum(GroupStatus), nullable=False, default=GroupStatus.ACTIVE)
    created_at = Column(DateTime, default=now_utc)
    last_active_at = Column(DateTime, default=now_utc)
    archived_at = Column(DateTime, nullable=True)  # ARCHIVED로 전환된 시각

    admin_assignments = relationship("GroupAdminAssignment", back_populates="group")
    members = relationship("Member", back_populates="group")


class GroupAdminAssignment(Base):
    """관리자 <-> 그룹 매핑 (관리자가 여러 그룹을 담당할 수 있음)"""
    __tablename__ = "group_admin_assignments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)

    user = relationship("User", back_populates="assignments")
    group = relationship("Group", back_populates="admin_assignments")


class Member(Base):
    """그룹에 속한 개별 멤버 (게임 참가자 / 학생)"""
    __tablename__ = "members"
    __table_args__ = (
        UniqueConstraint("group_id", "name", name="uq_member_group_name"),
    )

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    name = Column(String(50), nullable=False)
    pin_hash = Column(String(255), nullable=False)  # 4자리 PIN 해시
    balance = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, default=now_utc)

    group = relationship("Group", back_populates="members")
    transactions = relationship("Transaction", back_populates="member")


class Transaction(Base):
    """입출금/정정 거래 내역 (삭제하지 않고 항상 추가만 함)"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)

    type = Column(SAEnum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)  # 양수/음수 모두 가능
    memo = Column(String(200), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now_utc)

    member = relationship("Member", back_populates="transactions")


class AuditLog(Base):
    """수퍼유저/관리자의 주요 행위 감사 로그"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc)
