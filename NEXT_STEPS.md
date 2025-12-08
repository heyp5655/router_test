# 串口Boot模式修复 - 下一步工作计划

**日期**: 2025-12-03 18:30
**状态**: 串口Boot登录已修复成功 ✅

---

## ✅ 已完成

1. **串口Boot模式登录修复**
   - 问题：Python发送密码100%失败
   - 根本原因：`read_until()`等待检查会阻塞串口输入
   - 解决方案：固定延迟1秒 + 盲发密码
   - 文件：`utils/serial_client.py` 第446-474行
   - 测试：`test_single_serial_boot.py` 成功 ✅

2. **调试脚本清理**
   - 移动23个调试脚本到 `debug_scripts/` 目录
   - 保留核心测试脚本

---

## ⏳ 待完成：ID21用例修复

### 用例名称
**多设备反复升级稳定性测试（串口+Web混合）**

### 用例文件
`test_cases/stability/multi_device_firmware_upgrade_stability_test.py`

### 需要修改的内容

#### 1. 集成串口烧录功能

**当前问题**：
- 用例只使用Web升级
- 没有使用串口烧录功能

**修改方案**：
```python
# 在每次Web升级失败后，使用串口烧录恢复
def _upgrade_firmware(self, device_client, firmware_path, device_name, stats):
    """执行单次固件升级"""

    # 尝试Web升级
    try:
        success = device_client.upload_and_upgrade_firmware(firmware_path)
        if success:
            stats["success"] += 1
            return True
    except Exception as e:
        self.logger.error(f"{device_name} Web升级失败: {e}")

    # Web升级失败，使用串口烧录恢复
    self.logger.info(f"{device_name} Web升级失败，尝试串口烧录恢复...")

    try:
        # 获取对应的串口客户端
        serial_client = self._get_serial_client(device_name)

        # 进入Boot模式
        if serial_client.reboot_to_boot_mode():
            # 使用TFTP烧录固件
            if serial_client.burn_firmware_via_tftp(firmware_path):
                self.logger.info(f"{device_name} 串口烧录成功")
                stats["success"] += 1
                stats["serial_recovery"] += 1  # 新增统计
                return True

    except Exception as e:
        self.logger.error(f"{device_name} 串口烧录失败: {e}")

    # 两种方式都失败
    stats["failed"] += 1
    stats["failed_cycles"].append(cycle)
    return False
```

#### 2. 添加串口客户端管理

```python
class MultiDeviceFirmwareUpgradeStabilityTest(BaseTest):

    def setup(self):
        """初始化测试"""
        super().setup()

        # Web客户端（已有）
        self.device1_client = RouterClient(...)
        self.device2_client = RouterClient(...)

        # 新增：串口客户端
        from utils.serial_client import SerialClient
        self.device1_serial = SerialClient(port="COM7", baudrate=115200)
        self.device2_serial = SerialClient(port="COM8", baudrate=115200)

        # 打开串口
        self.device1_serial.open()
        self.device2_serial.open()

    def _get_serial_client(self, device_name):
        """根据设备名获取串口客户端"""
        if device_name == "设备1":
            return self.device1_serial
        elif device_name == "设备2":
            return self.device2_serial

    def cleanup(self):
        """清理资源"""
        # 关闭串口
        if hasattr(self, 'device1_serial'):
            self.device1_serial.close()
        if hasattr(self, 'device2_serial'):
            self.device2_serial.close()

        super().cleanup()
```

#### 3. SerialClient新增TFTP烧录方法

**文件**: `utils/serial_client.py`

**新增方法**:
```python
def burn_firmware_via_tftp(self, firmware_path: str) -> bool:
    """
    通过TFTP烧录固件（在Boot模式下）

    Args:
        firmware_path: 固件文件路径

    Returns:
        bool: 烧录成功返回True
    """
    # 1. 确认在Boot模式
    # 2. 配置TFTP参数
    # 3. 下载固件
    # 4. 烧录到Flash
    # 5. 重启验证
```

#### 4. 更新统计信息

```python
stats = {
    "total": 0,
    "success": 0,
    "failed": 0,
    "failed_cycles": [],
    "web_upgrades": 0,       # 新增
    "serial_recovery": 0,    # 新增：串口恢复次数
}
```

---

## 📝 具体实现步骤

1. **修改SerialClient** (utils/serial_client.py)
   - [ ] 新增 `burn_firmware_via_tftp()` 方法
   - [ ] 实现TFTP下载和烧录逻辑

2. **修改稳定性测试用例**
   - [ ] 添加串口客户端初始化
   - [ ] 修改 `_upgrade_firmware()` 集成串口恢复
   - [ ] 添加 `_get_serial_client()` 方法
   - [ ] 更新统计信息

3. **测试验证**
   - [ ] 测试Web升级成功流程
   - [ ] 测试Web升级失败 → 串口恢复流程
   - [ ] 测试完整1000次循环

---

## 🔑 关键点

1. **串口和Web并行**
   - 两个线程分别处理设备1和设备2
   - 每个线程独立的Web客户端和串口客户端
   - 串口烧录时需要加锁（TFTP服务器单线程）

2. **TFTP配置**
   - 服务器IP: 172.168.0.100
   - 设备IP: COM7→172.168.0.10, COM8→172.168.0.11
   - 固件文件名: 32.3.0.7.ext2

3. **容错机制**
   - Web升级失败 → 串口烧录
   - 串口烧录失败 → 记录并继续
   - 所有失败都记录到日志

---

## 📄 相关文件

- `utils/serial_client.py` - 串口客户端（已修复Boot登录）
- `test_cases/stability/multi_device_firmware_upgrade_stability_test.py` - 稳定性测试用例
- `test_single_serial_boot.py` - Boot登录测试（验证成功）
- `CLAUDE.md` - 项目文档（已更新修复记录）

---

**重启后从这里继续工作！**
