# VPN工具集 (DMVPN/IPSec/GRE)

本目录包含所有与VPN相关的诊断、配置和测试工具。

## 📁 目录结构

```
scripts/vpn_tools/
├── README.md                      # 本文档
├── dmvpn_config_gui.py            # 🌟 DMVPN可视化配置工具 (推荐)
├── DMVPN配置工具使用说明.md        # GUI工具使用说明
│
├── DMVPN诊断工具/
│   ├── check_dmvpn.py              # 检查DMVPN连接状态
│   ├── diagnose_dmvpn_detailed.py  # 详细诊断DMVPN问题
│   ├── fix_dmvpn.py                # 快速修复DMVPN配置
│   ├── monitor_dmvpn.py            # 监控DMVPN连接状态
│   ├── configure_dmvpn_nat.py      # 配置NAT环境下的DMVPN
│   ├── check_router_10_33_126_188.py   # 检查特定路由器连接
│   ├── diagnose_router_timeout.py      # 诊断路由器超时问题
│   ├── monitor_4g_router.py            # 监控4G路由器连接
│   ├── add_new_router_ip.py            # 添加新路由器IP到配置
│   └── configure_router_10_9_139_97.py # 配置特定路由器
│
├── GRE隧道工具/
│   ├── diagnose_gre.py             # 诊断GRE隧道问题
│   ├── test_correct_gre_ip.py      # 测试GRE IP配置
│   ├── test_gre_10003.py           # 测试GRE端口10003
│   └── setup_gre_remote.sh         # 远程设置GRE隧道
│
├── Racoon调试工具/
│   ├── check_racoon_error.py       # 检查Racoon错误
│   ├── check_racoon_logs.py        # 检查Racoon日志
│   ├── debug_racoon.py             # Racoon调试工具
│   ├── debug_racoon_verbose.py     # Racoon详细调试
│   └── monitor_vpn_restart.py      # 监控VPN重启
│
└── IPSec配置工具/
    ├── change_to_aes128.py         # 切换到AES-128加密
    ├── change_to_aes192.py         # 切换到AES-192加密
    ├── change_to_aes256.py         # 切换到AES-256加密
    ├── fix_aes192_complete.py      # 完整修复AES-192配置
    ├── test_aes256_sha256.py       # 测试AES-256+SHA-256
    ├── change_to_modp2048.py       # 切换到DH Group 14 (modp2048)
    ├── change_back_to_modp3072.py  # 切换回DH Group 15 (modp3072)
    ├── fix_modp3072.py             # 修复modp3072配置
    └── fix_server_match_router.py  # 修复服务器与路由器匹配
```

---

## 🌟 DMVPN可视化配置工具 (推荐)

### `dmvpn_config_gui.py` ⭐⭐⭐

**用途**: Windows 10图形界面工具，用于可视化配置DMVPN服务器

**主要功能**:
- ✅ 图形界面配置所有DMVPN参数
- ✅ 支持所有主流加密算法和DH组
- ✅ 一键应用配置到远程服务器
- ✅ 自动备份现有配置
- ✅ 实时日志输出和配置验证

**启动方式**:
```bash
# 方式1: 双击根目录的批处理文件
启动DMVPN配置工具.bat

# 方式2: 命令行启动
python scripts/vpn_tools/dmvpn_config_gui.py
```

**配置参数**:
- **SSH连接**: 服务器IP、端口、用户名、密码
- **基础配置**: Hub地址、接口类型
- **GRE隧道**: IP地址、子网掩码、密钥
- **IPSec Phase 1**: 协商模式、加密算法、认证算法、DH组
- **IPSec Phase 2**: PSK密钥、SA算法、PFS组、生存时间
- **高级配置**: DPD、NHRP、NAT穿透

**支持的加密算法**:
- 加密: AES256/192/128, 3DES, DES, BLOWFISH
- 认证: SHA2-256/384/512, SHA1, MD5
- DH组: MODP1024~8192, ECP256/384/521

**详细文档**: 见 `DMVPN配置工具使用说明.md`

---

## 🔧 常用工具说明

### 1. DMVPN诊断工具

#### `diagnose_dmvpn_detailed.py` ⭐
**用途**: 详细诊断DMVPN连接问题，包括IPSec SA、GRE隧道、路由等

**使用场景**:
- DMVPN连接失败
- GRE隧道无法建立
- 路由器无法ping通服务器

**示例**:
```bash
python scripts/vpn_tools/diagnose_dmvpn_detailed.py
```

**输出内容**:
- IPSec SA状态
- GRE隧道配置
- Racoon配置信息
- 路由表
- 连接测试结果

#### `configure_dmvpn_nat.py` ⭐
**用途**: 配置NAT环境下的DMVPN (公网IP访问)

**使用场景**:
- 服务器在私网，需通过公网IP提供服务
- 路由器通过4G公网连接到Hub

**示例**:
```bash
python scripts/vpn_tools/configure_dmvpn_nat.py
```

**配置内容**:
- 设置NAT-T force模式
- 配置anonymous模式
- 检查端口映射

