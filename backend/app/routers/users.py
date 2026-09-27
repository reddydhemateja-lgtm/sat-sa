from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import record_audit
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.user import RoleEnum, User
from app.schemas.user import UserCreate, UserOut
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=list[UserOut],
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.SUPERVISOR))],
)
async def list_users(db: AsyncSession = Depends(get_db)) -> list[UserOut]:
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    return [UserOut.model_validate(u) for u in users]


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(RoleEnum.ADMIN))],
)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOut:
    existing = await db.execute(
        select(User).where(
            (User.username == payload.username) | (User.email == payload.email)
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()

    await record_audit(
        db,
        user_id=current_user.id,
        action="USER_CREATE",
        target_type="user",
        target_id=user.id,
        new_value={
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
        },
    )

    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)