"""
配置模板服务层

封装配置模板 CRUD 和 Jinja2 渲染的业务逻辑，供路由和测试使用。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from jinja2 import Template, TemplateError

from app.shared.models import ConfigTemplate
from app.shared.exceptions import ResourceNotFoundException, ConflictException


def list_templates(db: Session) -> Dict[str, Any]:
    """获取配置模板列表

    Args:
        db: 数据库会话

    Returns:
        包含 total 和 items 的字典
    """
    templates = db.query(ConfigTemplate).order_by(ConfigTemplate.id.desc()).limit(500).all()

    return {
        "total": len(templates),
        "items": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in templates
        ]
    }


def get_template(db: Session, template_id: int) -> Dict[str, Any]:
    """获取模板详情

    Args:
        db: 数据库会话
        template_id: 模板 ID

    Returns:
        模板信息字典

    Raises:
        ResourceNotFoundException: 模板不存在
    """
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
    if not template:
        raise ResourceNotFoundException("Template")

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "template_content": template.template_content,
        "variables": template.variables,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }


def create_template(db: Session, template_data: Dict[str, Any]) -> Dict[str, Any]:
    """创建配置模板

    Args:
        db: 数据库会话
        template_data: 模板数据（name, description, template_content, variables）

    Returns:
        创建的模板信息

    Raises:
        ConflictException: 模板名称已存在
    """
    name = template_data.get("name")
    if not name:
        raise ValueError("模板名称不能为空")

    existing = db.query(ConfigTemplate).filter(ConfigTemplate.name == name).first()
    if existing:
        raise ConflictException(f"模板名称 '{name}' 已存在")

    template = ConfigTemplate(**template_data)
    db.add(template)
    db.commit()
    db.refresh(template)

    return {
        "id": template.id,
        "name": template.name,
        "message": "模板创建成功",
    }


def update_template(db: Session, template_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """更新配置模板

    Args:
        db: 数据库会话
        template_id: 模板 ID
        update_data: 要更新的字段

    Returns:
        更新后的模板信息

    Raises:
        ResourceNotFoundException: 模板不存在
    """
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
    if not template:
        raise ResourceNotFoundException("Template")

    # 如果更新名称，检查是否重复
    new_name = update_data.get("name")
    if new_name and new_name != template.name:
        existing = db.query(ConfigTemplate).filter(ConfigTemplate.name == new_name).first()
        if existing:
            raise ConflictException(f"模板名称 '{new_name}' 已存在")

    for key, value in update_data.items():
        if hasattr(template, key):
            setattr(template, key, value)

    db.commit()
    db.refresh(template)

    return {
        "id": template.id,
        "name": template.name,
        "message": "更新成功",
    }


def delete_template(db: Session, template_id: int) -> Dict[str, Any]:
    """删除配置模板

    Args:
        db: 数据库会话
        template_id: 模板 ID

    Returns:
        操作结果

    Raises:
        ResourceNotFoundException: 模板不存在
    """
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
    if not template:
        raise ResourceNotFoundException("Template")

    db.delete(template)
    db.commit()

    return {"success": True, "message": "删除成功"}


def render_template(db: Session, template_id: int, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """渲染 Jinja2 模板

    Args:
        db: 数据库会话
        template_id: 模板 ID
        variables: 模板变量

    Returns:
        渲染后的内容

    Raises:
        ResourceNotFoundException: 模板不存在
        ValueError: 模板渲染失败
    """
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
    if not template:
        raise ResourceNotFoundException("Template")

    try:
        tmpl = Template(template.template_content)
        context: Dict[str, Any] = {
            "now": datetime.utcnow,
            "now_str": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if variables:
            context.update(variables)

        rendered = tmpl.render(**context)
        return {"content": rendered, "template_name": template.name}

    except TemplateError as e:
        raise ValueError(f"模板渲染失败: {str(e)}")
