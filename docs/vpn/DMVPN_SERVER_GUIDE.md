# DMVPN服务器和路由器配置指南

## 🎯 当前配置状态 (2025-11-26)

### 服务器信息
- **服务器IP**: 192.168.50.48
- **操作系统**: Ubuntu 16.04 LTS
- **登录用户**: yuxy
- **SSH可用用户**: root, yuxy
- **VPN服务**: racoon (ipsec-tools 0.8.2)
- **隧道网段**: 10.0.0.0/24
- **Hub隧道IP**: 10.0.0.1

### 路由器信息
- **路由器WAN IP**: 192.168.50.16
- **路由器GRE IP**: 10.0.0.3
- **配置界面**: Web管理

---

## ✅ 服务器端配置（已完成）

### 1. Racoon配置 `/etc/racoon/racoon.conf`

```
log notify;
path include "/etc/racoon/";
path pre_shared_key "/etc/racoon/psk.txt";

remote anonymous {
        exchange_mode main;
        lifetime time 10800 seconds;
        my_identifier address;
        dpd_delay 30;
        dpd_retry 3;
        dpd_maxfail 6;
        nat_traversal on;

        proposal {
                encryption_algorithm aes128;
                hash_algorithm sha1;
                dh_group modp768;
                authentication_method pre_shared_key;
        }
}

sainfo anonymous {
        lifetime time 3600 seconds;
        compression_algorithm deflate;
        encryption_algorithm 3des;
        authentication_algorithm hmac_sha1;
}
```

**关键配置说明：**
- **Phase 1 (IKE)**:
  - 加密算法: AES-128
  - 认证算法: SHA1
  - DH组: modp768 (Group 1)
  - 模式: Main
  - 生存时间: 10800秒
  - DPD: 30秒间隔, 3次重试, 6次失败断开

- **Phase 2 (IPSec SA)**:
  - 加密算法: 3DES
  - 认证算法: HMAC-SHA1
  - 生存时间: 3600秒
  - 压缩: deflate

### 2. PSK密钥配置 `/etc/racoon/psk.txt`

```
#IPv4/v6 addresses
192.168.40.207    123456
192.168.40.210    123456
192.168.40.237    123456
192.168.40.240    123456
192.168.40.241    123456
192.168.40.242    123456
192.168.50.16     123456    # ← 新添加的路由器
```

**PSK密钥**: `123456`
**已添加**: 路由器IP 192.168.50.16

### 3. Racoon服务状态

```bash
# 服务状态：运行中
● racoon.service - ipsec key exchange server
   Loaded: loaded (/lib/systemd/system/racoon.service; enabled)
   Active: active (running)

# 管理命令
sudo systemctl status racoon    # 查看状态
sudo systemctl restart racoon   # 重启服务
sudo tail -f /var/log/syslog | grep racoon  # 查看日志
```

### 4. GRE隧道配置（已完成永久化配置）

✅ **GRE隧道已配置并永久化**

#### 方法1：使用自动化脚本（推荐）

```bash
# 1. 将脚本上传到服务器
scp scripts/setup_gre_tunnel.sh yuxy@192.168.50.48:~/

# 2. SSH登录服务器
ssh yuxy@192.168.50.48

# 3. 运行脚本
sudo bash setup_gre_tunnel.sh
```

脚本会自动完成：
- ✓ 创建永久化配置文件 `/etc/network/interfaces.d/gre1`
- ✓ 立即创建并启动GRE隧道
- ✓ 验证隧道状态和连通性
- ✓ 系统重启后自动生效

#### 方法2：手动配置

**临时创建GRE隧道（重启后失效）：**
```bash
sudo ip tunnel add gre1 mode gre local 192.168.50.48 key 123456
sudo ip addr add 10.0.0.1/24 dev gre1
sudo ip link set gre1 up
```

