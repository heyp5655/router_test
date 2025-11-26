# MQTT Reboot测试日志优化说明

## 更新时间
2025-11-25 (第三次优化)

## 优化目标
统一所有MQTT消息的日志输出格式，使用JSON格式显示，便于调试和问题追踪。

## 优化内容

### 1. 发送MQTT消息的日志格式

**改进前**：
```python
print(f"  发送命令: {json.dumps(command)}")
# 输出: 发送命令: {"id":"1","status":"reboot"}
```

**改进后**：
```python
print(f"  发送MQTT消息到主题: {self.REQUEST_TOPIC}")
print(f"  消息内容(JSON):")
print(f"    {json.dumps(command, indent=2, ensure_ascii=False)}")
```

**输出示例**：
```
  发送MQTT消息到主题: mqtt/system/request
  消息内容(JSON):
    {
      "id": "1",
      "status": "reboot"
    }
  ✅ 命令发送成功
```

### 2. 接收第一次响应的日志格式

**改进前**：
```python
print(f"  ✅ 收到第一次响应: {self.first_response}")
# 输出: ✅ 收到第一次响应: {"id":"1","code":"2","status":"reboot","time":"..."}
```

**改进后**：
```python
print(f"  ✅ 收到MQTT响应消息")
print(f"  主题: {response_msg.get('topic', self.RESPONSE_TOPIC)}")
print(f"  消息内容(JSON):")
try:
    response_json = json.loads(self.first_response)
    print(f"    {json.dumps(response_json, indent=2, ensure_ascii=False)}")
except:
    print(f"    {self.first_response}")
```

**输出示例**：
```
  等待路由器第一次响应（最多10秒）...
  监听主题: mqtt/system/response
  ✅ 收到MQTT响应消息
  主题: mqtt/system/response
  消息内容(JSON):
    {
      "id": "1",
      "code": "2",
      "status": "reboot",
      "time": "2025-11-25T10:30:45Z"
    }
```

### 3. 验证第一次响应格式的日志

**改进前**：
```python
print(f"  第一次响应内容:")
print(f"    {json.dumps(response_json, indent=2, ensure_ascii=False)}")
print("  ✅ 第一次响应格式验证通过")
print(f"     - id: {response_json['id']}")
print(f"     - code: {response_json['code']}")
print(f"     - status: {response_json['status']}")
```

**改进后**：
```python
print(f"  验证第一次响应消息格式...")
print(f"  完整消息(JSON):")
print(f"    {json.dumps(response_json, indent=2, ensure_ascii=False)}")
print("  ✅ 第一次响应格式验证通过")
print(f"  验证结果:")
print(f"    - id: {response_json['id']} ✓")
print(f"    - code: {response_json['code']} ✓")
print(f"    - status: {response_json['status']} ✓")
```

**输出示例**：
```
  验证第一次响应消息格式...
  完整消息(JSON):
    {
      "id": "1",
      "code": "2",
      "status": "reboot",
      "time": "2025-11-25T10:30:45Z"
    }
  ✅ 第一次响应格式验证通过
  验证结果:
    - id: 1 ✓
    - code: 2 ✓
    - status: reboot ✓
    - time: 2025-11-25T10:30:45Z
```

### 4. 接收第二次响应的日志格式

**改进前**：
```python
print(f"  ✅ 收到第二次响应: {self.second_response}")
```

**改进后**：
```python
print(f"  收到MQTT消息")
print(f"  主题: {response_msg.get('topic', self.RESPONSE_TOPIC)}")
print(f"  原始消息(JSON):")
try:
    temp_json = json.loads(response_msg['payload'])
    print(f"    {json.dumps(temp_json, indent=2, ensure_ascii=False)}")
except:
    print(f"    {response_msg['payload']}")
print(f"  ✅ 确认为第二次响应（包含result字段）")
```

**输出示例**：
```
  检查是否已收到第二次响应...
  监听主题: mqtt/system/response
  收到MQTT消息
  主题: mqtt/system/response
  原始消息(JSON):
    {
      "id": "1",
      "code": "2",
      "status": "reboot",
      "result": 1,
      "resultmsg": "Reboot system success",
      "time": "2025-11-25T10:35:20Z"
    }
  ✅ 确认为第二次响应（包含result字段）
```

### 5. 验证第二次响应格式的日志

**改进后**：
```python
print(f"  验证第二次响应消息格式...")
print(f"  完整消息(JSON):")
print(f"    {json.dumps(response_json, indent=2, ensure_ascii=False)}")
print("  ✅ 第二次响应格式验证通过")
print(f"  验证结果:")
print(f"    - id: {response_json['id']} ✓")
print(f"    - code: {response_json['code']} ✓")
print(f"    - status: {response_json['status']} ✓")
print(f"    - result: {response_json['result']} ✓")
print(f"    - resultmsg: {response_json['resultmsg']} ✓")
```

