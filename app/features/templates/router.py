"""Configuration template management router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.shared.database import get_db
from .template_service import (
    list_templates as svc_list_templates,
    get_template as svc_get_template,
    create_template as svc_create_template,
    update_template as svc_update_template,
    delete_template as svc_delete_template,
    render_template as svc_render_template,
)
from app.shared.exceptions import ResourceNotFoundException

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
async def api_list_templates(db: Session = Depends(get_db)):
    """获取配置模板列表"""
    return svc_list_templates(db)


@router.post("")
async def api_create_template(template_data: dict, db: Session = Depends(get_db)):
    """创建配置模板"""
    result = svc_create_template(db, template_data)
    return {"id": result["id"], "message": result["message"]}


@router.get("/{template_id}")
async def api_get_template(template_id: int, db: Session = Depends(get_db)):
    """获取模板详情"""
    return svc_get_template(db, template_id)


@router.put("/{template_id}")
async def api_update_template(template_id: int, template_data: dict, db: Session = Depends(get_db)):
    """更新配置模板"""
    result = svc_update_template(db, template_id, template_data)
    return {"id": result["id"], "message": result["message"]}


@router.delete("/{template_id}")
async def api_delete_template(template_id: int, db: Session = Depends(get_db)):
    """删除配置模板"""
    result = svc_delete_template(db, template_id)
    return result


@router.post("/{template_id}/render")
async def api_render_template(template_id: int, variables: dict = None, db: Session = Depends(get_db)):
    """渲染 Jinja2 模板"""
    try:
        result = svc_render_template(db, template_id, variables)
        return {"content": result["content"], "template_name": result["template_name"]}
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="模板不存在")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