**永久化配置（推荐）：**
```bash
# 创建配置文件
sudo nano /etc/network/interfaces.d/gre1

# 添加以下内容：
auto gre1
iface gre1 inet static
    address 10.0.0.1
    netmask 255.255.255.0
    pre-up ip tunnel add gre1 mode gre local 192.168.50.48 key 123456
    post-down ip tunnel del gre1

# 保存后启动隧道
sudo ifup gre1
```

#### GRE隧道管理命令

```bash
# 查看隧道状态
ip addr show gre1
ip tunnel show gre1

# 手动启动/停止
sudo ifup gre1
sudo ifdown gre1

# 重启隧道
sudo ifdown gre1 && sudo ifup gre1

# 查看路由
ip route | grep 10.0.0
```

---

## 🔧 路由器端配置（需要修改）

### 当前路由器配置（来自截图）

#### DMVPN基础设置
| 配置项 | 当前值 | 状态 |
|--------|--------|------|
| 启用 | ✓ | ✅ |
| Hub地址 | 192.168.50.48 | ✅ |
| 本地IP类型 | 接口获取 | ✅ |
| 接口 | WAN | ✅ |
| GRE HUB IP | 10.0.0.1 | ✅ |
| GRE本地IP | 10.0.0.3 | ✅ |
| GRE子网掩码 | 255.255.255.0 | ✅ |
| GRE密钥 | 123456 | ✅ |
| 协商模式 | Main | ✅ |
| **加密算法** | **DES** | ⚠️ **需要改** |

#### IPSec详细设置
| 配置项 | 当前值 | 状态 |
|--------|--------|------|
| **认证算法** | **MD5** | ⚠️ **需要改** |
| DH组 | MODP768-1 | ✅ |
| **PSK密钥** | **DMVPNsharedkey** | ⚠️ **需要改** |
| 本地ID类型 | Default | ✅ |
| IKE生存时间 | 10800 | ✅ |
| **SA算法** | **DES-MD5** | ⚠️ **需要改** |
| PFS组 | NULL | ✅ |
| 生存时间 | 3600 | ✅ |
| DPD间隔 | 30 | ✅ |
| DPD超时 | 150 | ✅ |
| NHRP保持时间 | 7200 | ✅ |

---

## 🎯 必须修改的4项配置

### 1. 加密算法（DMVPN设置页）
```
当前: DES
改为: AES-128 (或下拉框中的 AES128)
```

### 2. 认证算法（IPSec设置页）
```
当前: MD5
改为: SHA1 (或下拉框中的 SHA)
```

### 3. PSK密钥（IPSec设置页）
```
当前: DMVPNsharedkey
改为: 123456
```

### 4. SA算法（IPSec设置页）
```
当前: DES-MD5
改为: 3DES-SHA1 (或下拉框中的 3DES-SHA)
```

---

## 📊 配置对照表

### 服务器要求 vs 路由器当前配置

| 参数 | 服务器要求 | 路由器当前 | 是否匹配 |
|------|-----------|-----------|---------|
| Hub IP | 192.168.50.48 | 192.168.50.48 | ✅ |
| 协商模式 | Main | Main | ✅ |
| **加密算法** | **AES-128** | **DES** | ❌ |
| **认证算法** | **SHA1** | **MD5** | ❌ |
| DH组 | modp768 | MODP768-1 | ✅ |
| **PSK** | **123456** | **DMVPNsharedkey** | ❌ |
| IKE生存时间 | 10800s | 10800s | ✅ |
| **SA加密** | **3DES** | **DES** | ❌ |
| **SA认证** | **HMAC-SHA1** | **MD5** | ❌ |
| SA生存时间 | 3600s | 3600s | ✅ |
| DPD间隔 | 30s | 30s | ✅ |
| NAT穿透 | 开启 | (支持) | ✅ |

---

## 📝 修改步骤

### 步骤1：登录路由器
访问路由器Web管理界面

### 步骤2：进入DMVPN配置页
导航到 DMVPN 设置页面

