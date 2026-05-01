# Base class for all SQLAlchemy models
from app.core.database import Base
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, Enum
from sqlalchemy.dialects.postgresql import UUID  
import uuid 
import enum
from sqlalchemy.orm import relationship


class UserRole(str, enum.Enum):
    """
    User roles in the system.

    Role Hierarchy:
    - ADMIN: System administrator (full access to everything)
    - STAFF: System staff (limited access)
    - CUSTOMER: Regular user (can login, place orders)
    - GUEST_CUSTOMER: Guest user (cannot login but can place orders)

    Note:
        A user can only have ONE role in the system. 
    """
    ADMIN = "admin"
    STAFF = "staff" 
    CUSTOMER = "customer" 
    GUEST_CUSTOMER = "guest_customer"

class UserStatus(str, enum.Enum):
    """
    User account status for lifecycle management.

    Status Lifecycle:
    1. PENDING_VERIFICATION: User just registered, email not verified yet
    2. ACTIVE: Email verified, account fully functional
    3. INACTIVE: User or admin deactivated account (can be reactivated)
    4. SUSPENDED: Admin suspended account (requires support intervention)

    Business Logic:
    - PENDING_VERIFICATION: Can login, but some features may be restricted
    - ACTIVE: Full access to all features
    - INACTIVE: Cannot login (graceful account closure)
    - SUSPENDED: Cannot login (enforcement action, requires admin to lift)

    """
    ACTIVE = "active"  # Fully active account
    INACTIVE = "inactive"  # User-initiated deactivation
    SUSPENDED = "suspended"  # Admin-initiated suspension
    PENDING_VERIFICATION = "pending_verification"  # Awaiting email verification
    

class User(Base):
    """User Model
    
    Purpose:
        Represents users who can register, authenticate, and interact with the platform.
        Users can be customers or administrators.
    """
    
    __tablename__ = "users"  # Table name in PostgreSQL

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Hashed password for authentication
    password = Column(String(255), nullable=False)
    
    # Identity
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    user_name = Column(String(200), nullable=True)
    email = Column(String(255), unique=True, nullable=False,index=True)
    phone = Column(String(20), nullable=True)
    
    # BUSINESS LOGIC
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    status = Column(Enum(UserStatus),
                    default=UserStatus.PENDING_VERIFICATION, nullable=False)
    
    # Email verification status
    is_email_verified = Column(Boolean, default=False, nullable=False)
    # Phone verification status (SMS)
    is_phone_verified = Column(Boolean, default=False, nullable=False)
    
    # User's bio/description (for profiles, reviews, etc.)
    bio = Column(Text, nullable=True)
    
    #super user 
    is_superuser =  Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # relation
    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def full_name(self) -> str:
        """
        Get user's full name by combining first and last names.

        Returns:
            Full name like "John Smith" (strip to handle edge cases)
        """
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_active(self) -> bool:
        """
        Check if user account is fully active.

        Returns:
            True if status is ACTIVE, False otherwise

        Use Case:
            Used in authentication to check if user should be allowed to login

        """
        return self.status == UserStatus.ACTIVE
    
    @property
    def is_admin(self) -> bool:
        """
        Check if user is a system administrator.

        Returns:
            True if role is ADMIN, False otherwise

        Use Case:
            Used to determine if user can access admin-only features
            (user management, system configuration, view all data, etc.)
        """
        return self.role == UserRole.ADMIN
    
    @property
    def is_staff(self) -> bool:
        """
        Check if user is a system administrator staff.

        Returns:
            True if role is STAFF, False otherwise
        """
        return self.role == UserRole.STAFF
    
    @property
    def is_customer(self) -> bool:
        """
        Check if user is a registered customer.

        Returns:
            True if role is CUSTOMER, False otherwise
        """
        return self.role == UserRole.CUSTOMER
    
    @property
    def is_guest(self) -> bool:
        """
        Check if user is a guest customer. Cannot login to the platform.

        Returns:
            True if role is GUEST_CUSTOMER, False otherwise
        """
        return self.role == UserRole.GUEST_CUSTOMER
    