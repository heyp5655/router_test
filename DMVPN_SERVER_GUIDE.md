# DMVPN服务器使用指南

## 服务器信息

- **服务器IP**: 192.168.50.48
- **操作系统**: Ubuntu 16.04 LTS
- **登录用户**: root
- **登录密码**: milesight123
- **隧道网段**: 10.0.0.0/24
- **Hub隧道IP**: 10.0.0.1

## 一、服务器架构

### 使用的技术栈
- **IPsec IKE守护进程**: racoon (ipsec-tools 0.8.2)
- **加密协议**: IPsec ESP (transport模式)
- **隧道协议**: GRE (Generic Routing Encapsulation)
- **密钥交换**: IKE v1 (Main模式)

### 关键组件
```
┌─────────────────────────────────────┐
│   路由器 (Spoke)                     │
│   192.168.50.16                      │
│   隧道IP: 10.0.0.2                   │
└──────────────┬──────────────────────┘
               │ IPsec ESP + GRE
               │ (加密的GRE隧道)
┌──────────────▼──────────────────────┐
│   DMVPN Hub服务器                    │
│   192.168.50.48                      │
│   隧道IP: 10.0.0.1                   │
│                                       │
│   - racoon (IKE协商)                 │
│   - setkey (安全策略)                │
│   - GRE隧道接口                      │
└───────────────────────────────────────┘
```

## 二、服务管理

### 1. 启动服务

```bash
# SSH登录服务器
ssh root@192.168.50.48

# 启动racoon服务
systemctl start racoon

# 查看服务状态
systemctl status racoon

# 设置开机自启动
systemctl enable racoon
```

### 2. 停止服务

```bash
# 停止racoon服务
systemctl stop racoon

# 查看服务状态
systemctl status racoon
```

### 3. 重启服务

```bash
# 重启racoon服务
systemctl restart racoon

# 重新加载配置（不中断连接）
systemctl reload racoon
```

## 三、配置文件说明

### 1. racoon配置文件: `/etc/racoon/racoon.conf`

```bash
# 查看当前配置
cat /etc/racoon/racoon.conf

# 编辑配置
vim /etc/racoon/racoon.conf
```

**当前配置内容：**
```
path pre_shared_key "/etc/racoon/psk.txt";
log notify;

listen {
    isakmp 192.168.50.48 [500];
    isakmp_natt 192.168.50.48 [4500];
}

remote anonymous {
    exchange_mode main;
    passive on;
    generate_policy on;
    nat_traversal on;
    dpd_delay 30;

    proposal {
        encryption_algorithm des;
        hash_algorithm md5;
        authentication_method pre_shared_key;
        dh_group 1;
    }
}

sainfo anonymous {
    encryption_algorithm des;
    authentication_algorithm hmac_md5;
    compression_algorithm deflate;
    lifetime time 3600 sec;
}
```

**配置说明：**
- `exchange_mode main`: 使用主模式进行IKE协商
- `passive on`: Hub模式，被动接受连接
- `encryption_algorithm des`: DES加密（匹配路由器配置）
- `hash_algorithm md5`: MD5哈希算法
- `dh_group 1`: MODP768 Diffie-Hellman组
- **无PFS组**: 匹配路由器的NULL PFS配置

### 2. PSK密钥文件: `/etc/racoon/psk.txt`

```bash
# 查看PSK配置
cat /etc/racoon/psk.txt

# 编辑PSK（修改后需重启racoon）
vim /etc/racoon/psk.txt
```

**当前配置：**
```
192.168.50.16   DMVPNsharedkey123
*               DMVPNsharedkey123
```

**格式说明：**
- `192.168.50.16 DMVPNsharedkey123`: 为特定路由器IP配置PSK
- `* DMVPNsharedkey123`: 通配符，接受任何IP使用此PSK

**修改PSK后：**
```bash
# 1. 修改文件权限
chmod 600 /etc/racoon/psk.txt

# 2. 重启racoon
systemctl restart racoon
```

### 3. 安全策略配置: `/etc/ipsec-tools.conf`

```bash
# 查看当前策略
cat /etc/ipsec-tools.conf

# 手动应用策略
setkey -F           # 清空SA
setkey -FP          # 清空SPD
setkey -f /etc/ipsec-tools.conf  # 应用新策略
```

**当前配置：**
```bash
#!/usr/sbin/setkey -f

flush;
spdflush;

# 出站GRE流量需要IPsec保护
spdadd 192.168.50.48 192.168.50.16 gre -P out ipsec esp/transport//require;

# 入站GRE流量需要IPsec保护
spdadd 192.168.50.16 192.168.50.48 gre -P in ipsec esp/transport//require;

# 允许IKE流量
spdadd 192.168.50.48[500] 192.168.50.16[500] udp -P out none;
spdadd 192.168.50.16[500] 192.168.50.48[500] udp -P in none;
spdadd 192.168.50.48[4500] 192.168.50.16[4500] udp -P out none;
spdadd 192.168.50.16[4500] 192.168.50.48[4500] udp -P in none;
```