### 步骤3：修改第一页参数
找到"加密算法"，改为：
```
AES-128 或 AES128
```

### 步骤4：向下滚动，修改IPSec参数
修改以下3项：

**认证算法:**
```
SHA1 或 SHA
```

**PSK密钥:**
```
123456
```

**SA算法:**
```
3DES-SHA1 或 3DES-SHA
```

### 步骤5：保存配置
点击"应用"或"保存"按钮

### 步骤6：重启DMVPN
重启DMVPN服务或整个路由器使配置生效

---

## ✅ 验证连接

### 1. 检查路由器DMVPN状态
- 状态应显示"已连接"或"Connected"
- GRE隧道应该已建立

### 2. 测试GRE隧道连通性
在路由器上执行：
```
ping 10.0.0.1
```
应该能ping通服务器的GRE IP

### 3. 查看服务器端日志
```bash
# 在服务器上查看连接日志
sudo tail -50 /var/log/syslog | grep racoon

# 查看IPSec SA状态
sudo setkey -D

# 应该看到类似输出：
# 192.168.50.48 192.168.50.16
#   esp mode=transport spi=...
#   E: 3des-cbc ...
#   A: hmac-sha1 ...
#   state=mature
```

### 4. 测试双向通信
**从服务器ping路由器:**
```bash
ping 10.0.0.3
```

**从路由器ping服务器:**
```
ping 10.0.0.1
```

---

## 🐛 故障排查

### 常见错误和解决方法

#### 1. 连接失败 - "authentication failed"
**原因**: PSK密钥不匹配
**解决**:
- 确认路由器PSK改为 `123456`
- 确认服务器 `/etc/racoon/psk.txt` 中有路由器IP条目
- 重启racoon: `sudo systemctl restart racoon`

#### 2. 连接失败 - "no proposal chosen"
**原因**: 加密算法不匹配
**解决**:
- 确认路由器加密算法改为 `AES-128`
- 确认路由器认证算法改为 `SHA1`
- 确认路由器SA算法改为 `3DES-SHA1`

#### 3. Phase 1成功但Phase 2失败
**原因**: SA参数不匹配
**解决**:
- 检查SA算法是否为 `3DES-SHA1`
- 检查PFS组是否为 `NULL`

#### 4. IPSec连接成功但GRE不通
**原因**: GRE配置问题
**解决**:
```bash
# 在服务器上检查GRE隧道
ip tunnel show
ip addr show | grep gre

# 如果没有GRE隧道，使用自动化脚本创建
cd ~
sudo bash setup_gre_tunnel.sh

# 或手动创建
sudo ip tunnel add gre1 mode gre local 192.168.50.48 key 123456
sudo ip addr add 10.0.0.1/24 dev gre1
sudo ip link set gre1 up
```

#### 5. 路由器能ping通服务器，但服务器不能ping通路由器 ⚠️
**现象**: 单向连通性问题
- ✓ 路由器可以 ping 10.0.0.1
- ✗ 服务器不能 ping 10.0.0.3

**原因分析**:
1. **服务器缺少GRE隧道配置**（最常见）
   - 路由器有GRE接口所以能主动发起ping
   - 服务器没有GRE接口无法回应或主动ping

2. **路由器防火墙阻止入站流量**
   - GRE协议(IP 47)被阻止
   - ICMP入站被阻止

3. **服务器路由表缺少路由**
   - 没有到10.0.0.0/24的路由条目

**解决步骤**:

**第一步：创建服务器GRE隧道（必须）**
```bash
# 使用自动化脚本（推荐）
sudo bash ~/setup_gre_tunnel.sh

# 验证隧道已创建
ip addr show gre1
# 应显示: inet 10.0.0.1/24 scope global gre1
```

**第二步：验证路由表**
```bash
ip route | grep 10.0.0
# 应显示: 10.0.0.0/24 dev gre1 proto kernel scope link src 10.0.0.1

# 如果没有，手动添加
sudo ip route add 10.0.0.0/24 dev gre1
```

