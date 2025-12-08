# DMVPN配置最佳实践指南

**版本**: v2.3
**更新时间**: 2025-11-28
**重要性**: ⭐⭐⭐⭐⭐

---

## 🎯 核心要点（必读！）

### 关键规则 #1：必须使用 dmvpn.sh 重启

```bash
# ✅ 正确做法
cd /home && sudo sh dmvpn.sh stop
cd /home && sudo sh dmvpn.sh start

# ❌ 错误做法
systemctl restart racoon  # 这不够！缺少IPsec策略加载
```

**原因**：DMVPN需要4个组件协同工作：
1. **setkey** - 加载IPsec策略（告诉内核GRE流量需要加密）
2. **racoon** - IKE协商
3. **GRE隧道** - 创建gre1接口
4. **OpenNHRP** - 动态路由

**缺少setkey的后果**：
```
没有IPsec策略 → GRE流量不加密 → 路由器连接失败
```

### 关键规则 #2：优先使用GUI工具

```
双击 "启动DMVPN配置工具.bat" （推荐）
```

GUI工具已经内置了正确的重启逻辑和验证功能。

---

## 📋 修改配置后的标准流程

### 方法1: 使用DMVPN配置工具GUI（推荐）⭐

**步骤**：

1. **启动工具**
   ```
   双击 "启动DMVPN配置工具.bat"
   ```

2. **修改配置参数**
   - SSH连接信息
   - GRE隧道配置
   - IPsec Phase 1参数
   - IPsec Phase 2参数

3. **生成并预览配置**
   - 点击 **"1. 生成并预览配置"**
   - 仔细检查生成的Racoon配置
   - 确认无误

4. **应用到服务器**
   - 点击 **"2. 应用到服务器"**
   - 在确认对话框中点击"是"
   - **工具会自动使用dmvpn.sh重启！**

5. **查看验证结果**
   - 查看日志输出
   - 确认以下4项都显示 ✓：
     - ✓ Racoon进程运行正常
     - ✓ GRE隧道配置正确
     - ✓ OpenNHRP运行正常
     - ✓ **IPsec策略已加载** ⭐（最关键！）

**自动验证功能**：

GUI工具会自动检查：
```
[检查] Racoon进程
[检查] GRE隧道 (10.0.0.1)
[检查] OpenNHRP
[检查] IPsec策略（GRE流量加密）⭐
```

如果看到：
```
✓ IPsec策略已加载（GRE流量加密）
```
说明配置成功！

---

### 方法2: 使用命令行（适合脚本化）

**1. 修改配置文件**
```bash
# 编辑 /etc/racoon/racoon.conf
# 修改需要的参数
```

**2. 使用dmvpn.sh重启**
```bash
ssh yuxy@192.168.50.48
cd /home
sudo sh dmvpn.sh stop
sleep 2
sudo sh dmvpn.sh start
```

**3. 验证配置**
```bash
# 检查Racoon
ps aux | grep racoon

# 检查GRE
ip addr show gre1

# 检查OpenNHRP
ps aux | grep opennhrp

# ⭐最关键：检查IPsec策略
setkey -DP | grep gre

# 应该看到：
# 0.0.0.0/0 0.0.0.0/0 gre -P out ipsec esp/transport//require
# 0.0.0.0/0 0.0.0.0/0 gre -P in  ipsec esp/transport//require
```

---

### 方法3: 使用诊断脚本（快速检查）

```bash
python scripts/diagnose_dmvpn.py
```

**输出示例**：
```
======================================================================
DMVPN服务器诊断工具 v1.0
======================================================================

[1/7] 连接到服务器 192.168.50.48...
  [OK] SSH连接成功

[2/7] 检查Racoon进程...
  [OK] Racoon进程运行正常

[3/7] 检查GRE隧道...
  [OK] GRE隧道已创建并运行

[4/7] 检查OpenNHRP...
  [OK] OpenNHRP运行正常

[5/7] 检查IPsec策略...
  [OK] IPsec策略已加载
    GRE流量将通过ESP加密

[6/7] 检查Racoon配置...
  [OK] 使用anonymous模式（允许任意路由器IP）

[7/7] 检查已连接的路由器...
  已发现的路由器:
    10.0.0.6 lladdr 192.168.50.16 STALE
```

---

## 🛠️ 常见问题和解决方案

### 问题1: 路由器显示"连接超时"

**症状**：
```
路由器日志: phase1 negotiation failed due to time up
```

