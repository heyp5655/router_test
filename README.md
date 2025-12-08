# ROUTER_TEST - 路由器自动化测试框架

> 基于 Flask 的路由器自动化测试平台，支持 WAN、蜂窝网络、MQTT 等功能测试

## 🚀 快速开始

### 新电脑首次安装

```bash
# 1. 运行安装脚本（以管理员身份）
完整安装_含GitHub.bat

# 2. 按提示输入 Git 信息
# 3. 等待自动完成（约 10 分钟）
# 4. 浏览器访问 http://localhost:5000
```

### 日常使用

```bash
# 启动测试框架
start_admin.bat
```

## 📚 文档

- **[安装使用指南.md](安装使用指南.md)** - 详细的安装和使用说明
- **[CLAUDE.md](CLAUDE.md)** - 项目概述和开发指南
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - 项目结构规范（必读）

## 🛠️ 技术栈

- Python 3.12
- Flask 2.3.3
- Selenium 4.12.0
- PySerial 3.5
- paho-mqtt 2.0+
- paramiko 2.7+

## 📁 项目结构

```
├── app.py                  # Flask 主应用
├── core/                   # 核心模块
├── test_cases/             # 测试用例
├── utils/                  # 工具类
├── config/                 # 配置文件
└── templates/              # Web 模板
```

## ⚠️ 注意事项

- 需要管理员权限运行（修改网络配置）
- 默认端口：5000
- 测试网卡名称：TEST

## 🔧 问题修复

如果遇到依赖问题：

```bash
# 运行修复脚本（以管理员身份）
修复依赖安装.bat
```

## 📝 许可

内部项目

---

**最后更新**: 2025-11-26
