# app/models/m_rls_invoice.py
import uuid
from sqlmodel import Relationship, SQLModel, Field, UniqueConstraint, String
from sqlalchemy import Boolean
from sqlalchemy import Column, String, Computed
from sqlalchemy.dialects.postgresql import JSONB

from typing import ClassVar, Optional, Dict, Any, List, Literal
from datetime import datetime

from app.models.m_mixin import BaseMixin
from app.models.rls.m_payment_allocation_rls import PaymentAllocationRead

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.rls.m_payment_allocation_rls import PaymentAllocationDB


class InvoiceBase(SQLModel):
    inv_rec: str = Field(default="invoice")

    extras: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSONB))

    issue_date: datetime  # 发票日期
    due_date: datetime  # 到期日期

    invoice_prefix: str = Field(default="INV-", index=True)
    invoice_sequence: int = Field(nullable=False)

    customer_id: uuid.UUID = Field(default_factory=uuid.uuid4, index=True)
    customer_snapshot: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSONB))

    line_items: List[Dict[str, Any]] = Field(
        default=[], sa_column=Column(JSONB))  # 行项目
    subtotal: float = Field(default  =  0)  # 小计

    other_items: List[Dict[str, Any]] = Field(
        default=[], sa_column=Column(JSONB))  # 行项目
    total1: float = Field(default  =  0)  # 小计
    total2: float = Field(default  =  0)  # 小计
    total3: float = Field(default  =  0)  # 小计
    total4: float = Field(default  =  0)  # 小计
    total5: float = Field(default  =  0)
    total6: float = Field(default  =  0)
    total7: float = Field(default  =  0)
    total8: float = Field(default  =  0)    
    total9: float = Field(default  =  0)
    
    

    discount_rate: float = Field(ge=0, le=100, default=0)  # 折扣率（百分比）
    discount_flat_amount: float = Field(default  =  0)  # 折扣金额
    discount_type: Optional[str] = Field(default=None)  # 折扣类型：percentage, flat
    discounted_subtotal: float = Field(default  =  0)  # 折扣后小计

    tax_amount: float = Field(default  =  0)  # 税额
    total_amount: float = Field(default  =  0)  # 总金额
    amount_credited: float = Field(default  =  0)  # 已抵扣金额
    amount_paid: float = Field(default  =  0)  # 已付金额
    balance_due: float = Field(default  =  0)  # 欠款金额

    # draft, sent, paid, overdue, cancelled
    status: str = Field(default="draft")
    # pending, partial, paid, overdue
    payment_status: str = Field(default="pending")

    mark_as_sent: bool = Field(
        default=False, sa_column=Column(Boolean))  # 标记是否已发送
    auto_apply: bool = Field(
        default=False, sa_column=Column(Boolean))  # 自动应用付款
    sent_at: Optional[datetime] = Field(default=None)  # 发送时间

    # JSONB 灵活数据
    tax_breakdown: Dict[str, Any] = Field(
        default={}, sa_column=Column(JSONB))  # 税费明细
    payment_terms: Dict[str, Any] = Field(
        default={}, sa_column=Column(JSONB))  # 付款条款
    shipping_info: Dict[str, Any] = Field(
        default={}, sa_column=Column(JSONB))  # 配送信息
    notes: Dict[str, Any] = Field(
        default={}, sa_column=Column(JSONB))  # 备注和自定义字段


class InvoiceDB(InvoiceBase, BaseMixin, table=True):
    __tablename__: ClassVar[str] = "invoices_rls"
    __table_args__ = (UniqueConstraint("tenant_id", "invoice_sequence"),)

    invoice_number: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String,
            Computed("invoice_prefix || invoice_sequence::text", persisted=True)
        )
    )

    payment_allocations: list["PaymentAllocationDB"] = Relationship(
        back_populates="invoice")

    class Config:
        indexes = [
            ("tenant_id", "invoice_sequence"),  # 复合索引
            ("tenant_id", "status"),
            ("tenant_id", "issue_date"),
        ]


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceReadList(InvoiceBase):
    id: uuid.UUID  # 🔥 改为 UUID
    invoice_number: str  # will be auto-exposed
    created_at: datetime
    updated_at: datetime


class InvoiceUpdate(SQLModel):
    id: uuid.UUID
    # General extras
    extras: Optional[Dict[str, Any]] = None

    # Dates
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


    # Customer
    customer_id: Optional[uuid.UUID] = None
    customer_snapshot: Optional[Dict[str, Any]] = None

    # Line items
    line_items: Optional[List[Dict[str, Any]]] = None
    subtotal: Optional[float] = None


    other_items: Optional[List[Dict[str, Any]]] = None
    total1: Optional[float] = None
    total2: Optional[float] = None
    total3: Optional[float] = None
    total4: Optional[float] = None
    total5: Optional[float] = None
    total6: Optional[float] = None
    total7: Optional[float] = None
    total8: Optional[float] = None
    total9: Optional[float] = None

    # Discounts
    discount_rate: Optional[float] = None
    discount_flat_amount: Optional[float] = None
    discount_type: Optional[str] = None
    discounted_subtotal: Optional[float] = None

    # Tax and total
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    amount_credited: Optional[float] = None
    amount_paid: Optional[float] = None
    balance_due: Optional[float] = None

    # Status
    # draft, sent, paid, overdue, cancelled
    status: Optional[str] = None
    payment_status: Optional[str] = None    # pending, partial, paid, overdue

    # Flags / actions
    mark_as_sent: Optional[bool] = None
    auto_apply: Optional[bool] = None
    sent_at: Optional[datetime] = None

    # JSON fields
    tax_breakdown: Optional[Dict[str, Any]] = None
    payment_terms: Optional[Dict[str, Any]] = None
    shipping_info: Optional[Dict[str, Any]] = None
    notes: Optional[Dict[str, Any]] = None

    # Business metadata
    description: Optional[str] = None


class InvoiceDelete(SQLModel):
    is_deleted: bool = Field(default=True)


class InvoiceRead(InvoiceBase):
    id: uuid.UUID
    invoice_number: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    payment_allocations: list[PaymentAllocationRead] = []
