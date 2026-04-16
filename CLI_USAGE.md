# CLI 工具使用指南

Network Automation System 命令行工具，用于通过命令行管理网络设备和系统功能。

## 快速开始

### Windows
```bash
nas-cli.bat <command> [options]
# 或
python -m app.cli <command> [options]
```

### Linux/Mac
```bash
./nas-cli <command> [options]
```

---

## 命令列表

### 设备管理 (`device`)
```bash
nas-cli device list              # 列出所有设备
nas-cli device list -s online    # 按状态过滤 (online/offline/maintenance/retired)
nas-cli device list -r access    # 按角色过滤 (access/distribution/core)
nas-cli device show SW-01        # 查看设备详情
nas-cli device add -n SW-01 -i 192.168.1.1 -l "Data Center"
nas-cli device update SW-01 -s maintenance  # 更新状态
nas-cli device update SW-01 -i 192.168.1.100 -l "New Location"
nas-cli device delete SW-01 -y   # 删除设备
```

### 备份管理 (`backup`)
```bash
nas-cli backup run SW-01         # 备份设备配置
nas-cli backup run SW-01 -o admin  # 指定操作员
nas-cli backup list              # 列出备份记录
nas-cli backup list -d SW-01     # 按设备过滤
```

### 故障管理 (`fault`)
```bash
nas-cli fault add -d SW-01 -s major -desc "端口故障"
nas-cli fault add -d SW-01 -s critical -desc "设备宕机" -t 120
nas-cli fault list               # 列出故障记录
nas-cli fault list -s open       # 按状态过滤 (open/investigating/resolved/closed)
nas-cli fault update 1 -s resolved  # 更新故障状态
nas-cli fault delete 1 -y        # 删除故障记录
```

### 维修管理 (`maintenance`)
```bash
nas-cli maintenance add -d SW-01 -t corrective -desc "更换端口模块" -p 500 -l 200 -h 2
nas-cli maintenance list         # 列出维修记录
nas-cli maintenance list -d SW-01 -n 10  # 按设备过滤
nas-cli maintenance update 1 --status completed  # 更新维修记录
nas-cli maintenance delete 1 -y  # 删除维修记录
```

### 日志管理 (`log`)
```bash
nas-cli log list                 # 列出最新日志
nas-cli log list -l ERROR        # 按级别过滤
nas-cli log list -d 30           # 最近 30 天日志
nas-cli log search "backup"      # 搜索日志
```

### 模板管理 (`template`)
```bash
nas-cli template list            # 列出配置模板
nas-cli template show 1          # 查看模板详情
```

### 凭证管理 (`credential`)
```bash
nas-cli credential list          # 列出凭证组
```

### 统计分析

```bash
# 简要统计
nas-cli stats

# 详细统计报表（可指定天数）
nas-cli report -n 30             # 最近 30 天报表
nas-cli report -d SW-01 -n 7     # 指定设备最近 7 天

# 成本分析（默认本月）
nas-cli cost                     # 本月成本
nas-cli cost -m 2026-03          # 指定月份
nas-cli cost -d SW-01            # 指定设备
```

### 其他命令
```bash
nas-cli init-db                  # 初始化数据库
```

---

## 选项速查

| 选项 | 说明 | 示例 |
|------|------|------|
| `-n` | 设备名称/数量 | `-n SW-01` / `-n 50` |
| `-i` | IP 地址 | `-i 192.168.1.1` |
| `-l` | 位置/限制/人工 | `-l "DC"` / `-l 50` / `-l 200` |
| `-r` | 角色 | `-r access` |
| `-s` | 状态/级别 | `-s online` / `-s critical` |
| `-d` | 设备/天数 | `-d SW-01` / `-d 7` |
| `-o` | 操作员 | `-o admin` |
| `-desc` | 描述 | `-desc "故障"` |
| `-p` | 配件费用 | `-p 500` |
| `-h` | 工时 | `-h 2` |
| `-t` | 类型 | `-t corrective` |
| `-m` | 月份 | `-m 2026-03` |

---

## 常用场景

### 1. 新设备上线
```bash
# 添加设备
nas-cli device add -n SW-New-01 -i 192.168.1.100 -l "Building A" -r access

# 备份配置
nas-cli backup run SW-New-01

# 查看备份结果
nas-cli backup list -d SW-New-01
```

### 2. 设备故障处理
```bash
# 报告故障
nas-cli fault add -d SW-01 -s critical -desc "设备无法连接" -t 60

# 更新故障状态
nas-cli fault update 1 -s investigating
nas-cli fault update 1 -s resolved

# 关闭故障
nas-cli fault update 1 -s closed
```

### 3. 设备维修记录
```bash
# 添加维修记录
nas-cli maintenance add -d SW-01 -t corrective -desc "更换故障端口" -p 300 -l 150 -h 2

# 查看维修历史
nas-cli maintenance list -d SW-01

# 查看本月成本
nas-cli cost
```

### 4. 生成报表
```bash
# 周报
nas-cli report -n 7

# 月报
nas-cli report -n 30

# 指定设备报表
nas-cli report -d SW-01 -n 30
```

### 5. 批量更新设备状态
```bash
# 设备维护开始
nas-cli device update SW-01 -s maintenance

# 维护完成
nas-cli device update SW-01 -s online
```

---

## AI Agent 集成示例

```bash
# 1. 检查系统状态
nas-cli stats
nas-cli device list

# 2. 执行备份
nas-cli backup run SW-01

# 3. 检查备份结果
nas-cli backup list -d SW-01 -n 1

# 4. 如果有错误，查看日志
nas-cli log search "SW-01" -l ERROR

# 5. 创建故障记录
nas-cli fault add -d SW-01 -s major -desc "备份失败"

# 6. 生成报表
nas-cli report -n 7
```

---

*详细文档：`README.md`*
