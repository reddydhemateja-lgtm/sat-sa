from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def record_audit(
    db: AsyncSession,
    *,
    user_id: int | None,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    previous_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    Append an entry to the audit log.

    The caller is responsible for committing the surrounding transaction.
    This function only flushes so that the entry gets an id.
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        previous_value=previous_value,
        new_value=new_value,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    return entry