#### `fix_dmvpn.py`
**用途**: 快速修复常见DMVPN配置问题

**修复内容**:
- 重启Racoon服务
- 重新加载GRE隧道
- 清理IPSec SA

#### `monitor_dmvpn.py`
**用途**: 实时监控DMVPN连接状态

**监控内容**:
- IPSec SA数量
- GRE隧道状态
- 连接持续时间

---

### 2. GRE隧道工具

#### `diagnose_gre.py`
**用途**: 诊断GRE隧道问题

**检查内容**:
- GRE接口状态
- IP地址配置
- 路由配置
- Ping测试

#### `test_gre_10003.py`
**用途**: 测试GRE端口10003的连通性

**使用场景**:
- 验证GRE隧道是否正常工作
- 测试路由器到服务器的GRE流量

---

### 3. Racoon调试工具

#### `debug_racoon_verbose.py` ⭐
**用途**: 开启Racoon详细日志并实时查看

**使用场景**:
- IPSec协商失败
- 需要查看详细的IKE交换过程

**输出内容**:
- IKE Phase 1/2 协商过程
- 加密算法协商
- DH组协商
- NAT-T检测

#### `check_racoon_logs.py`
**用途**: 查看Racoon日志中的错误和警告

**输出内容**:
- ERROR级别日志
- WARNING级别日志
- 最近的连接记录

#### `monitor_vpn_restart.py`
**用途**: 监控VPN重启后的连接恢复

**使用场景**:
- 重启Racoon服务后验证
- 测试自动重连功能

---

### 4. IPSec配置工具

#### 加密算法切换工具

- `change_to_aes128.py` - 切换到AES-128 (最快，兼容性最好)
- `change_to_aes192.py` - 切换到AES-192 (平衡性能和安全性)
- `change_to_aes256.py` - 切换到AES-256 (最安全，性能稍低)

**使用场景**:
- 路由器只支持特定加密算法
- 测试不同加密算法的性能

#### DH组切换工具

- `change_to_modp2048.py` - 切换到DH Group 14 (兼容性好)
- `change_back_to_modp3072.py` - 切换回DH Group 15 (更安全)

**使用场景**:
- 路由器不支持modp3072
- 需要更快的密钥交换

#### `fix_server_match_router.py`
**用途**: 确保服务器配置与路由器匹配

**修复内容**:
- 加密算法匹配
- DH组匹配
- 认证算法匹配

---

## 📚 相关文档

详细的VPN配置和使用文档位于: `docs/vpn/`

**主要文档**:
- `DMVPN_SERVER_GUIDE.md` - DMVPN服务器配置指南
- `DMVPN快速修复指南_20251127.md` - 快速修复参考
- `DMVPN_NAT端口映射配置指南_20251127.md` - NAT配置详解
- `GRE隧道配置手册.md` - GRE隧道配置说明
- `4G路由器公网连接方案_20251127.md` - 4G路由器连接方案
- `完整网络拓扑与问题分析_20251127.md` - 网络拓扑分析

---

## 🌐 测试环境

### DMVPN服务器
- **地址**: 192.168.50.48 (私网)
- **公网IP**: 112.48.19.183
- **用户名**: yuxy
- **密码**: milesight123

### IPSec配置
- **Phase 1**: Main Mode, AES256, SHA256, modp3072 (DH Group 15)
- **Phase 2**: AES256/192/128, HMAC-SHA256
- **PSK密钥**: 123456

### GRE隧道
- **服务器GRE IP**: 10.0.0.1/24
- **GRE密钥**: 123456
- **隧道接口**: gre1

### 支持的路由器IP
- 192.168.40.207, 192.168.40.210, 192.168.40.237
- 192.168.50.16, 192.168.50.40, 192.168.50.123
- 192.168.40.242
- 10.33.126.188

---

## ⚠️ 注意事项

1. **SSH访问**: 所有工具需要SSH访问服务器 (192.168.50.48)
2. **管理员权限**: 部分工具需要sudo权限
3. **备份配置**: 修改配置前请备份原始文件
4. **生产环境**: 生产环境使用前请先在测试环境验证

---

## 🔍 故障排查流程

### DMVPN连接失败
1. 运行 `diagnose_dmvpn_detailed.py` 获取详细诊断
2. 检查 IPSec SA 是否建立
3. 检查 GRE 隧道是否配置正确
4. 运行 `debug_racoon_verbose.py` 查看协商过程
5. 如需修复，运行 `fix_dmvpn.py`

### NAT环境下的DMVPN
1. 运行 `configure_dmvpn_nat.py` 配置NAT-T
2. 确保NAT网关端口映射为标准端口 (500→500, 4500→4500)
3. 路由器配置Hub为公网IP (112.48.19.183)
4. 运行 `diagnose_dmvpn_detailed.py` 验证

### 加密算法不匹配
1. 检查路由器支持的算法
2. 运行对应的切换脚本 (change_to_aes*.py)
3. 重启Racoon服务
4. 验证连接

---

**最后更新**: 2025-11-27
**维护者**: 项目团队
