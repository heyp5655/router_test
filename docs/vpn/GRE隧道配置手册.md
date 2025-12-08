# GRE隧道永久化配置 - 手动操作指南

## 服务器信息
- **服务器IP**: 192.168.50.48
- **用户名**: yuxy
- **GRE隧道IP**: 10.0.0.1/24
- **路由器GRE IP**: 10.0.0.3
- **GRE密钥**: 123456

---

## 快速配置步骤（5分钟完成）

### 步骤1: SSH登录服务器

```bash
ssh yuxy@192.168.50.48
# 输入密码
```

### 步骤2: 检查当前GRE隧道状态

```bash
ip addr show gre1
# 如果显示 "Device does not exist"，说明需要创建
```

### 步骤3: 创建永久化配置文件

```bash
# 创建配置文件（一键复制粘贴）
sudo tee /etc/network/interfaces.d/gre1 > /dev/null << 'EOF'
# GRE隧道配置 - DMVPN Hub
# 创建时间: 2025-11-26
# 本地物理IP: 192.168.50.48
# 隧道IP: 10.0.0.1
# GRE密钥: 123456

auto gre1
iface gre1 inet static
    address 10.0.0.1
    netmask 255.255.255.0
    pre-up ip tunnel add gre1 mode gre local 192.168.50.48 key 123456
    post-down ip tunnel del gre1
EOF
```

**输入sudo密码后，配置文件即创建成功！**

### 步骤4: 验证配置文件内容

```bash
cat /etc/network/interfaces.d/gre1
```

应该看到刚才创建的配置内容。

### 步骤5: 立即创建并启动GRE隧道

```bash
# 如果隧道已存在，先删除
sudo ip link set gre1 down 2>/dev/null
sudo ip tunnel del gre1 2>/dev/null

# 创建新隧道
sudo ip tunnel add gre1 mode gre local 192.168.50.48 key 123456
sudo ip addr add 10.0.0.1/24 dev gre1
sudo ip link set gre1 up
```

### 步骤6: 验证隧道已创建

```bash
# 查看隧道接口
ip addr show gre1
```

**预期输出：**
```
X: gre1@NONE: <POINTOPOINT,NOARP,UP,LOWER_UP> mtu 1476 qdisc noqueue state UNKNOWN group default
    link/gre 192.168.50.48 peer 0.0.0.0
    inet 10.0.0.1/24 scope global gre1
       valid_lft forever preferred_lft forever
```

看到 `UP,LOWER_UP` 和 `inet 10.0.0.1/24` 就说明成功了！

### 步骤7: 查看GRE隧道详细信息

```bash
ip tunnel show gre1
```

**预期输出：**
```
gre1: gre/ip remote any local 192.168.50.48 ttl inherit key 123456
```

### 步骤8: 检查路由表

```bash
ip route | grep 10.0.0
```

**预期输出：**
```
10.0.0.0/24 dev gre1 proto kernel scope link src 10.0.0.1
```

### 步骤9: 测试连通性

```bash
# 尝试ping路由器的GRE IP
ping -c 4 10.0.0.3
```

**可能结果：**
- ✓ **能ping通**: 说明路由器已配置好DMVPN和GRE隧道，双向通信正常！
- ✗ **不能ping通**: 说明路由器可能还未配置或防火墙阻止，这是正常的，等路由器配置完成后再测试

---

## 验证永久化配置

### 测试重启后自动生效（可选）

```bash
# 方法1: 重启网络服务
sudo systemctl restart networking

# 方法2: 手动关闭再启动
sudo ifdown gre1
sudo ifup gre1

# 验证隧道仍然存在
ip addr show gre1
```

---

## 常用管理命令

```bash
# 查看隧道状态
ip addr show gre1
ip tunnel show gre1

# 手动启动隧道
sudo ifup gre1

# 手动停止隧道
sudo ifdown gre1

# 重启隧道
sudo ifdown gre1 && sudo ifup gre1

# 查看路由表
ip route | grep 10.0.0

# 查看所有GRE隧道
ip tunnel show

# 实时ping测试
ping 10.0.0.3
```

