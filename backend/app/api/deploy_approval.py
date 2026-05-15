"""
审批API
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.approval import DeployApproval, ApprovalStatus
from app.services.backup_rollback_service import ApprovalService

router = APIRouter(prefix="/deploy-approval", tags=["deploy-approval"])


@router.post("/request")
async def create_approval_request(
    task_id: str,
    approval_level: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建审批请求"""
    result = await ApprovalService.create_approval_request(
        db=db,
        task_id=task_id,
        requester_id=current_user.id,
        approval_level=approval_level,
        deploy_data={}
    )
    return result


@router.post("/{approval_id}/approve")
async def approve_deployment(
    approval_id: int,
    comment: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批准部署"""
    result = await ApprovalService.approve_deployment(
        db=db,
        approval_id=approval_id,
        approver_id=current_user.id,
        comment=comment
    )
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result


@router.post("/{approval_id}/reject")
async def reject_deployment(
    approval_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """拒绝部署"""
    result = await ApprovalService.reject_deployment(
        db=db,
        approval_id=approval_id,
        approver_id=current_user.id,
        reason=reason
    )
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result


@router.get("/pending")
async def list_pending_approvals(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取待审批列表"""
    query = db.query(DeployApproval).filter(
        DeployApproval.status == ApprovalStatus.PENDING_APPROVAL
    )

    total = query.count()
    approvals = query.order_by(desc(DeployApproval.requested_at)) \
                     .offset((page - 1) * size) \
                     .limit(size) \
                     .all()

    return {
        "total": total,
        "items": [a.to_dict() for a in approvals],
        "page": page,
        "size": size
    }


@router.get("/my")
async def list_my_approvals(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的审批（我申请的）"""
    query = db.query(DeployApproval).filter(
        DeployApproval.requester_id == current_user.id
    )

    if status:
        query = query.filter(DeployApproval.status == status)

    total = query.count()
    approvals = query.order_by(desc(DeployApproval.requested_at)) \
                     .offset((page - 1) * size) \
                     .limit(size) \
                     .all()

    return {
        "total": total,
        "items": [a.to_dict() for a in approvals],
        "page": page,
        "size": size
    }


@router.get("/{approval_id}")
async def get_approval_detail(
    approval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取审批详情"""
    approval = db.query(DeployApproval).filter(DeployApproval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval.to_dict()
