# DMVPN连接问题修复完整总结

**修复时间**: 2025-11-28
**问题**: 路由器无法连接到DMVPN服务器
**结果**: ✅ 成功修复并建立连接

---

## 🔍 问题诊断过程

### 1. 路由器日志显示
```
2025-11-28 09:24:57: racoon: phase1 negotiation failed due to time up
```
- Phase 1协商超时
- 路由器WAN IP: 172.168.0.214
- 不断重试但都失败

### 2. 服务器日志显示

**第一个错误**（已修复）：
```
Nov 28 17:35:29: [192.168.50.17] ERROR: exchange Identity Protection not allowed in any applicable rmconf
```

**问题原因**: 服务器配置只允许特定IP (172.168.0.214)连接，但还有其他路由器尝试连接
**解决方案**: 切换到 `anonymous` 模式，允许任意IP连接

**第二个错误**（已修复）：
```
Nov 28 17:53:42: ERROR: no suitable proposal found
```

**问题原因**: IPSec Phase 1参数不匹配
**解决方案**: 添加多个proposal支持不同的加密算法组合

**核心问题**（用户发现）：
**仅重启racoon服务不够，必须使用完整的DMVPN启动脚本！**

---

## 💡 核心发现

### 为什么必须用 dmvpn.sh？

**错误做法**：
```bash
systemctl restart racoon   # ❌ 只重启racoon守护进程
```

**正确做法**：
```bash
cd /home && sudo sh dmvpn.sh stop
cd /home && sudo sh dmvpn.sh start   # ✅ 完整启动DMVPN
```

### dmvpn.sh 做了什么？

```bash
#!/bin/sh

# 1. 配置GRE隧道
ip tunnel add gre1 mode gre local 192.168.50.48 key 123456 ttl 64
ip addr add 10.0.0.1/24 dev gre1
ip link set gre1 up multicast on

# 2. 加载IPsec策略（关键步骤！）
setkey -f /etc/ipsec-tools.conf

# 3. 启动Racoon
racoon -f /etc/racoon/racoon.conf

# 4. 启动OpenNHRP
opennhrp -d
```

### 关键：IPsec策略加载

`/etc/ipsec-tools.conf` 内容：
```bash
flush;
spdflush;

# 告诉内核：所有GRE流量必须用IPsec ESP加密
spdadd 0.0.0.0/0 0.0.0.0/0 gre -P out ipsec esp/transport//require;
spdadd 0.0.0.0/0 0.0.0.0/0 gre -P in  ipsec esp/transport//require;
```

**如果不执行 `setkey -f`，IPsec策略不会加载到内核，DMVPN无法工作！**

---

## ✅ 最终解决方案

### 1. 修改服务器Racoon配置

切换到 **anonymous模式**，支持多个proposal：

```bash
# /etc/racoon/racoon.conf

remote anonymous {
    exchange_mode main;
    my_identifier address;
    peers_identifier address;

    nat_traversal on;

    # 多个proposal支持不同的路由器配置
    proposal {
        encryption_algorithm aes 256;
        hash_algorithm sha256;
        authentication_method pre_shared_key;
        dh_group modp3072;
        lifetime time 10800 sec;
    }

    proposal {
        encryption_algorithm aes 192;
        hash_algorithm sha256;
        authentication_method pre_shared_key;
        dh_group modp3072;
        lifetime time 10800 sec;
    }

    # ... 更多proposal
}

sainfo anonymous {
    encryption_algorithm aes 256, aes 192, aes 128;
    authentication_algorithm hmac_sha2_256, hmac_sha1;
}
```

### 2. 使用完整的DMVPN重启流程

```bash
cd /home && sudo sh dmvpn.sh stop
cd /home && sudo sh dmvpn.sh start
```

### 3. 验证连接成功

**服务器日志**：
```
Nov 28 18:21:26: INFO: ISAKMP-SA established 192.168.50.48[500]-192.168.50.16[500]
Nov 28 18:21:27: INFO: IPsec-SA established: ESP/Transport (x2)
```

✅ **路由器 192.168.50.16 成功连接！**

---

## 🔧 工具更新

### 1. 修复脚本 (`scripts/fix_dmvpn_config.py`)

**之前**:
```python
run_ssh_command(ssh_client, "systemctl restart racoon")
```