**可能原因**：
1. 服务器只允许特定IP（不是anonymous模式）
2. IPsec参数不匹配
3. **IPsec策略未加载** ⭐

**解决方案**：

**第1步**：检查IPsec策略
```bash
ssh yuxy@192.168.50.48 "setkey -DP | grep gre"
```

如果没有输出或看不到 `esp/transport`，说明策略未加载！

**第2步**：使用dmvpn.sh重启
```bash
cd /home && sudo sh dmvpn.sh stop
cd /home && sudo sh dmvpn.sh start
```

**第3步**：再次检查
```bash
setkey -DP | grep gre
```

应该看到：
```
0.0.0.0/0 0.0.0.0/0 gre -P out ipsec esp/transport//require;
0.0.0.0/0 0.0.0.0/0 gre -P in  ipsec esp/transport//require;
```

---

### 问题2: "no suitable proposal found"

**症状**：
```
服务器日志: ERROR: no suitable proposal found
```

**原因**：路由器和服务器的IPsec参数不匹配

**解决方案**：

**选项A**：修改服务器配置支持多个proposal（推荐）

使用GUI工具，服务器会自动支持多种参数组合：
- AES256/192/128
- SHA256/SHA1
- modp3072/modp4096/modp2048

**选项B**：修改路由器配置匹配服务器

确保路由器配置与服务器的任一proposal匹配。

---

### 问题3: "Identity Protection not allowed"

**症状**：
```
服务器日志: exchange Identity Protection not allowed in any applicable rmconf
```

**原因**：服务器配置只允许特定IP，拒绝了其他路由器

**解决方案**：

切换到anonymous模式：

**使用GUI**：
1. 勾选 "允许任意IP"
2. 生成并预览配置
3. 应用到服务器

**手动修改**：
```bash
# /etc/racoon/racoon.conf

# 将：
remote 172.168.0.214 { ... }

# 改为：
remote anonymous { ... }
```

然后使用dmvpn.sh重启。

---

### 问题4: NHRP注册超时

**症状**：
```
路由器日志: Failed to register to 10.0.0.1: timeout (65535)
```

**如果第一次失败，第二次成功**：
- 这是正常的，服务刚启动时组件未就绪

**如果一直失败**：
1. 检查OpenNHRP进程
   ```bash
   ps aux | grep opennhrp
   ```

2. 检查防火墙（UDP 4500/500）
   ```bash
   iptables -L -n | grep -E "500|4500"
   ```

---

## 🔄 版本升级指南

如果您之前使用的是旧版本的配置工具或脚本：

### 升级步骤

1. **更新代码**
   ```bash
   git pull
   ```

2. **使用新的GUI工具**
   ```
   双击 "启动DMVPN配置工具.bat"
   ```

3. **重新生成配置**
   - 按现有参数填写
   - 生成并预览
   - 应用到服务器

4. **验证**
   ```bash
   python scripts/diagnose_dmvpn.py
   ```

---

## ✅ 快速检查清单

在应用配置后，确认以下几点：

- [ ] Racoon进程运行中 (`ps aux | grep racoon`)
- [ ] GRE隧道UP (`ip addr show gre1`)
- [ ] OpenNHRP运行中 (`ps aux | grep opennhrp`)
- [ ] **IPsec策略已加载** (`setkey -DP | grep gre`) ⭐
- [ ] 路由器能ping通服务器GRE IP (10.0.0.1)
- [ ] 服务器能ping通路由器GRE IP (10.0.0.x)

---

## 📚 相关文档

- `docs/vpn/DMVPN连接问题修复总结.md` - 完整的问题诊断和修复记录
- `docs/vpn/DMVPN配置工具v2.2更新说明.md` - GUI工具功能说明
- `scripts/diagnose_dmvpn.py` - 自动诊断脚本
- `/home/dmvpn.sh` - 服务器DMVPN启动脚本

---

## 🆘 寻求帮助

如果遇到问题：

1. **运行诊断脚本**
   ```bash
   python scripts/diagnose_dmvpn.py
   ```

2. **查看日志**
   ```bash
   # 服务器日志
   journalctl -u racoon -n 100 --no-pager

   # 路由器日志
   tail -f /etc/urlog/vpn.log
   ```

3. **提供信息**
   - 诊断脚本输出
   - 服务器和路由器日志
   - 配置文件内容

---

**最后更新**: 2025-11-28
**维护者**: ROUTER_TEST项目组