### 4. GRE隧道配置

**当前配置命令：**
```bash
# 创建GRE隧道
ip tunnel add gre1 mode gre \
    remote 192.168.50.16 \
    local 192.168.50.48 \
    key 123456 \
    ttl 255

# 配置隧道IP（点对点）
ip addr add 10.0.0.1/32 peer 10.0.0.2 dev gre1

# 启动隧道
ip link set gre1 up
```

**查看GRE隧道：**
```bash
# 查看隧道配置
ip tunnel show gre1

# 查看隧道接口
ip addr show gre1

# 查看隧道统计
ip -s link show gre1
```

## 四、监控和调试

### 1. 查看IPsec SA状态

```bash
# 查看所有安全关联
setkey -D

# 查看安全策略
setkey -DP

# 查看特定对端的SA
setkey -D | grep 192.168.50.16
```

**正常输出示例：**
```
192.168.50.48 192.168.50.16
	esp mode=transport spi=209434721(0x0c7bb861) reqid=0(0x00000000)
	E: des-cbc  8cf56f9f ccad6686
	A: hmac-md5  a27df77a 3e6e8cc5 bf19dc6b a636a61b
	seq=0x00000000 replay=4 flags=0x00000000 state=mature
	created: Nov 24 18:06:59 2025	current: Nov 24 18:07:25 2025
	diff: 38(s)	hard: 3600(s)	soft: 2880(s)
	current: 1234(bytes)	hard: 0(bytes)	soft: 0(bytes)
	allocated: 15	hard: 0	soft: 0
```

**关键字段说明：**
- `state=mature`: SA已建立并可用
- `current: 1234(bytes)`: 已传输的数据量
- `allocated: 15`: 已使用的包数

### 2. 查看racoon日志

```bash
# 实时查看日志
tail -f /var/log/syslog | grep racoon

# 查看最近50条日志
tail -50 /var/log/syslog | grep racoon

# 查看特定时间的日志
grep "Nov 24 18:00" /var/log/syslog | grep racoon
```

**日志关键信息：**
- `INFO: respond new phase 1 negotiation`: 收到IKE Phase 1请求
- `INFO: ISAKMP-SA established`: Phase 1协商成功
- `INFO: IPsec-SA established`: Phase 2协商成功，SA建立
- `ERROR: phase1 negotiation failed`: Phase 1失败
- `ERROR: no proposal chosen`: 协商参数不匹配

### 3. 测试连通性

```bash
# Ping路由器隧道IP
ping -c 5 10.0.0.2

# 跟踪路由
traceroute 10.0.0.2

# 检查GRE隧道状态
ip link show gre1

# 检查路由表
ip route show
```

### 4. 抓包调试

```bash
# 抓取IKE协商流量（UDP 500/4500）
tcpdump -i ens33 udp port 500 or udp port 4500 -n -v

# 抓取ESP加密流量
tcpdump -i ens33 esp -n -v

# 抓取GRE隧道流量
tcpdump -i gre1 -n -v

# 抓取与特定路由器的所有流量
tcpdump -i ens33 host 192.168.50.16 -n -v
```

### 5. 查看xfrm统计（IPsec统计）

```bash
# 查看IPsec统计
cat /proc/net/xfrm_stat

# 查看非零统计项
cat /proc/net/xfrm_stat | grep -v "\\s0$"
```

**关键统计项：**
- `XfrmOutNoStates`: 出站包没有找到SA（表示SPD策略问题）
- `XfrmInStateInvalid`: 入站SA无效
- `XfrmInHdrError`: 头部错误

## 五、添加新的Spoke路由器

### 方法1：使用相同PSK（推荐）

如果新路由器使用相同的PSK（`DMVPNsharedkey123`），无需修改服务器配置，路由器自动连接。

**路由器端配置要求：**
- Hub地址: `192.168.50.48`
- PSK密钥: `DMVPNsharedkey123`
- GRE密钥: `123456`
- 加密算法: DES
- 认证算法: MD5
- DH组: MODP768-1
- PFS组: NULL

### 方法2：使用独立PSK

如果需要为新路由器配置独立PSK：

```bash
# 1. 编辑PSK文件
vim /etc/racoon/psk.txt

# 添加新路由器配置
192.168.50.100   NewRouterPSK123

# 2. 修改权限
chmod 600 /etc/racoon/psk.txt

# 3. 重启racoon
systemctl restart racoon
```

