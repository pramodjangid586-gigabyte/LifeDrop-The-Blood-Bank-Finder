from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from app.database.connection import query_all, execute_cmd
from app.api.auth import require_auth

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.get("")
def get_user_notifications(user: Dict[str, Any] = Depends(require_auth)):
    notifications = query_all("""
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 50
    """, (user["id"],))

    unread_count = sum(1 for n in notifications if not n["is_read"])
    return {
        "unread_count": unread_count,
        "notifications": notifications
    }

@router.put("/{notification_id}/read")
def mark_read(notification_id: int, user: Dict[str, Any] = Depends(require_auth)):
    execute_cmd(
        "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
        (notification_id, user["id"])
    )
    return {"status": "success"}

@router.put("/read-all")
def mark_all_read(user: Dict[str, Any] = Depends(require_auth)):
    execute_cmd("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user["id"],))
    return {"status": "success"}
