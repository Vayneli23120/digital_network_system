# 编程任务：修复 napalm_service.py 中硬编码的厂商驱动映射

## 任务背景

项目已完成 Phase 2 重构，建立了统一设备驱动注册表 `DriverRegistry`。
但 `app/features/deploy/napalm_service.py` 中仍有 **2 处** 独立的硬编码 `vendor_driver_map` 字典，
未接入注册表，与其他部署路径行为不一致。

本任务将这 2 处替换为调用 `DriverRegistry`，消除技术债 TD-008。

---

## 任务范围

**只修改一个文件**：`app/features/deploy/napalm_service.py`

**改动数量**：2 处替换，逻辑相同，仅所在方法不同。

---

## 前置知识

`DriverRegistry` 的用法：

```python
from app.features.devices.drivers.registry import DriverRegistry

driver_class = DriverRegistry.get(vendor)   # 传入厂商字符串，返回驱动类
driver_name = driver_class.NAPALM_DRIVER    # 获取 NAPALM driver 名称（str 或 None）
```

`NAPALM_DRIVER` 为 `None` 时，表示该厂商不支持 NAPALM（如 Aruba、H3C、Fortinet），
此时应回退到默认值 `'ios'`，等同于旧逻辑的 `.get(vendor, 'ios')`。

等价逻辑：
```python
driver_name = driver_class.NAPALM_DRIVER or 'ios'
```

---

## 修改 1：`NapalmDeployService.connect_device` 方法

**文件**：`app/features/deploy/napalm_service.py`

**定位**：搜索字符串 `vendor_driver_map = {` 第一次出现处（约第 88 行）。

### 替换前（旧代码）

```python
        vendor = device.get('vendor', 'cisco').lower()

        vendor_driver_map = {
            'cisco': 'ios',           # Cisco IOS/IOS-XE 设备
            'juniper': 'junos',       # Juniper 设备
            'huawei': 'huawei',       # 华为设备
            'h3c': 'huawei',          # H3C 设备
            'arista': 'eos',          # Arista 设备
        }
        driver_name = vendor_driver_map.get(vendor, 'ios')
```

### 替换后（新代码）

```python
        vendor = device.get('vendor', 'cisco').lower()

        from app.features.devices.drivers.registry import DriverRegistry
        driver_class = DriverRegistry.get(vendor)
        driver_name = driver_class.NAPALM_DRIVER or 'ios'
```

---

## 修改 2：`NapalmStreamService._connect_device` 方法

**文件**：`app/features/deploy/napalm_service.py`

**定位**：搜索字符串 `vendor_driver_map = {` 第二次出现处（约第 733 行）。

### 替换前（旧代码）

```python
        vendor = device.get('vendor', 'cisco').lower()

        vendor_driver_map = {
            'cisco': 'ios',
            'juniper': 'junos',
            'huawei': 'huawei',
            'h3c': 'huawei',
            'arista': 'eos',
        }
        driver_name = vendor_driver_map.get(vendor, 'ios')
```

### 替换后（新代码）

```python
        vendor = device.get('vendor', 'cisco').lower()

        from app.features.devices.drivers.registry import DriverRegistry
        driver_class = DriverRegistry.get(vendor)
        driver_name = driver_class.NAPALM_DRIVER or 'ios'
```

---

## 验收标准

完成修改后，执行以下检查：

### 1. 文件中不再存在硬编码映射

在 `app/features/deploy/napalm_service.py` 全文中搜索 `vendor_driver_map`，
**结果必须为 0 条匹配**。

### 2. DriverRegistry 被正确导入

在该文件中搜索 `DriverRegistry`，**必须有至少 2 条匹配**（两个方法各一处）。

### 3. 运行现有测试

```bash
python -m pytest tests/test_deploy_service.py tests/test_vendor_adapter.py -v
```

所有测试必须通过，不得引入新的失败。

### 4. 语法检查

```bash
python -m py_compile app/features/deploy/napalm_service.py
```

无报错输出即通过。

---

## 注意事项

- **不要修改** `napalm_service.py` 中的其他任何代码，包括注释、日志、连接参数等。
- **不要修改** `DriverRegistry` 或任何 `drivers/` 目录下的文件。
- `from app.features.devices.drivers.registry import DriverRegistry` 使用局部导入（写在方法体内）即可，无需移至文件顶部，保持与当前代码风格一致。
- 两处修改逻辑完全相同，只是所在方法不同（`connect_device` 和 `_connect_device`）。

---

## 完成后确认

修改完成后，在回复中确认：

1. `vendor_driver_map` 在文件中出现次数（期望：0）
2. `DriverRegistry` 在文件中出现次数（期望：≥2）
3. 测试运行结果（通过/失败条数）