### 方法3：动态mGRE模式（多点对多点）

对于真正的DMVPN（支持多Spoke），需要修改GRE隧道配置：

```bash
# 1. 删除现有点对点隧道
ip link set gre1 down
ip tunnel del gre1

# 2. 创建mGRE隧道（remote any）
ip tunnel add gre1 mode gre \
    local 192.168.50.48 \
    key 123456 \
    ttl 255

# 3. 配置隧道IP（网段模式）
ip addr add 10.0.0.1/24 dev gre1

# 4. 启动隧道
ip link set gre1 up

# 5. 更新SPD策略（允许任意对端）
cat > /etc/ipsec-tools.conf << 'EOF'
#!/usr/sbin/setkey -f
flush;
spdflush;

# GRE流量需要IPsec保护（任意对端）
spdadd 192.168.50.48 0.0.0.0/0 gre -P out ipsec esp/transport//require;
spdadd 0.0.0.0/0 192.168.50.48 gre -P in ipsec esp/transport//require;
EOF

# 6. 应用策略
setkey -F && setkey -FP && setkey -f /etc/ipsec-tools.conf

# 7. 安装NHRP守护进程（用于动态路由学习）
# apt-get install opennhrp
```

## 六、常见问题排查

### 1. 路由器无法连接

**问题现象：**
- 日志显示 `ERROR: no suitable proposal found`

**解决方法：**
```bash
# 检查racoon配置，确保加密参数匹配：
# - encryption_algorithm: des
# - hash_algorithm: md5
# - dh_group: 1 (MODP768)
# - 无PFS组配置

# 查看路由器发送的proposal
tail -100 /var/log/syslog | grep -E "(proposal|encryption|hash|dh_group)"
```

### 2. Phase 1成功但Phase 2失败

**问题现象：**
- 日志显示 `ERROR: pfs group mismatched`

**解决方法：**
```bash
# 在racoon.conf的sainfo中移除pfs_group行
vim /etc/racoon/racoon.conf

# 确保sainfo配置如下：
sainfo anonymous {
    encryption_algorithm des;
    authentication_algorithm hmac_md5;
    compression_algorithm deflate;
    # 不要添加 pfs_group
}

# 重启服务
systemctl restart racoon
```

### 3. SA建立但GRE不通

**问题现象：**
- `setkey -D` 显示SA存在且 state=mature
- `ping 10.0.0.2` 不通

**排查步骤：**

```bash
# 1. 检查GRE隧道状态
ip link show gre1
# 确保状态是 UP

# 2. 检查GRE隧道配置
ip tunnel show gre1
# 确保remote和key正确

# 3. 检查SPD策略
setkey -DP | grep gre
# 确保有出站和入站的GRE策略

# 4. 检查xfrm统计
cat /proc/net/xfrm_stat | grep -v "\\s0$"
# 如果XfrmOutNoStates不为0，说明SPD策略有问题

# 5. 检查路由表
ip route get 10.0.0.2
# 确保流量走gre1接口

# 6. 抓包验证
tcpdump -i ens33 esp -c 10
# 应该能看到ESP加密的包
```

### 4. PSK认证失败

**问题现象：**
- 日志显示 `ERROR: invalid length of payload`
- 或 `ERROR: phase1 negotiation failed due to time up`

**解决方法：**
```bash
# 1. 检查PSK文件格式
cat -A /etc/racoon/psk.txt
# 确保没有引号，格式为：
# 192.168.50.16   DMVPNsharedkey123

# 2. 检查文件权限
ls -l /etc/racoon/psk.txt
# 应该是 -rw------- (600)

# 3. 确保PSK与路由器一致
# 路由器PSK: DMVPNsharedkey123

# 4. 重启racoon
systemctl restart racoon
```

### 5. 服务无法启动

**问题现象：**
- `systemctl status racoon` 显示 failed

**解决方法：**
```bash
# 1. 查看详细错误
journalctl -u racoon -n 50

# 2. 检查配置文件语法
racoon -C -f /etc/racoon/racoon.conf

# 3. 常见错误：
# - DH group不一致（aggressive模式）
# - 配置文件语法错误
# - PSK文件路径错误

# 4. 手动启动测试
racoon -F -f /etc/racoon/racoon.conf
```

## 七、性能优化

### 1. 调整加密算法（更安全）

```bash
# 编辑racoon配置
vim /etc/racoon/racoon.conf

# 修改proposal（需要路由器也支持）
proposal {
    encryption_algorithm 3des;    # 或 aes
    hash_algorithm sha1;           # 或 sha256
    authentication_method pre_shared_key;
    dh_group 2;                    # MODP1024
}

# 修改sainfo
sainfo anonymous {
    encryption_algorithm 3des, aes;
    authentication_algorithm hmac_sha1, hmac_sha256;
    pfs_group 2;
}

# 重启服务
systemctl restart racoon
```

