"""
Tests for template_service.py
"""

import pytest
from sqlalchemy.orm import Session

from app.shared.models import ConfigTemplate
from app.features.templates.template_service import (
    list_templates, get_template, create_template,
    update_template, delete_template, render_template,
)
from app.shared.exceptions import ResourceNotFoundException, ConflictException


class TestListTemplates:
    def test_list_templates_empty(self, db_session):
        result = list_templates(db_session)
        assert result["total"] == 0
        assert result["items"] == []

    def test_list_templates_with_data(self, db_session, sample_template_data):
        create_template(db_session, sample_template_data)
        result = list_templates(db_session)
        assert result["total"] == 1
        assert result["items"][0]["name"] == "basic-access-switch"

    def test_list_templates_multiple(self, db_session, sample_template_data):
        create_template(db_session, sample_template_data)
        create_template(db_session, {
            "name": "core-switch",
            "description": "Core switch template",
            "template_content": "hostname {{ HOSTNAME }}\n",
        })
        result = list_templates(db_session)
        assert result["total"] == 2


class TestGetTemplate:
    def test_get_template_success(self, db_session, sample_template_data):
        create_result = create_template(db_session, sample_template_data)
        result = get_template(db_session, create_result["id"])
        assert result["name"] == "basic-access-switch"
        assert "template_content" in result
        assert "variables" in result
        assert "created_at" in result

    def test_get_template_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundException):
            get_template(db_session, 999)


class TestCreateTemplate:
    def test_create_template(self, db_session, sample_template_data):
        result = create_template(db_session, sample_template_data)
        assert "id" in result
        assert result["name"] == "basic-access-switch"
        assert "message" in result

    def test_create_template_duplicate_name(self, db_session, sample_template_data):
        create_template(db_session, sample_template_data)
        with pytest.raises(ConflictException) as exc_info:
            create_template(db_session, sample_template_data)
        assert "已存在" in str(exc_info.value)

    def test_create_template_no_name(self, db_session):
        with pytest.raises(ValueError):
            create_template(db_session, {"description": "no name"})


class TestUpdateTemplate:
    def test_update_template(self, db_session, sample_template_data):
        create_result = create_template(db_session, sample_template_data)
        result = update_template(db_session, create_result["id"], {"description": "updated desc"})
        assert result["message"] == "更新成功"

        # Verify update persisted
        updated = get_template(db_session, create_result["id"])
        assert updated["description"] == "updated desc"

    def test_update_template_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundException):
            update_template(db_session, 999, {"description": "nope"})

    def test_update_template_duplicate_name(self, db_session, sample_template_data):
        create_template(db_session, sample_template_data)
        create_template(db_session, {
            "name": "another-template",
            "template_content": "test",
        })
        with pytest.raises(ConflictException):
            update_template(db_session, 2, {"name": "basic-access-switch"})

    def test_update_template_content(self, db_session, sample_template_data):
        create_result = create_template(db_session, sample_template_data)
        update_template(db_session, create_result["id"], {
            "template_content": "hostname {{ NEW_VAR }}\n",
        })
        updated = get_template(db_session, create_result["id"])
        assert "NEW_VAR" in updated["template_content"]


class TestDeleteTemplate:
    def test_delete_template(self, db_session, sample_template_data):
        create_result = create_template(db_session, sample_template_data)
        result = delete_template(db_session, create_result["id"])
        assert result["success"] is True

        with pytest.raises(ResourceNotFoundException):
            get_template(db_session, create_result["id"])

    def test_delete_template_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundException):
            delete_template(db_session, 999)


class TestRenderTemplate:
    def test_render_template_basic(self, db_session):
        create_result = create_template(db_session, {
            "name": "render-test",
            "template_content": "hostname {{ HOSTNAME }}\nip address {{ IP }}\n",
        })
        result = render_template(db_session, create_result["id"], {
            "HOSTNAME": "SW-01",
            "IP": "192.168.1.1",
        })
        assert "hostname SW-01" in result["content"]
        assert "ip address 192.168.1.1" in result["content"]
        assert result["template_name"] == "render-test"

    def test_render_template_no_variables(self, db_session):
        create_result = create_template(db_session, {
            "name": "static-template",
            "template_content": "This is static content.\nTimestamp: {{ now_str }}\n",
        })
        result = render_template(db_session, create_result["id"])
        assert "This is static content." in result["content"]
        assert "Timestamp:" in result["content"]

    def test_render_template_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundException):
            render_template(db_session, 999, {})

    def test_render_template_invalid_jinja(self, db_session):
        create_result = create_template(db_session, {
            "name": "bad-template",
            "template_content": "hostname {{ INVALID SYNTAX",
        })
        with pytest.raises(ValueError) as exc_info:
            render_template(db_session, create_result["id"])
        assert "渲染失败" in str(exc_info.value)

    def test_render_template_with_now_context(self, db_session):
        create_result = create_template(db_session, {
            "name": "time-test",
            "template_content": "Generated at: {{ now_str }}\n",
        })
        result = render_template(db_session, create_result["id"])
        assert "Generated at:" in result["content"]
        # now_str should be a formatted timestamp
        assert len(result["content"]) > 20
