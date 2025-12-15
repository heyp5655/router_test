# TFTP服务器配置指南

## 目录
- [概述](#概述)
- [为什么需要TFTP服务器](#为什么需要tftp服务器)
- [快速开始](#快速开始)
- [详细配置步骤](#详细配置步骤)
- [故障排查](#故障排查)

---

## 概述

本文档指导您配置TFTP服务器，用于路由器固件烧录测试。

**测试场景**: 多设备固定在两个版本之间反复升级稳定性测试（串口烧录 + Web升级）

**固件烧录流程**:
1. **串口烧录旧版本** (32.3.0.7) ← 需要TFTP服务器
2. **Web升级新版本** (32.3.0.9)
3. 循环1000次

---

## 为什么需要TFTP服务器

路由器的Boot模式通过**TFTP协议**下载固件文件到内存，然后写入Flash。

**TFTP协议特点**:
- 简单、轻量级的文件传输协议
- 使用UDP协议，端口69
- 适用于嵌入式设备的固件更新
- 不需要身份认证（局域网内使用）

**烧录过程**:
```
路由器Boot模式 ──TFTP下载──> PC TFTP服务器
                                ↓
                          固件文件(32.3.0.7.ext2)
```

---

## 快速开始

### 1. 检查配置

双击运行：`检查TFTP配置.bat`

或命令行：
```bash
python scripts/tftp_server.py --check
```

### 2. 下载并安装Tftpd64

**推荐软件**: Tftpd64（免费、简单易用）

**下载地址**:
- 官方网站: https://pjo2.github.io/tftpd64/
- 备用地址: http://tftpd32.jounin.net/tftpd32_download.html

**选择版本**:
- Windows 64位: `Tftpd64-4.xx-setup.exe`
- Windows 32位: `Tftpd32-4.xx-setup.exe`

**安装步骤**:
1. 双击安装包
2. 选择安装路径（建议: `C:\Program Files\Tftpd64\`）
3. 全部默认选项，点击"Next"直到完成
4. 勾选"Launch Tftpd64"，启动软件

### 3. 配置PC网卡

TFTP服务器需要配置静态IP。

**必需配置**:
- **IP地址**: `192.168.3.100` ← 重要！
- **子网掩码**: `255.255.255.0`
- **默认网关**: (可以留空)

**配置步骤**:

#### 方法1：通过"网络和共享中心"（推荐）
1. 按 `Win + R`，输入 `ncpa.cpl`，回车
2. 找到连接到路由器的网卡（有线网卡）
3. 右键 → 属性
4. 双击"Internet协议版本4 (TCP/IPv4)"
5. 选择"使用下面的IP地址"
6. 填写：
   - IP地址: `192.168.3.100`
   - 子网掩码: `255.255.255.0`
7. 点击"确定" → "确定"

#### 方法2：通过命令行（快速）
以管理员身份运行命令提示符：
```cmd
netsh interface ip set address name="以太网" static 192.168.3.100 255.255.255.0
```

⚠️ **注意**: 将"以太网"替换为实际的网卡名称

**验证配置**:
```cmd
ipconfig
```
查找输出中是否有 `192.168.3.100`

### 4. 准备固件文件

将旧版本固件文件放到目录：
```
E:\GIT\ROUTER_TEST\docs\upload\old\
```

**当前已检测到的固件**:
- `32.3.0.7.ext2` ✅

**支持的固件格式**:
- `.ext2` (推荐)
- `.bin`
- `.img`
- `.tar` / `.tar.gz`

### 5. 启动Tftpd64

双击运行：`启动TFTP服务器.bat`

或手动启动：
1. 打开Tftpd64软件
2. 在主界面配置：
   - **Current Directory**: 点击右侧的"Browse"按钮，选择
     ```
     E:\GIT\ROUTER_TEST\docs\upload\old
     ```
   - **Server interfaces**: 从下拉列表中选择 `192.168.3.100`

3. 切换到"TFTP"标签页（底部）
4. 点击"Settings"按钮（右上角）
5. 在"TFTP"标签页中配置：
   - **Base Directory**:
     ```
     E:\GIT\ROUTER_TEST\docs\upload\old
     ```
   - **TFTP Security**: 选择 `None`
   - 勾选 `Show Progress bar`（显示进度条）
6. 点击"OK"保存设置

**验证服务器运行**:
- Tftpd64日志窗口应该显示: `TFTP server started`
- 如果有错误提示，检查：
  - Windows防火墙是否允许Tftpd64（UDP 69端口）
  - 是否有其他程序占用UDP 69端口

### 6. 运行测试用例

现在可以运行稳定性测试用例了：
```bash
python -m test_cases.stability.multi_device_firmware_upgrade_stability_test
```

或通过Web界面：
```
http://localhost:5000
选择：稳定性用例 → 多设备固定在两个版本之间反复升级稳定性测试
```

---

## 详细配置步骤

### 串口连接配置

**设备配置**:
| 设备 | COM口 | Bridge IP | 用途 |
|------|-------|-----------|------|
| 设备1 | COM7 | 192.168.3.7 | 烧录+测试 |
| 设备2 | COM8 | 192.168.3.8 | 烧录+测试 |

**网络拓扑**:
```
PC (192.168.3.100) ──TFTP──┬──> 设备1 (192.168.3.7)
                           └──> 设备2 (192.168.3.8)
```

### Tftpd64高级配置

#### 1. TFTP标签页设置

**Settings → TFTP**:
- **TFTP Port**: `69` (默认，不要修改)
- **TFTP Timeout**: `5` 秒
- **TFTP Max Retries**: `6` 次
- **TFTP Security**: `None` ← 重要！允许所有连接
- **PXE Compatibility**: 不勾选
- **Show Progress bar**: ✅ 勾选（方便监控）

#### 2. DHCP标签页设置（可选）

如果不使用DHCP功能，可以禁用：
- 取消勾选"DHCP server"

#### 3. 防火墙配置

**Windows防火墙规则**:
```
协议: UDP
端口: 69
方向: 入站
操作: 允许
```

**快速添加规则**（以管理员身份运行）:
```cmd
netsh advfirewall firewall add rule name="TFTP Server" dir=in action=allow protocol=UDP localport=69
```

#### 4. 日志监控

**Tftpd64日志说明**:
| 日志内容 | 含义 |
|---------|------|
| `TFTP server started` | 服务器启动成功 |
| `Connection received from 192.168.3.7` | 设备连接 |
| `Read request for file "32.3.0.7.ext2"` | 设备请求文件 |
| `Sent 12345 bytes in 0:00:30` | 传输完成 |
| `Error code 1 : File not found` | 文件不存在 ❌ |

---

## 故障排查

### 问题1：Tftpd64启动失败

**现象**: 双击Tftpd64.exe无反应，或报错"无法启动"

**可能原因**:
1. UDP 69端口被占用
2. 权限不足

**解决方案**:

1. **检查端口占用**:
   ```cmd
   netstat -ano | findstr :69
   ```
   如果有输出，说明端口被占用。

   **关闭占用进程**:
   ```cmd
   taskkill /F /PID <进程ID>
   ```

2. **以管理员身份运行**:
   - 右键Tftpd64.exe → "以管理员身份运行"

### 问题2：设备无法连接TFTP服务器

**现象**: 路由器Boot模式显示 `TFTP: Timeout`

**可能原因**:
1. 网卡IP配置错误
2. 路由器和PC不在同一网段
3. 网络不通
4. Tftpd64未启动或配置错误

**解决步骤**:

1. **验证PC网卡IP**:
   ```cmd
   ipconfig
   ```
   确保有 `192.168.3.100`

2. **Ping测试**:

   从PC ping路由器：
   ```cmd
   ping 192.168.3.7
   ping 192.168.3.8
   ```

   应该能ping通。如果不通：
   - 检查网线是否连接
   - 检查路由器Bridge IP是否配置正确
   - 检查防火墙是否阻止ICMP

3. **检查Tftpd64配置**:
   - Server interfaces: 确认选择了 `192.168.3.100`
   - Current Directory: 确认路径正确
   - 日志窗口: 确认服务器已启动

4. **关闭防火墙测试**（临时）:
   ```cmd
   netsh advfirewall set allprofiles state off
   ```

   测试成功后记得重新开启：
   ```cmd
   netsh advfirewall set allprofiles state on
   ```

### 问题3：文件传输中断

**现象**: Tftpd64日志显示 `Timeout` 或传输到一半停止

**可能原因**:
1. 网络不稳定
2. 固件文件损坏
3. 路由器Flash写入失败

**解决方案**:

1. **检查网线连接**:
   - 更换网线
   - 检查网卡是否工作正常

2. **重新下载固件**:
   - 固件文件可能损坏
   - 检查文件大小和MD5

3. **增加超时时间**:
   Tftpd64 → Settings → TFTP →
   - TFTP Timeout: `10` 秒
   - TFTP Max Retries: `10` 次

### 问题4：固件文件找不到

**现象**: Tftpd64日志 `Error code 1 : File not found`

**可能原因**:
1. 固件文件不在TFTP根目录
2. 文件名不匹配

**解决方案**:

1. **确认文件位置**:
   ```
   E:\GIT\ROUTER_TEST\docs\upload\old\32.3.0.7.ext2
   ```

   文件必须直接在目录下，不能在子文件夹中。

2. **确认文件名**:
   - 串口烧录脚本中配置的文件名: `32.3.0.7.ext2`
   - 实际文件名必须完全匹配（区分大小写）

3. **刷新Tftpd64配置**:
   - 重新选择Current Directory
   - 重启Tftpd64软件

### 问题5：自动检测固件失败

**现象**: 脚本提示"⚠️ 固件文件检测失败，使用默认值"

**可能原因**:
1. 固件目录路径错误
2. 固件文件扩展名不支持

**解决方案**:

1. **检查目录路径**:
   - 确认目录存在: `E:\GIT\ROUTER_TEST\docs\upload\old`
   - 路径分隔符使用反斜杠 `\`

2. **检查文件扩展名**:
   支持的扩展名: `.ext2`, `.bin`, `.img`, `.tar`, `.tar.gz`

   如果是其他扩展名，手动指定：
   ```python
   serial_client = SerialClient(
       "COM7",
       firmware_name="your_firmware.xxx"
   )
   ```

---

## 附录

### A. TFTP协议基础

**TFTP vs FTP**:
| 特性 | TFTP | FTP |
|------|------|-----|
| 协议 | UDP | TCP |
| 端口 | 69 | 20/21 |
| 认证 | 无 | 有 |
| 速度 | 较慢 | 较快 |
| 可靠性 | 较低 | 高 |
| 用途 | 嵌入式设备 | 通用文件传输 |

**TFTP适用场景**:
- 路由器、交换机固件更新
- 网络设备配置备份
- PXE网络启动
- 嵌入式系统开发

### B. Tftpd64替代方案

如果不想使用Tftpd64，可以考虑：

1. **tftpy**（Python库）
   ```bash
   pip install tftpy
   ```

2. **Solarwinds TFTP Server**（企业级）
   - 下载: https://www.solarwinds.com/free-tools/free-tftp-server

3. **Windows内置TFTP服务器**（不推荐，配置复杂）

### C. 完整配置检查清单

在开始测试前，确认以下项目：

- [ ] Tftpd64已安装并启动
- [ ] PC网卡IP配置为 `192.168.3.100`
- [ ] 固件文件在目录 `E:\GIT\ROUTER_TEST\docs\upload\old\`
- [ ] 固件文件名正确（如 `32.3.0.7.ext2`）
- [ ] Tftpd64的Current Directory配置正确
- [ ] Tftpd64的Server interfaces选择正确
- [ ] Windows防火墙允许UDP 69端口
- [ ] 串口COM7和COM8连接正常
- [ ] 路由器设备可以ping通PC

---

## 技术支持

如遇到问题，请：
1. 运行 `python scripts/tftp_server.py --check` 检查配置
2. 查看Tftpd64日志窗口的错误信息
3. 参考本文档"故障排查"章节
4. 查看串口日志文件（`logs/serial/COMx_*.log`）

---

**最后更新**: 2025-12-09