### 2. 调整MTU避免分片

```bash
# GRE + IPsec开销约60字节
# 标准以太网MTU 1500
# 建议GRE MTU: 1440

ip link set gre1 mtu 1440
```

### 3. 启用日志压缩

```bash
# 在racoon.conf中修改日志级别
log notify;  # 默认（推荐）
# log info;    # 详细日志（调试用）
# log debug;   # 完整调试日志（仅故障排查）
```

## 八、安全建议

### 1. 更换弱加密算法

当前使用的DES和MD5已被认为不安全，建议升级：

```
推荐配置：
- 加密: AES-256
- 认证: SHA256
- DH组: Group 14 (MODP2048)
- PFS: Group 14
```

### 2. 配置防火墙

```bash
# 仅允许特定IP连接
iptables -A INPUT -p udp --dport 500 -s 192.168.50.16 -j ACCEPT
iptables -A INPUT -p udp --dport 500 -j DROP

iptables -A INPUT -p udp --dport 4500 -s 192.168.50.16 -j ACCEPT
iptables -A INPUT -p udp --dport 4500 -j DROP

iptables -A INPUT -p esp -s 192.168.50.16 -j ACCEPT
iptables -A INPUT -p esp -j DROP
```

### 3. 定期更换PSK

```bash
# 1. 生成新的随机PSK
openssl rand -base64 32

# 2. 更新PSK文件
vim /etc/racoon/psk.txt

# 3. 更新路由器配置

# 4. 重启racoon
systemctl restart racoon
```

### 4. 启用日志审计

```bash
# 配置rsyslog记录racoon日志到独立文件
cat >> /etc/rsyslog.d/50-racoon.conf << 'EOF'
:programname, isequal, "racoon" /var/log/racoon.log
& stop
EOF

# 重启rsyslog
systemctl restart rsyslog
```

## 九、备份和恢复

### 备份配置

```bash
# 创建备份目录
mkdir -p /root/dmvpn_backup

# 备份所有配置文件
tar -czf /root/dmvpn_backup/dmvpn-config-$(date +%Y%m%d).tar.gz \
    /etc/racoon/racoon.conf \
    /etc/racoon/psk.txt \
    /etc/ipsec-tools.conf

# 保存GRE隧道配置
ip tunnel show gre1 > /root/dmvpn_backup/gre1-config.txt
ip addr show gre1 >> /root/dmvpn_backup/gre1-config.txt
```

### 恢复配置

```bash
# 解压备份
cd /root/dmvpn_backup
tar -xzf dmvpn-config-20251124.tar.gz -C /

# 修复权限
chmod 600 /etc/racoon/psk.txt
chmod +x /etc/ipsec-tools.conf

# 重建GRE隧道（参考备份的配置）
cat gre1-config.txt

# 应用策略
setkey -F && setkey -FP && setkey -f /etc/ipsec-tools.conf

# 重启服务
systemctl restart racoon
```

## 十、快速参考

### 常用命令速查

```bash
# 服务管理
systemctl start|stop|restart|status racoon

# 查看SA
setkey -D

# 查看SPD
setkey -DP

# 刷新SA和SPD
setkey -F && setkey -FP && setkey -f /etc/ipsec-tools.conf

# 查看GRE隧道
ip tunnel show gre1
ip addr show gre1
ip -s link show gre1

# 测试连通性
ping 10.0.0.2

# 实时日志
tail -f /var/log/syslog | grep racoon

# 抓包
tcpdump -i ens33 "udp port 500 or esp" -n
```

### 关键端口

- **UDP 500**: ISAKMP/IKE协商
- **UDP 4500**: NAT-T (NAT穿透)
- **Protocol 50**: ESP加密协议
- **Protocol 47**: GRE隧道协议

### 配置文件位置

- `/etc/racoon/racoon.conf` - racoon主配置
- `/etc/racoon/psk.txt` - PSK密钥文件
- `/etc/ipsec-tools.conf` - SPD安全策略
- `/var/log/syslog` - 日志文件

## 联系和支持

如有问题，请检查：
1. 服务器日志: `/var/log/syslog`
2. SA状态: `setkey -D`
3. SPD策略: `setkey -DP`
4. GRE隧道: `ip tunnel show`
5. xfrm统计: `cat /proc/net/xfrm_stat`

---

**文档版本**: 1.0
**最后更新**: 2025-11-24
**服务器IP**: 192.168.50.48
**适用系统**: Ubuntu 16.04 LTS