**现在**:
```python
# Stop DMVPN
run_ssh_command(ssh_client, "cd /home && sh dmvpn.sh stop")
time.sleep(2)

# Start DMVPN
run_ssh_command(ssh_client, "cd /home && sh dmvpn.sh start")
time.sleep(3)
```

### 2. DMVPN配置工具GUI (`scripts/vpn_tools/dmvpn_config_gui.py`)

**更新内容**：
- ✅ `apply_config()` 方法：使用 dmvpn.sh 重启
- ✅ `restart_racoon()` 方法：使用 dmvpn.sh 重启
- ✅ 按钮文本："重启DMVPN服务"（原："重启Racoon服务"）
- ✅ 确认对话框：明确显示"重启DMVPN服务(dmvpn.sh)"

---

## 📊 连接建立流程

### 完整的DMVPN工作流程

```
┌──────────────────────────────────────────┐
│  1. 加载IPsec策略                        │
│     setkey -f /etc/ipsec-tools.conf      │
│     → 所有GRE流量需要ESP加密             │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│  2. 启动Racoon                           │
│     racoon -f /etc/racoon/racoon.conf    │
│     → IKE协商（Phase 1/2）               │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│  3. 创建GRE隧道                          │
│     ip tunnel add gre1 mode gre...       │
│     ip addr add 10.0.0.1/24 dev gre1     │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│  4. 启动OpenNHRP                         │
│     opennhrp -d                          │
│     → 动态路由协议                       │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│  ✅ DMVPN连接建立                        │
│     路由器 ←→ 服务器                     │
└──────────────────────────────────────────┘
```

### 连接验证

**服务器端**：
```bash
# 检查Racoon进程
ps aux | grep racoon

# 检查GRE隧道
ip addr show gre1

# 检查IPsec SA
setkey -D

# 查看日志
journalctl -u racoon -n 50 --no-pager
```

---

## 📝 关键知识点

### IPsec工作原理

1. **IKE (Internet Key Exchange)** - 由Racoon负责
   - Phase 1: 建立ISAKMP-SA（安全通道）
   - Phase 2: 协商IPsec-SA（加密参数）

2. **Setkey** - 加载策略到内核
   - SPD (Security Policy Database): 定义哪些流量需要加密
   - SAD (Security Association Database): 存储协商的密钥

3. **GRE隧道** - 承载DMVPN流量
   - 点对点隧道
   - 被IPsec ESP保护

### DMVPN三要素

```
DMVPN = GRE + IPsec + NHRP
        ↓      ↓       ↓
      隧道   加密   动态路由
```

---

## 🎯 经验教训

### 1. 系统服务管理的差异

| 方式 | 命令 | 适用场景 |
|------|------|----------|
| systemctl | `systemctl restart racoon` | 只重启单个服务 |
| init.d | `/etc/init.d/racoon restart` | 旧式服务管理 |
| **自定义脚本** | `dmvpn.sh start/stop` | **完整的服务栈启动** |

**关键**: 复杂的服务（如DMVPN）通常需要自定义启动脚本来协调多个组件。

### 2. 日志分析的重要性

通过对比路由器和服务器日志，找到了根本原因：
- 路由器：phase1 negotiation failed due to time up
- 服务器：exchange Identity Protection not allowed

**两边日志结合分析才能准确定位问题！**

### 3. 文档和注释的价值

`dmvpn.sh` 脚本清晰地展示了启动流程，这对于理解DMVPN工作原理至关重要。

---

## 🚀 后续建议

1. **标准化重启命令**
   - 所有DMVPN相关操作都使用 `dmvpn.sh`
   - 避免直接使用 `systemctl restart racoon`

2. **监控路由器连接**
   - 定期检查 `journalctl -u racoon`
   - 监控ISAKMP-SA和IPsec-SA建立情况

3. **配置备份**
   - 每次修改配置前自动备份
   - 保留最近10个版本

4. **文档更新**
   - 记录每个路由器的IPsec参数
   - 维护连接成功的配置组合

---

## 📚 参考文档

- `/home/dmvpn.sh` - DMVPN启动脚本
- `/etc/racoon/racoon.conf` - Racoon配置
- `/etc/ipsec-tools.conf` - IPsec策略配置
- `scripts/fix_dmvpn_config.py` - 自动修复脚本
- `scripts/vpn_tools/dmvpn_config_gui.py` - GUI配置工具

---

**修复完成时间**: 2025-11-28 18:30
**最终状态**: ✅ DMVPN连接成功建立
