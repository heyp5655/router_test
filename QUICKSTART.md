# ROUTER_TEST - 快速开始指南 🚀

## 📋 前提条件

- Windows 10/11 (需要管理员权限)
- 路由器设备 (支持Web界面)
- 网络连接

## 🎯 5分钟快速上手

### 1️⃣ 新电脑首次安装

```bash
# 以管理员身份运行
完整安装_含GitHub.bat

# 按提示输入 Git 用户信息
# 等待自动完成（约 10 分钟）
```

### 2️⃣ 启动测试平台

```bash
# 推荐：使用启动脚本（自动管理员权限）
start_admin.bat

# 或手动以管理员身份运行
python app.py
```

### 3️⃣ 访问 Web 界面

浏览器打开: **http://localhost:5000**

## ⚙️ 常见操作

### 依赖问题修复
```bash
# 以管理员身份运行
修复依赖安装.bat
```

### 配置路由器连接
编辑 `config/default_config.yaml`:
```yaml
router_ip: "192.168.1.1"      # 路由器IP
username: "admin"             # 用户名
password: "password"          # 密码
```

### 配置测试网卡
默认网卡名称: `TEST`

查看网卡名称:
```powershell
Get-NetAdapter
```

## 📚 进一步阅读

- **项目结构规范**: `PROJECT_STRUCTURE.md` ⭐ 必读！
- **完整文档**: `CLAUDE.md`
- **历史更新**: `CHANGELOG.md`
- **详细安装指南**: `安装使用指南.md`

## ❗ 注意事项

- ✅ Windows 需要**管理员权限**运行（修改网络配置）
- ✅ Web 服务默认端口 **5000**
- ✅ 修改代码后需要**重启 Flask 服务**
- ✅ 测试网卡名称默认为 `TEST`

## 🆘 遇到问题？

1. 查看日志文件: `logs/` 目录
2. 阅读文档: `CLAUDE.md` → "项目维护说明"
3. 检查网络连接和路由器配置
4. 运行依赖修复: `修复依赖安装.bat`

---

**💡 提示**: 第一次使用建议阅读 `PROJECT_STRUCTURE.md` 了解代码组织规范！
