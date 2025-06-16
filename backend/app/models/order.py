from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from app.db.base import Base


class OrderStatus(enum.Enum):
    INQUIRY = "inquiry"
    NEGOTIATING = "negotiating"
    ORDERED = "ordered"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False)
    
    # Order details
    order_number = Column(String)
    product_name = Column(String, nullable=False)
    product_url = Column(String)
    quantity = Column(String)
    
    # Pricing
    unit_price = Column(Numeric(10, 2))
    total_price = Column(Numeric(10, 2))
    currency = Column(String, default="USD")
    
    # Shipping
    shipping_address = Column(Text)
    shipping_method = Column(String)
    tracking_number = Column(String)
    estimated_delivery = Column(DateTime(timezone=True))
    
    # Status
    status = Column(Enum(OrderStatus), default=OrderStatus.INQUIRY)
    
    # Additional details
    notes = Column(Text)
    supplier_details = Column(JSON, default={})  # company info, contact, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    chat = relationship("Chat", back_populates="orders")