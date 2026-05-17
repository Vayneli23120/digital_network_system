"""Configuration deployment router"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
from jinja2 import Template

from app.shared.database import get_db
from app.shared.models import Device, ConfigTemplate, CredentialGroup, BackupRecord, AuditLog
from app.features.credentials.credential_service import decrypt_password
from .deploy_service import get_deploy_service
from .napalm_service import get_napalm_service
from .config_diff_service import ConfigDiffService, ConfigDiffResult, DiffType, DiffLine

router = APIRouter(prefix="/api/deploy", tags=["deploy"])

# 每个请求使用独立的线程池，避免全局资源争抢
@asynccontextmanager
async def get_deploy_executor(max_workers: int):
    """获取部署专用的线程池执行器，自动清理"""
    executor = ThreadPoolExecutor(max_workers=max_workers)
    try:
        yield executor
    finally:
        executor.shutdown(wait=False)  # 不等待，快速释放


@router.post("/preview")
async def preview_deploy(deploy_data: dict):
    """
    预览配置部署变更（增强版）
    """
    db: Session = next(get_db())

    try:
        mode = deploy_data.get('mode', 'backup')
        target_device_ids = deploy_data.get('target_devices', [])
        variables = deploy_data.get('variables', {})

        if not target_device_ids:
            raise HTTPException(status_code=400, detail="请选择至少一台设备")

        # 获取设备列表
        devices = db.query(Device).filter(Device.id.in_(target_device_ids)).all()
        if not devices:
            raise HTTPException(status_code=404, detail="未找到指定的设备")

        # 获取配置内容
        config_content = ""
        if mode == 'backup':
            backup_file = deploy_data.get('backup_file')
            if backup_file:
                backup_path = Path(backup_file)
                if not backup_path.exists():
                    backup_path = Path(f"./backups/{backup_file}")
                if backup_path.exists():
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        config_content = f.read()

        elif mode == 'template':
            template_id = deploy_data.get('template_id')
            if template_id:
                template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
                if template:
                    tmpl = Template(template.template_content)
                    context = {'now': datetime.utcnow, 'now_str': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}
                    context.update(variables)
                    config_content = tmpl.render(**context)

        elif mode == 'snippet':
            # 配置片段模式：将片段追加到当前配置
            snippet_content = deploy_data.get('snippet', '')
            snippet_position = deploy_data.get('snippet_position', 'append')  # append, prepend, replace

            # 先获取基础配置（从备份或模板）
            base_config = ""
            if deploy_data.get('base_backup_file'):
                backup_path = Path(deploy_data['base_backup_file'])
                if not backup_path.exists():
                    backup_path = Path(f"./backups/{deploy_data['base_backup_file']}")
                if backup_path.exists():
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        base_config = f.read()

            # 应用变量替换到片段
            if variables:
                for key, value in variables.items():
                    snippet_content = snippet_content.replace(f"{{{{{key}}}}}", str(value))

            # 根据位置合并配置
            if snippet_position == 'append':
                config_content = base_config + "\n! \n! 新增配置片段\n" + snippet_content if base_config else snippet_content
            elif snippet_position == 'prepend':
                config_content = snippet_content + "\n! \n! 原有配置\n" + base_config if base_config else snippet_content
            elif snippet_position == 'replace':
                config_content = snippet_content
            else:
                config_content = snippet_content

        # 为每个设备生成差异分析
        preview_results = []
        for device in devices:
            # 获取当前配置（从最新备份文件，而非数据库快照）
            current_config = ""
            latest_backup = db.query(BackupRecord).filter(
                BackupRecord.device_id == device.id
            ).order_by(BackupRecord.backup_time.desc()).first()
            if latest_backup:
                # 优先从文件读取，数据库 snapshot 可能为空
                backup_path = Path(latest_backup.backup_file)
                if not backup_path.exists():
                    backup_path = Path(f"./backups/{latest_backup.backup_file}")
                if backup_path.exists():
                    try:
                        with open(backup_path, 'r', encoding='utf-8') as f:
                            current_config = f.read()
                    except Exception as e:
                        logger.warning(f"读取备份文件失败 {backup_path}: {e}")
                        current_config = latest_backup.config_snapshot or ""
                else:
                    current_config = latest_backup.config_snapshot or ""

            # 片段模式特殊处理：只显示增量变更
            if mode == 'snippet':
                snippet_content = deploy_data.get('snippet', '').strip()
                snippet_position = deploy_data.get('snippet_position', 'append')

                # 应用变量替换
                if variables:
                    for key, value in variables.items():
                        snippet_content = snippet_content.replace(f"{{{{{key}}}}}", str(value))

                # 构建新配置（确保换行符处理正确）
                current_config_normalized = current_config.rstrip('\n')
                current_config_lines = current_config_normalized.splitlines()

                if snippet_position == 'replace':
                    # 替换模式：片段完全替换原配置
                    diff_result = ConfigDiffService.analyze_diff(current_config, snippet_content)
                    impact = ConfigDiffService.estimate_impact(diff_result)
                    new_config = snippet_content
                elif snippet_position == 'smart':
                    # 智能模式：识别命令类型，原地替换/删除
                    new_config_lines = current_config_lines.copy()
                    diff_lines = []
                    removed_lines = []  # 记录被删除的行号

                    snippet_lines = snippet_content.splitlines()
                    for snippet_line in snippet_lines:
                        snippet_line_stripped = snippet_line.strip()

                        # 检查是否是 "no xxx" 删除命令
                        if snippet_line_stripped.startswith('no '):
                            # 提取要删除的命令关键字
                            target_cmd = snippet_line_stripped[3:].strip()  # 去掉 "no "
                            cmd_keyword = target_cmd.split()[0] if target_cmd.split() else target_cmd

                            # 在原配置中查找匹配的行并删除
                            found_and_removed = False
                            for idx, orig_line in enumerate(current_config_lines):
                                orig_stripped = orig_line.strip()
                                # 匹配：行以该命令关键字开头
                                if orig_stripped.startswith(cmd_keyword) or orig_stripped == target_cmd:
                                    # 检查是否已被删除（避免重复）
                                    line_num = idx + 1
                                    if line_num not in removed_lines:
                                        removed_lines.append(line_num)
                                        # 在新配置中标记删除（用空行占位或直接移除）
                                        # 这里采用直接移除的方式
                                        diff_lines.append(DiffLine(
                                            type=DiffType.REMOVED,
                                            content=orig_line,
                                            old_line_num=line_num,
                                            new_line_num=None
                                        ))
                                        found_and_removed = True
                            if not found_and_removed:
                                # 未找到对应配置，no 命令本身作为新增显示
                                pass  # 不显示，因为删除不存在的配置没有实际效果

                        # 检查是否是可替换的单行命令
                        elif snippet_line_stripped.startswith('hostname '):
                            # hostname 替换
                            for idx, orig_line in enumerate(current_config_lines):
                                if orig_line.strip().startswith('hostname '):
                                    line_num = idx + 1
                                    if line_num not in removed_lines:
                                        removed_lines.append(line_num)
                                        diff_lines.append(DiffLine(
                                            type=DiffType.REMOVED,
                                            content=orig_line,
                                            old_line_num=line_num,
                                            new_line_num=None
                                        ))
                                        # 替换为新行
                                        new_config_lines[idx] = snippet_line
                                        diff_lines.append(DiffLine(
                                            type=DiffType.ADDED,
                                            content=snippet_line,
                                            old_line_num=None,
                                            new_line_num=line_num
                                        ))
                                    break
                            else:
                                # 未找到原 hostname，添加到末尾
                                new_config_lines.append(snippet_line)
                                new_line_num = len(new_config_lines)
                                diff_lines.append(DiffLine(
                                    type=DiffType.ADDED,
                                    content=snippet_line,
                                    old_line_num=None,
                                    new_line_num=new_line_num
                                ))

                        elif snippet_line_stripped.startswith('ntp server '):
                            # ntp server 替换（可能有多个，替换第一个或添加）
                            replaced = False
                            for idx, orig_line in enumerate(current_config_lines):
                                if orig_line.strip().startswith('ntp server '):
                                    line_num = idx + 1
                                    if line_num not in removed_lines:
                                        removed_lines.append(line_num)
                                        diff_lines.append(DiffLine(
                                            type=DiffType.REMOVED,
                                            content=orig_line,
                                            old_line_num=line_num,
                                            new_line_num=None
                                        ))
                                        new_config_lines[idx] = snippet_line
                                        diff_lines.append(DiffLine(
                                            type=DiffType.ADDED,
                                            content=snippet_line,
                                            old_line_num=None,
                                            new_line_num=line_num
                                        ))
                                        replaced = True
                                        break
                            if not replaced:
                                new_config_lines.append(snippet_line)
                                new_line_num = len(new_config_lines)
                                diff_lines.append(DiffLine(
                                    type=DiffType.ADDED,
                                    content=snippet_line,
                                    old_line_num=None,
                                    new_line_num=new_line_num
                                ))

                        elif snippet_line_stripped.startswith('snmp-server location '):
                            # snmp-server location 替换
                            replaced = False
                            for idx, orig_line in enumerate(current_config_lines):
                                if orig_line.strip().startswith('snmp-server location '):
                                    line_num = idx + 1
                                    if line_num not in removed_lines:
                                        removed_lines.append(line_num)
                                        diff_lines.append(DiffLine(
                                            type=DiffType.REMOVED,
                                            content=orig_line,
                                            old_line_num=line_num,
                                            new_line_num=None
                                        ))
                                        new_config_lines[idx] = snippet_line
                                        diff_lines.append(DiffLine(
                                            type=DiffType.ADDED,
                                            content=snippet_line,
                                            old_line_num=None,
                                            new_line_num=line_num
                                        ))
                                        replaced = True
                                        break
                            if not replaced:
                                new_config_lines.append(snippet_line)
                                new_line_num = len(new_config_lines)
                                diff_lines.append(DiffLine(
                                    type=DiffType.ADDED,
                                    content=snippet_line,
                                    old_line_num=None,
                                    new_line_num=new_line_num
                                ))

                        elif snippet_line_stripped.startswith('snmp-server contact '):
                            # snmp-server contact 替换
                            replaced = False
                            for idx, orig_line in enumerate(current_config_lines):
                                if orig_line.strip().startswith('snmp-server contact '):
                                    line_num = idx + 1
                                    if line_num not in removed_lines:
                                        removed_lines.append(line_num)
                                        diff_lines.append(DiffLine(
                                            type=DiffType.REMOVED,
                                            content=orig_line,
                                            old_line_num=line_num,
                                            new_line_num=None
                                        ))
                                        new_config_lines[idx] = snippet_line
                                        diff_lines.append(DiffLine(
                                            type=DiffType.ADDED,
                                            content=snippet_line,
                                            old_line_num=None,
                                            new_line_num=line_num
                                        ))
                                        replaced = True
                                        break
                            if not replaced:
                                new_config_lines.append(snippet_line)
                                new_line_num = len(new_config_lines)
                                diff_lines.append(DiffLine(
                                    type=DiffType.ADDED,
                                    content=snippet_line,
                                    old_line_num=None,
                                    new_line_num=new_line_num
                                ))

                        else:
                            # 其他命令：直接追加到末尾（fallback）
                            new_config_lines.append(snippet_line)
                            new_line_num = len(new_config_lines)
                            diff_lines.append(DiffLine(
                                type=DiffType.ADDED,
                                content=snippet_line,
                                old_line_num=None,
                                new_line_num=new_line_num
                            ))

                    # 构建最终新配置
                    new_config = '\n'.join(new_config_lines)

                    # 统计
                    added_count = sum(1 for l in diff_lines if l.type == DiffType.ADDED)
                    removed_count = sum(1 for l in diff_lines if l.type == DiffType.REMOVED)

                    diff_result = ConfigDiffResult(
                        old_config=current_config,
                        new_config=new_config,
                        lines=diff_lines,
                        stats={"added": added_count, "removed": removed_count, "modified": 0, "unchanged": len(current_config_lines) - removed_count}
                    )
                    impact = ConfigDiffService.estimate_impact(diff_result)

                elif snippet_position == 'append':
                    # 追加模式：片段在当前配置末尾
                    snippet_lines = snippet_content.splitlines()
                    current_config_lines = current_config_normalized.splitlines()
                    current_line_count = len(current_config_lines)

                    # 构建新配置：原配置 + 分隔行 + 片段
                    separator = "\n!\n! 追加配置\n"
                    new_config = current_config_normalized + separator + snippet_content

                    # 计算片段在新配置中的起始行号
                    # +1 for separator newline, +1 for "!", +1 for "! 追加配置"
                    start_line = current_line_count + 3

                    diff_lines = []
                    for i, line in enumerate(snippet_lines):
                        diff_lines.append(DiffLine(
                            type=DiffType.ADDED,
                            content=line,
                            old_line_num=None,
                            new_line_num=start_line + i
                        ))

                    # 创建 diff_result 用于后续统计
                    diff_result = ConfigDiffResult(
                        old_config=current_config,
                        new_config=new_config,
                        lines=diff_lines,
                        stats={"added": len(snippet_lines), "removed": 0, "modified": 0, "unchanged": current_line_count}
                    )
                    impact = ConfigDiffService.estimate_impact(diff_result)
                elif snippet_position == 'prepend':
                    # 插入模式：片段在当前配置开头
                    snippet_lines = snippet_content.splitlines()

                    # 构建新配置：片段 + 分隔行 + 原配置
                    separator = "!\n! 原有配置\n"
                    new_config = snippet_content + "\n" + separator + current_config_normalized

                    diff_lines = []
                    # 片段行号从1开始
                    for i, line in enumerate(snippet_lines):
                        diff_lines.append(DiffLine(
                            type=DiffType.ADDED,
                            content=line,
                            old_line_num=None,
                            new_line_num=i + 1
                        ))

                    diff_result = ConfigDiffResult(
                        old_config=current_config,
                        new_config=new_config,
                        lines=diff_lines,
                        stats={"added": len(snippet_lines), "removed": 0, "modified": 0, "unchanged": len(current_config_normalized.splitlines())}
                    )
                    impact = ConfigDiffService.estimate_impact(diff_result)
                else:
                    # 默认按追加处理
                    snippet_lines = snippet_content.splitlines()
                    current_config_lines = current_config_normalized.splitlines()
                    current_line_count = len(current_config_lines)
                    start_line = current_line_count + 3

                    diff_lines = []
                    for i, line in enumerate(snippet_lines):
                        diff_lines.append(DiffLine(
                            type=DiffType.ADDED,
                            content=line,
                            old_line_num=None,
                            new_line_num=start_line + i
                        ))
                    new_config = current_config_normalized + "\n!\n! 追加配置\n" + snippet_content

                    diff_result = ConfigDiffResult(
                        old_config=current_config,
                        new_config=new_config,
                        lines=diff_lines,
                        stats={"added": len(snippet_lines), "removed": 0, "modified": 0, "unchanged": current_line_count}
                    )
                    impact = ConfigDiffService.estimate_impact(diff_result)
            else:
                # 其他模式：生成完整差异分析
                diff_result = ConfigDiffService.analyze_diff(current_config, config_content)
                impact = ConfigDiffService.estimate_impact(diff_result)
                new_config = config_content

            preview_results.append({
                "device_id": device.id,
                "device_name": device.name,
                "device_ip": device.ip,
                "old_config": current_config,
                "new_config": new_config,
                "diff": {
                    "lines": [
                        {
                            "type": line.type.value,
                            "content": line.content,
                            "old_line_num": line.old_line_num,
                            "new_line_num": line.new_line_num
                        }
                        for line in diff_result.lines[:100]
                    ],
                    "stats": diff_result.stats
                },
                "impact": impact
            })

        return {
            "success": True,
            "preview": preview_results,
            "summary": {
                "total_devices": len(preview_results),
                "total_changes": sum(p["diff"]["stats"]["added"] + p["diff"]["stats"]["removed"]
                                    for p in preview_results),
                "high_risk_devices": sum(1 for p in preview_results
                                         if p["impact"]["risk_level"] == "high")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览部署失败：{e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"预览失败：{str(e)}")
    finally:
        db.close()


@router.post("/execute")
async def execute_deploy(deploy_data: dict):
    """
    执行配置部署

    请求体:
    {
        "mode": "backup" | "template" | "snippet",
        "engine": "napalm" | "netmiko",  // 部署引擎，默认 napalm
        "napalm_mode": "merge" | "replace",  // NAPALM 模式，默认 merge
        "backup_file": "备份文件路径",
        "template_id": 模板 ID,
        "snippet": "配置片段内容",
        "snippet_position": "smart" | "append" | "prepend" | "replace",
        "variables": {"变量名": "变量值"},
        "target_devices": [设备 ID 列表],
        "dry_run": false
    }
    """
    db: Session = next(get_db())

    try:
        mode = deploy_data.get('mode', 'backup')
        engine = deploy_data.get('engine', 'napalm')  # napalm | netmiko，默认 napalm
        napalm_mode = deploy_data.get('napalm_mode', 'merge')  # merge | replace
        target_device_ids = deploy_data.get('target_devices', [])
        variables = deploy_data.get('variables', {})
        dry_run = deploy_data.get('dry_run', False)

        if not target_device_ids:
            raise HTTPException(status_code=400, detail="请选择至少一台设备")

        # 获取设备列表
        devices = db.query(Device).filter(Device.id.in_(target_device_ids)).all()
        if not devices:
            raise HTTPException(status_code=404, detail="未找到指定的设备")

        # 获取凭证组列表
        credential_groups_data = db.query(CredentialGroup).all()
        credential_groups = []
        for g in credential_groups_data:
            try:
                password = decrypt_password(g.password_encrypted) if g.password_encrypted else ''
                enable_password = decrypt_password(g.enable_password_encrypted) if g.enable_password_encrypted else None
                credential_groups.append({
                    'id': g.id,
                    'name': g.name,
                    'username': g.username,
                    'password': password,
                    'enable_password': enable_password
                })
            except Exception as cred_error:
                logger.warning(f"凭证组 {g.name} 解密失败: {cred_error}")
                # 跳过无法解密的凭证组
                continue

        if not credential_groups:
            raise HTTPException(status_code=500, detail="无法解密任何凭证组，请检查加密密钥配置")

        # 获取配置内容
        config_content = None
        if mode == 'backup':
            backup_file = deploy_data.get('backup_file')
            if not backup_file:
                raise HTTPException(status_code=400, detail="请选择备份文件")

            backup_path = Path(backup_file)
            if not backup_path.exists():
                backup_path = Path(f"./backups/{backup_file}")

            if not backup_path.exists():
                raise HTTPException(status_code=404, detail=f"备份文件不存在：{backup_file}")

            with open(backup_path, 'r', encoding='utf-8') as f:
                config_content = f.read()

        elif mode == 'template':
            template_id = deploy_data.get('template_id')
            if not template_id:
                raise HTTPException(status_code=400, detail="请选择配置模板")

            template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
            if not template:
                raise HTTPException(status_code=404, detail=f"模板不存在：{template_id}")

            tmpl = Template(template.template_content)
            context = {
                'now': datetime.utcnow,
                'now_str': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            }
            context.update(variables)
            config_content = tmpl.render(**context)

        elif mode == 'snippet':
            # 配置片段模式
            snippet_content = deploy_data.get('snippet', '')
            if not snippet_content:
                raise HTTPException(status_code=400, detail="请输入配置片段")

            snippet_position = deploy_data.get('snippet_position', 'append')

            # 应用变量替换
            if variables:
                for key, value in variables.items():
                    snippet_content = snippet_content.replace(f"{{{{{key}}}}}", str(value))

            # 如果需要基于现有配置
            base_config = ""
            if deploy_data.get('base_backup_file'):
                backup_path = Path(deploy_data['base_backup_file'])
                if not backup_path.exists():
                    backup_path = Path(f"./backups/{deploy_data['base_backup_file']}")
                if backup_path.exists():
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        base_config = f.read()

            # 合并配置
            if snippet_position == 'append':
                config_content = base_config + "\n! \n! 新增配置片段\n" + snippet_content if base_config else snippet_content
            elif snippet_position == 'prepend':
                config_content = snippet_content + "\n! \n! 原有配置\n" + base_config if base_config else snippet_content
            elif snippet_position == 'replace':
                config_content = snippet_content
            else:
                config_content = snippet_content

        else:
            raise HTTPException(status_code=400, detail=f"不支持的部署模式：{mode}")

        # ========== 阶段1：数据库操作完成，关闭 Session ==========
        # 将设备数据转为纯字典（脱离 SQLAlchemy 对象，避免线程安全问题）
        device_data_list = [
            {
                'id': device.id,
                'name': device.name,
                'ip': device.ip,
                'device_type': 'cisco_ios',
                'credential_group': device.credential_group or 'default'
            }
            for device in devices
        ]

        # 关闭数据库连接（并行执行阶段不访问数据库）
        db.close()
        logger.info("数据库读取完成，关闭连接，开始部署")

        # ========== 阶段2：执行部署（完全隔离数据库） ==========
        parallel_limit = deploy_data.get('parallel_limit', 1)
        # 单设备部署超时时间（秒）
        DEVICE_TIMEOUT = 120

        logger.info(f"部署参数: engine={engine}, napalm_mode={napalm_mode}, parallel_limit={parallel_limit}")

        # 选择部署引擎
        if engine == 'napalm':
            deploy_service = get_napalm_service()
            logger.info(f"使用 NAPALM 引擎部署 (mode={napalm_mode})")
        else:
            deploy_service = get_deploy_service()
            logger.info(f"使用 Netmiko 引擎部署")

        results = []
        loop = asyncio.get_event_loop()

        if parallel_limit == 1:
            # ========== 串行模式：简单逐个执行 ==========
            logger.info(f"串行模式：逐个部署 {len(device_data_list)} 个设备")
            for device_dict in device_data_list:
                logger.info(f"开始部署设备: {device_dict['name']}")
                try:
                    if engine == 'napalm':
                        result = await asyncio.wait_for(
                            loop.run_in_executor(
                                None,  # 使用默认 executor
                                lambda d=device_dict: deploy_service.deploy_to_device(
                                    device=d,
                                    config=config_content,
                                    credential_groups=credential_groups,
                                    dry_run=dry_run,
                                    mode=napalm_mode
                                )
                            ),
                            timeout=DEVICE_TIMEOUT
                        )
                    else:
                        result = await asyncio.wait_for(
                            loop.run_in_executor(
                                None,
                                lambda d=device_dict: deploy_service.deploy_to_device(
                                    device=d,
                                    config=config_content,
                                    credential_groups=credential_groups,
                                    dry_run=dry_run
                                )
                            ),
                            timeout=DEVICE_TIMEOUT
                        )
                    results.append(result)
                    logger.info(f"设备 {device_dict['name']} 部署完成: success={result.get('success')}")
                except asyncio.TimeoutError:
                    logger.warning(f"设备 {device_dict['name']} 部署超时 ({DEVICE_TIMEOUT}s)")
                    results.append({
                        'device_id': device_dict['id'],
                        'device_name': device_dict['name'],
                        'success': False,
                        'message': f'部署超时（{DEVICE_TIMEOUT}秒）'
                    })
                except Exception as e:
                    logger.error(f"设备 {device_dict['name']} 部署异常: {e}")
                    results.append({
                        'device_id': device_dict['id'],
                        'device_name': device_dict['name'],
                        'success': False,
                        'message': f'部署异常: {str(e)}'
                    })

        else:
            # ========== 并行模式：使用线程池 + semaphore ==========
            # 整体超时时间（秒）
            TOTAL_TIMEOUT = DEVICE_TIMEOUT * len(device_data_list) / parallel_limit + 60

            # 使用独立的线程池执行器
            async with get_deploy_executor(max_workers=min(parallel_limit, 5)) as executor:
                semaphore = asyncio.Semaphore(parallel_limit)

                async def deploy_single_device(device_dict: dict):
                    """部署单个设备（带超时控制）"""
                    try:
                        if engine == 'napalm':
                            result = await asyncio.wait_for(
                                loop.run_in_executor(
                                    executor,
                                    lambda: deploy_service.deploy_to_device(
                                        device=device_dict,
                                        config=config_content,
                                        credential_groups=credential_groups,
                                        dry_run=dry_run,
                                        mode=napalm_mode
                                    )
                                ),
                                timeout=DEVICE_TIMEOUT
                            )
                        else:
                            result = await asyncio.wait_for(
                                loop.run_in_executor(
                                    executor,
                                    lambda: deploy_service.deploy_to_device(
                                        device=device_dict,
                                        config=config_content,
                                        credential_groups=credential_groups,
                                        dry_run=dry_run
                                    )
                                ),
                                timeout=DEVICE_TIMEOUT
                            )
                        return result
                    except asyncio.TimeoutError:
                        logger.warning(f"设备 {device_dict['name']} 部署超时 ({DEVICE_TIMEOUT}s)")
                        return {
                            'device_id': device_dict['id'],
                            'device_name': device_dict['name'],
                            'success': False,
                            'message': f'部署超时（{DEVICE_TIMEOUT}秒）'
                        }
                    except Exception as e:
                        logger.error(f"设备 {device_dict['name']} 部署异常: {e}")
                        return {
                            'device_id': device_dict['id'],
                            'device_name': device_dict['name'],
                            'success': False,
                            'message': f'部署异常: {str(e)}'
                        }

                async def deploy_with_semaphore(device_dict: dict):
                    """带信号量控制的部署"""
                    async with semaphore:
                        logger.info(f"开始部署设备: {device_dict['name']}")
                        result = await deploy_single_device(device_dict)
                        logger.info(f"设备 {device_dict['name']} 部署完成: success={result.get('success')}")
                        return result

                # 并行执行所有设备部署（带整体超时）
                logger.info(f"并行模式：同时部署 {len(device_data_list)} 个设备，并行数量: {parallel_limit}")
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(
                            *[deploy_with_semaphore(d) for d in device_data_list],
                            return_exceptions=True
                        ),
                        timeout=TOTAL_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    logger.error(f"整体部署超时 ({TOTAL_TIMEOUT}s)")
                    raise HTTPException(status_code=504, detail=f"部署超时，请减少设备数量或增加并行数")

                # 处理结果
                processed_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        processed_results.append({
                            'device_id': device_data_list[i]['id'],
                            'device_name': device_data_list[i]['name'],
                            'success': False,
                            'message': f'部署异常: {str(result)}'
                        })
                    else:
                        processed_results.append(result)
                results = processed_results

        # ========== 阶段3：重新获取 Session 写入审计日志 ==========
        logger.info("并行部署完成，重新获取数据库连接写入审计日志")
        db_log: Session = next(get_db())
        try:
            for device_dict, result in zip(device_data_list, results):
                action = "deploy_config_dry_run" if dry_run else "deploy_config"
                engine_text = f"引擎:{engine}"
                if engine == 'napalm':
                    engine_text += f"({napalm_mode})"
                details = f"部署模式:{mode}, {engine_text}, 结果:{'成功' if result.get('success') else '失败'}"

                audit_log = AuditLog(
                    operator="Web",
                    action=action,
                    target_type="device",
                    target_id=device_dict['id'],
                    details=details
                )
                db_log.add(audit_log)

            db_log.commit()
        except Exception as log_error:
            logger.error(f"写入审计日志失败: {log_error}")
            db_log.rollback()
        finally:
            db_log.close()

        # 计算成功/失败数量
        success_count = sum(1 for r in results if r.get('success'))
        failed_count = len(results) - success_count

        return {
            "success": True,
            "results": results,
            "summary": {
                "total": len(device_data_list),
                "success": success_count,
                "failed": failed_count
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"执行部署失败：{e}")
        logger.error(traceback.format_exc())
        # db 可能已关闭，安全地尝试 rollback
        try:
            if db and db.is_active:
                db.rollback()
                db.close()
        except:
            pass
        raise HTTPException(status_code=500, detail=f"部署失败：{str(e)}")
    # 注意：db.close() 在正常流程中已经在并行执行前关闭，
    # 这里不需要 finally 再次关闭


@router.post("/rollback")
async def rollback_deploy(rollback_data: dict):
    """
    回滚设备配置到上一版本（仅 NAPALM 支持）

    请求体:
    {
        "target_devices": [设备 ID 列表]
    }
    """
    db: Session = next(get_db())

    try:
        target_device_ids = rollback_data.get('target_devices', [])

        if not target_device_ids:
            raise HTTPException(status_code=400, detail="请选择至少一台设备")

        # 获取设备列表
        devices = db.query(Device).filter(Device.id.in_(target_device_ids)).all()
        if not devices:
            raise HTTPException(status_code=404, detail="未找到指定的设备")

        # 获取凭证组列表
        credential_groups_data = db.query(CredentialGroup).all()
        credential_groups = []
        for g in credential_groups_data:
            try:
                password = decrypt_password(g.password_encrypted) if g.password_encrypted else ''
                credential_groups.append({
                    'id': g.id,
                    'name': g.name,
                    'username': g.username,
                    'password': password,
                })
            except Exception as cred_error:
                logger.warning(f"凭证组 {g.name} 解密失败: {cred_error}")
                continue

        # 使用 NAPALM 服务回滚
        napalm_service = get_napalm_service()
        results = []
        success_count = 0
        failed_count = 0

        for device in devices:
            device_dict = {
                'id': device.id,
                'name': device.name,
                'ip': device.ip,
                'device_type': 'cisco_ios',
                'credential_group': device.credential_group or 'default'
            }

            result = napalm_service.rollback_device(
                device=device_dict,
                credential_groups=credential_groups
            )
            results.append(result)

            if result.get('success'):
                success_count += 1
            else:
                failed_count += 1

        # 记录审计日志
        for device, result in zip(devices, results):
            audit_log = AuditLog(
                operator="Web",
                action="rollback_config",
                target_type="device",
                target_id=device.id,
                details=f"配置回滚, 结果:{'成功' if result.get('success') else '失败'}"
            )
            db.add(audit_log)

        db.commit()

        return {
            "success": True,
            "results": results,
            "summary": {
                "total": len(devices),
                "success": success_count,
                "failed": failed_count
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"回滚配置失败：{e}")
        raise HTTPException(status_code=500, detail=f"回滚失败：{str(e)}")
    finally:
        db.close()


@router.get("/compatible-variables")
async def get_compatible_variables():
    """
    获取所有兼容的变量列表
    """
    return {
        "variables": [
            {"key": "HOSTNAME", "example": "SW-Access-01"},
            {"key": "ENABLE_SECRET", "example": "YourPassword123"},
            {"key": "ADMIN_USERNAME", "example": "admin"},
            {"key": "ADMIN_PASSWORD", "example": "YourAdminPass"},
            {"key": "DOMAIN_NAME", "example": "company.local"},
            {"key": "MGMT_VLAN_ID", "example": "100"},
            {"key": "MGMT_IP", "example": "192.168.1.10"},
            {"key": "MGMT_NETMASK", "example": "255.255.255.0"},
            {"key": "DEFAULT_GATEWAY", "example": "192.168.1.1"},
            {"key": "SNMP_COMMUNITY", "example": "public"},
            {"key": "LOCATION", "example": "Building-A-Floor-2"},
            {"key": "CONTACT", "example": "network-admin@company.com"},
            {"key": "NTP_SERVER", "example": "10.0.0.1"},
            {"key": "SYSLOG_SERVER", "example": "10.0.0.2"},
            {"key": "DEFAULT_ROUTE", "example": "10.0.0.1"},
            {"key": "OSPF_ROUTER_ID", "example": "1.1.1.1"},
            {"key": "ACCESS_PORT_RANGE", "example": "GigabitEthernet1/0/1-48"},
            {"key": "UPLINK_PORT", "example": "TenGigabitEthernet1/1/1"},
            {"key": "BUSINESS_VLAN_LIST", "example": "10,20,30,100"},
            {"key": "TRUNK_VLANS", "example": "10,20,30,100,200"}
        ]
    }


@router.get("/maintenance-windows")
async def get_maintenance_windows():
    """
    获取可用的维护窗口时段
    """
    windows = []
    now = datetime.now()

    for day_offset in range(1, 8):
        date = now + timedelta(days=day_offset)

        # 凌晨窗口: 02:00-06:00
        windows.append({
            "id": f"{date.strftime('%Y%m%d')}_morning",
            "date": date.strftime("%Y-%m-%d"),
            "start_time": "02:00",
            "end_time": "06:00",
            "period": "morning",  # 前端根据此生成国际化标签
            "available": True
        })

        # 下午窗口: 14:00-16:00
        windows.append({
            "id": f"{date.strftime('%Y%m%d')}_afternoon",
            "date": date.strftime("%Y-%m-%d"),
            "start_time": "14:00",
            "end_time": "16:00",
            "period": "afternoon",
            "available": True
        })

        # 晚间窗口: 22:00-02:00
        windows.append({
            "id": f"{date.strftime('%Y%m%d')}_evening",
            "date": date.strftime("%Y-%m-%d"),
            "start_time": "22:00",
            "end_time": "02:00",
            "next_day": True,
            "period": "evening",
            "available": True
        })

    return {"windows": windows}


@router.post("/schedule")
async def schedule_deploy(schedule_data: dict, db: Session = Depends(get_db)):
    """
    预约部署任务
    """
    try:
        window_id = schedule_data.get("window_id")
        deploy_data = schedule_data.get("deploy_data", {})

        # 解析维护窗口时间
        parts = window_id.split('_')
        date_str = parts[0]
        period = parts[1]

        date = datetime.strptime(date_str, "%Y%m%d")

        if period == "morning":
            scheduled_time = date.replace(hour=2, minute=0)
        elif period == "afternoon":
            scheduled_time = date.replace(hour=14, minute=0)
        else:
            scheduled_time = date.replace(hour=22, minute=0)

        # 创建预约任务（这里简化处理，实际应创建定时任务）
        return {
            "success": True,
            "task_id": f"scheduled_{window_id}",
            "scheduled_at": scheduled_time.isoformat()
        }

    except Exception as e:
        logger.error(f"预约部署失败：{e}")
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")
