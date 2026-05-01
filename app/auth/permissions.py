from fastapi import Depends, HTTPException, status
from app.models.user import UserRole
from app.services.security import get_current_user

def admin_required(current_user = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def staff_required(current_user = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required"
        )
    return current_user

def role_required(allowed_roles: list[UserRole]):
    def checker(current_user = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        return current_user
    return checker

##permissions
admin_only = role_required([UserRole.ADMIN])
staff_only = role_required([UserRole.ADMIN, UserRole.STAFF])
customer_only = role_required([UserRole.CUSTOMER])