---

## 故障排查

### 问题1: 创建隧道时提示 "Device or resource busy"

**解决**：
```bash
# 先删除现有隧道
sudo ip link set gre1 down
sudo ip tunnel del gre1

# 再重新创建
sudo ip tunnel add gre1 mode gre local 192.168.50.48 key 123456
sudo ip addr add 10.0.0.1/24 dev gre1
sudo ip link set gre1 up
```

### 问题2: 隧道状态显示 DOWN

**检查**：
```bash
# 手动启动
sudo ip link set gre1 up

# 查看状态
ip link show gre1
```

### 问题3: ping不通路由器 10.0.0.3

**原因和解决**：

1. **路由器还未配置DMVPN** - 等待路由器配置完成
2. **路由器防火墙阻止** - 检查路由器防火墙规则
3. **服务器防火墙阻止** - 临时禁用测试：
   ```bash
   sudo ufw status
   sudo ufw disable
   ping 10.0.0.3
   sudo ufw enable
   ```

### 问题4: 配置文件不生效

**检查配置文件语法**：
```bash
# 查看配置文件
cat /etc/network/interfaces.d/gre1

# 测试配置
sudo ifdown gre1
sudo ifup gre1 -v  # -v 参数显示详细信息
```

---

## 配置完成检查清单

完成以下检查确保配置成功：

- [ ] SSH成功登录服务器 192.168.50.48
- [ ] 配置文件已创建：`/etc/network/interfaces.d/gre1`
- [ ] GRE隧道已创建：`ip addr show gre1` 显示 UP 状态
- [ ] 隧道IP已配置：显示 `inet 10.0.0.1/24`
- [ ] 路由表已生成：`ip route | grep 10.0.0` 有输出
- [ ] 能从服务器ping路由器 10.0.0.3（如果路由器已配置）

---

## 一键脚本（备选方案）

如果上面的步骤太多，也可以使用这个一键脚本：

```bash
# 在服务器上创建脚本
cat > ~/setup_gre.sh << 'SCRIPTEND'
#!/bin/bash
echo "=== 创建GRE隧道配置 ==="
sudo tee /etc/network/interfaces.d/gre1 > /dev/null << 'EOF'
auto gre1
iface gre1 inet static
    address 10.0.0.1
    netmask 255.255.255.0
    pre-up ip tunnel add gre1 mode gre local 192.168.50.48 key 123456
    post-down ip tunnel del gre1
EOF
echo "✓ 配置文件已创建"

echo "=== 创建GRE隧道 ==="
sudo ip link set gre1 down 2>/dev/null
sudo ip tunnel del gre1 2>/dev/null
sudo ip tunnel add gre1 mode gre local 192.168.50.48 key 123456
sudo ip addr add 10.0.0.1/24 dev gre1
sudo ip link set gre1 up
echo "✓ GRE隧道已创建"

echo "=== 验证 ==="
ip addr show gre1
echo ""
ip route | grep 10.0.0
echo ""
echo "测试连通性:"
ping -c 3 10.0.0.3 || echo "无法ping通路由器（可能还未配置）"
SCRIPTEND

# 运行脚本
bash ~/setup_gre.sh
```

---

## 完成后的预期状态

### 服务器端
- ✅ GRE隧道 gre1 已创建并运行
- ✅ 隧道IP: 10.0.0.1/24
- ✅ 配置永久化，重启后自动生效
- ✅ 路由表包含 10.0.0.0/24 网段

### 等待路由器端
- ⏳ 路由器修改4项加密参数
- ⏳ 路由器PSK改为 123456
- ⏳ 路由器DMVPN连接成功
- ⏳ 双向ping通测试

---

**配置完成后，请告知我结果，我会协助进行下一步测试！**