**第三步：测试双向连通性**
```bash
# 从服务器ping路由器
ping -c 4 10.0.0.3

# 同时在路由器Web界面执行
ping -c 4 10.0.0.1
```

**第四步：如果仍不通，检查路由器防火墙**
- 在路由器Web界面检查防火墙规则
- 确保允许GRE协议(IP Protocol 47)
- 确保允许ICMP入站

**第五步：检查服务器防火墙（可选）**
```bash
# 查看防火墙状态
sudo ufw status

# 临时测试：禁用防火墙
sudo ufw disable
ping -c 4 10.0.0.3
sudo ufw enable  # 测试完记得开启

# 或添加GRE规则
sudo iptables -A INPUT -p 47 -j ACCEPT
sudo iptables -A OUTPUT -p 47 -j ACCEPT
```

---

## 📋 服务器管理命令

### 查看服务状态
```bash
sudo systemctl status racoon
ps aux | grep racoon
```

### 查看日志
```bash
# 实时查看
sudo tail -f /var/log/syslog | grep racoon

# 查看最近日志
sudo tail -100 /var/log/syslog | grep racoon
```

### 查看IPSec状态
```bash
# 查看SA
sudo setkey -D

# 查看SPD策略
sudo setkey -DP
```

### 重启服务
```bash
sudo systemctl restart racoon
```

### 编辑配置
```bash
# 编辑racoon配置
sudo nano /etc/racoon/racoon.conf

# 编辑PSK
sudo nano /etc/racoon/psk.txt

# 保存: Ctrl+O, Enter, Ctrl+X
```

---

## 🔑 关键信息速查

### 网络信息
- 服务器物理IP: `192.168.50.48`
- 路由器物理IP: `192.168.50.16`
- 服务器GRE IP: `10.0.0.1`
- 路由器GRE IP: `10.0.0.3`
- GRE子网: `10.0.0.0/24`

### 密钥信息
- PSK密钥: `123456`
- GRE密钥: `123456`

### 加密参数
- Phase 1 加密: `AES-128`
- Phase 1 认证: `SHA1`
- Phase 1 DH组: `modp768` (Group 1)
- Phase 2 加密: `3DES`
- Phase 2 认证: `HMAC-SHA1`

### 端口信息
- IKE: UDP 500
- NAT-T: UDP 4500
- ESP: IP Protocol 50
- GRE: IP Protocol 47

---

## 📞 下一步操作

### 服务器端（已完成）
1. ✅ Racoon IPSec服务已配置
2. ✅ PSK密钥已添加（192.168.50.16 -> 123456）
3. ✅ GRE隧道永久化配置已完成
4. ✅ 自动化脚本已创建（scripts/setup_gre_tunnel.sh）

### 路由器端（待确认）
1. ⏳ 等待路由器修改配置（4项加密参数）
2. ⏳ 测试IPSec连接
3. ⏳ 验证GRE隧道双向通信
4. ⏳ 解决单向连通性问题（如果存在）

### 故障排查清单
- [ ] 服务器GRE隧道是否已创建？（`ip addr show gre1`）
- [ ] 路由器加密参数是否已修改？（AES-128, SHA1, 3DES-SHA1）
- [ ] 路由器PSK密钥是否已改为 `123456`？
- [ ] 路由器能否ping通 10.0.0.1？
- [ ] 服务器能否ping通 10.0.0.3？
- [ ] 路由器防火墙是否允许GRE和ICMP入站？

---

**文档版本**: 3.0
**最后更新**: 2025-11-26 17:00
**配置状态**: 服务器完成(含GRE永久化)，等待路由器修改测试
**新增内容**:
- ✅ GRE隧道永久化配置
- ✅ 自动化配置脚本（setup_gre_tunnel.sh）
- ✅ 单向连通性问题排查指南
**维护人员**: Claude AI Assistant
