"""Configuration template management router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from jinja2 import Template

from ..database import get_db
from ..models import ConfigTemplate

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
async def list_templates():
    """获取配置模板列表"""
    db: Session = next(get_db())
    templates = db.query(ConfigTemplate).all()

    return {
        "items": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in templates
        ]
    }


@router.post("")
async def create_template(template_data: dict):
    """创建配置模板"""
    db: Session = next(get_db())

    template = ConfigTemplate(**template_data)
    db.add(template)
    db.commit()
    db.refresh(template)

    return {"id": template.id, "message": "模板创建成功"}


@router.get("/{template_id}")
async def get_template(template_id: int):
    """获取模板详情"""
    db: Session = next(get_db())
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "template_content": template.template_content,
        "variables": template.variables
    }


@router.put("/{template_id}")
async def update_template(template_id: int, template_data: dict):
    """更新配置模板"""
    db: Session = next(get_db())
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    for key, value in template_data.items():
        if hasattr(template, key):
            setattr(template, key, value)

    db.commit()
    db.refresh(template)

    return {"id": template.id, "message": "更新成功"}


@router.delete("/{template_id}")
async def delete_template(template_id: int):
    """删除配置模板"""
    db: Session = next(get_db())
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    db.delete(template)
    db.commit()

    return {"message": "删除成功"}


@router.post("/{template_id}/render")
async def render_template(template_id: int, variables: dict = None):
    """渲染 Jinja2 模板"""
    db: Session = next(get_db())
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    tmpl = Template(template.template_content)
    context = {
        "now": datetime.utcnow,
        "now_str": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }
    if variables:
        context.update(variables)

    rendered = tmpl.render(**context)

    return {"content": rendered}