**输出示例**：
```
  验证第二次响应消息格式...
  完整消息(JSON):
    {
      "id": "1",
      "code": "2",
      "status": "reboot",
      "result": 1,
      "resultmsg": "Reboot system success",
      "time": "2025-11-25T10:35:20Z"
    }
  ✅ 第二次响应格式验证通过
  验证结果:
    - id: 1 ✓
    - code: 2 ✓
    - status: reboot ✓
    - result: 1 ✓
    - resultmsg: Reboot system success ✓
    - time: 2025-11-25T10:35:20Z
```

## 日志格式规范

### MQTT消息输出标准格式

所有MQTT消息统一使用以下格式：

1. **发送消息**：
   ```
   发送MQTT消息到主题: <topic_name>
   消息内容(JSON):
     <formatted_json>
   ```

2. **接收消息**：
   ```
   收到MQTT消息
   主题: <topic_name>
   消息内容(JSON) 或 原始消息(JSON):
     <formatted_json>
   ```

3. **验证消息格式**：
   ```
   验证<第X次>响应消息格式...
   完整消息(JSON):
     <formatted_json>
   验证结果:
     - field1: value1 ✓
     - field2: value2 ✓
   ```

### JSON格式化参数

使用统一的JSON格式化参数：
```python
json.dumps(data, indent=2, ensure_ascii=False)
```

- `indent=2` - 缩进2个空格，便于阅读
- `ensure_ascii=False` - 支持中文等非ASCII字符

### 异常处理

如果JSON解析失败，显示原始消息：
```python
try:
    json_data = json.loads(message)
    print(f"    {json.dumps(json_data, indent=2, ensure_ascii=False)}")
except:
    print(f"    {message}")
```

## 优化效果

### 1. 可读性提升
- ✅ JSON格式化输出，层次结构清晰
- ✅ 统一的日志格式，易于理解
- ✅ 关键信息醒目（主题、字段验证结果）

### 2. 调试便利性
- ✅ 完整的MQTT消息内容展示
- ✅ 清晰的发送/接收区分
- ✅ 字段级别的验证结果（✓标记）

### 3. 问题定位
- ✅ 易于发现消息格式问题
- ✅ 便于复制JSON进行测试
- ✅ 清晰的主题信息

## 完整测试日志示例

```
步骤4: 发送reboot命令...
  发送MQTT消息到主题: mqtt/system/request
  消息内容(JSON):
    {
      "id": "1",
      "status": "reboot"
    }
  ✅ 命令发送成功

步骤5: 等待路由器第一次响应...
  等待路由器第一次响应（最多10秒）...
  监听主题: mqtt/system/response
  ✅ 收到MQTT响应消息
  主题: mqtt/system/response
  消息内容(JSON):
    {
      "id": "1",
      "code": "2",
      "status": "reboot",
      "time": "2025-11-25T10:30:45Z"
    }
✅ 收到路由器第一次响应

步骤6: 验证第一次响应消息格式...
  验证第一次响应消息格式...
  完整消息(JSON):
    {
      "id": "1",
      "code": "2",
      "status": "reboot",
      "time": "2025-11-25T10:30:45Z"
    }
  ✅ 第一次响应格式验证通过
  验证结果:
    - id: 1 ✓
    - code: 2 ✓
    - status: reboot ✓
    - time: 2025-11-25T10:30:45Z
✅ 第一次响应消息格式正确

步骤9: 等待路由器第二次响应(重启完成消息)...
  检查是否已收到第二次响应...
  监听主题: mqtt/system/response
  收到MQTT消息
  主题: mqtt/system/response
  原始消息(JSON):
    {
      "id": "1",
      "code": "2",
      "status": "reboot",
      "result": 1,
      "resultmsg": "Reboot system success",
      "time": "2025-11-25T10:35:20Z"
    }
  ✅ 确认为第二次响应（包含result字段）
✅ 收到路由器第二次响应

步骤10: 验证第二次响应消息格式...
  验证第二次响应消息格式...
  完整消息(JSON):
    {
      "id": "1",
      "code": "2",
      "status": "reboot",
      "result": 1,
      "resultmsg": "Reboot system success",
      "time": "2025-11-25T10:35:20Z"
    }
  ✅ 第二次响应格式验证通过
  验证结果:
    - id: 1 ✓
    - code: 2 ✓
    - status: reboot ✓
    - result: 1 ✓
    - resultmsg: Reboot system success ✓
    - time: 2025-11-25T10:35:20Z
✅ 第二次响应消息格式正确
```

## 相关文件

- `test_cases/mqtt_test/mqtt_router_command_reboot_test.py` - 测试用例实现
- `docs/MQTT_Reboot测试优化说明.md` - 完整优化说明文档

## 优化历史

1. **第一次优化** - PC端持续监听，不清空消息队列
2. **第二次优化** - 严格失败判断，移除冗余Web界面检查
3. **第三次优化** - 统一MQTT消息日志格式，使用JSON格式化输出

---
**最后更新**: 2025-11-25
**优化人**: Claude Code
