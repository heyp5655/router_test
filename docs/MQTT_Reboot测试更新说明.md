# MQTT Reboot测试用例更新说明

## 更新时间
2025-11-25

## 更新内容

### 测试步骤完善
原测试步骤只验证了路由器收到命令后的初始响应,现在增加了完整的重启验证流程。

### 新增测试步骤

#### 步骤8: 验证系统日志中的重启记录
- **目的**: 通过SSH连接路由器,查看系统日志确认重启确实发生
- **实现**: `_verify_reboot_log()` 方法
- **验证点**:
  - 日志文件: `/etc/urlog/system.log`
  - 关键词: `reboot: Restarting system`
  - 最多等待20次,每次间隔15秒
  - 显示最近10条reboot相关日志

```python
def _verify_reboot_log(self):
    """通过SSH验证系统日志中的重启记录"""
    # SSH连接路由器
    # 执行: cat /etc/urlog/system.log | grep -i reboot | tail -10
    # 检查日志中是否包含"Restarting system"
```

#### 步骤9: 等待路由器重新连接MQTT
- **目的**: 确认路由器重启后能重新连接到MQTT服务器
- **实现**: `_wait_mqtt_reconnect()` 方法
- **步骤**:
  1. 重新登录路由器Web界面
  2. 导航到MQTT状态页面
  3. 使用 `wait_for_mqtt_connection()` 等待连接
  4. 最多等待180秒,每5秒检查一次

```python
def _wait_mqtt_reconnect(self):
    """等待路由器重新连接MQTT"""
    # 重新登录Web
    # 检查MQTT连接状态
    # 兼容中英文状态
```

#### 步骤10-11: 验证第二次响应消息
- **目的**: 验证路由器重启完成后发送的通知消息
- **实现**: `_wait_for_second_response()` 和 `_verify_second_response_format()` 方法
- **消息格式**:
```json
{
  "code": "2",
  "id": "1",
  "time": "2025-11-25T09:55:22Z",
  "status": "reboot",
  "result": 1,
  "resultmsg": "Reboot system success"
}
```

### 响应消息区分

#### 第一次响应 (步骤5-6)
- **时机**: 收到reboot命令后立即响应
- **用途**: 确认路由器收到命令
- **字段**:
  - `id`: 命令ID
  - `code`: "2" (表示已接收)
  - `status`: "reboot"
  - `time`: 时间戳

#### 第二次响应 (步骤10-11)
- **时机**: 重启完成后,重新连接MQTT时发送
- **用途**: 通知重启完成状态
- **字段**:
  - `id`: 命令ID
  - `code`: "2"
  - `status`: "reboot"
  - `time`: 时间戳
  - `result`: 1 (成功)
  - `resultmsg`: "Reboot system success"

### 方法重命名

| 原方法名 | 新方法名 | 说明 |
|---------|---------|------|
| `_wait_for_response()` | `_wait_for_first_response()` | 等待第一次响应 |
| `_verify_response_format()` | `_verify_first_response_format()` | 验证第一次响应格式 |
| `_verify_router_reboot()` | `_verify_reboot_log()` | 验证系统日志 |
| - | `_wait_mqtt_reconnect()` | 新增:等待MQTT重连 |
| - | `_wait_for_second_response()` | 新增:等待第二次响应 |
| - | `_verify_second_response_format()` | 新增:验证第二次响应 |

### 变量重命名

| 原变量名 | 新变量名 | 说明 |
|---------|---------|------|
| `self.router_response` | `self.first_response` | 第一次响应内容 |
| - | `self.second_response` | 第二次响应内容 |

### 测试流程对比

#### 更新前
```
1. 配置MQTT → 2. 连接客户端 → 3. 订阅主题 → 4. 发送命令
→ 5. 收到响应 → 6. 验证格式 → 7. 验证重启 → 结束
```

#### 更新后
```
1. 配置MQTT → 2. 连接客户端 → 3. 订阅主题 → 4. 发送命令
→ 5. 收到第一次响应 → 6. 验证第一次格式 → 7. 等待重启开始
→ 8. 验证系统日志 → 9. 等待MQTT重连 → 10. 收到第二次响应
→ 11. 验证第二次格式 → 结束
```

### 优化点

1. **更完整的验证**
   - 不仅验证响应消息,还验证系统日志
   - 确认重启真正发生
   - 验证重启后的MQTT重连

2. **更好的错误处理**
   - SSH连接失败会重试(最多20次)
   - 第二次响应未收到不会导致测试失败(因为某些路由器可能不发送)
   - 每个步骤都有详细的日志输出

3. **时间优化**
   - 系统日志验证: 最多等待5分钟(20次 × 15秒)
   - MQTT重连验证: 最多等待3分钟(180秒)
   - 第二次响应等待: 最多1分钟(60秒)

4. **兼容性**
   - 第二次响应是可选的(部分路由器可能不发送)
   - 支持中英文MQTT状态显示
   - 系统日志检查支持多种格式

## 使用说明

### 配置要求
确保在配置文件中设置正确的SSH凭据:
```python
self.SSH_ROOT_USERNAME = "root"
self.SSH_ROOT_PASSWORD = "your_password"
```

### 预期时间
完整测试预计耗时: **8-10分钟**
- MQTT配置和连接: 1-2分钟
- 发送命令和第一次响应: 10秒
- 等待重启: 30秒
- SSH验证日志: 1-5分钟
- MQTT重连: 1-3分钟
- 第二次响应: 0-1分钟

### 失败排查

#### 第一次响应未收到
- 检查MQTT服务器连接
- 检查主题配置是否正确
- 检查路由器是否支持MQTT命令

#### 系统日志验证失败
- 检查SSH凭据是否正确
- 检查路由器是否真正重启
- 检查日志文件路径: `/etc/urlog/system.log`

#### MQTT重连失败
- 路由器可能重启时间过长
- MQTT配置可能在重启后丢失
- 检查Web界面是否需要重新登录

#### 第二次响应未收到
- 这是正常的,部分路由器不发送重启完成消息
- 不会导致测试失败

## 相关文件
- 测试用例: `test_cases/mqtt_test/mqtt_router_command_reboot_test.py`
- MQTT客户端: `utils/mqtt_client.py`
- 路由器客户端: `core/router_client.py`

---
**最后更新**: 2025-11-25
