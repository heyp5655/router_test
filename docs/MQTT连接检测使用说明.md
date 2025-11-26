# MQTT连接状态检测 - 使用说明

## 概述
本文档说明如何在测试用例中正确使用MQTT连接状态检测功能。

## 问题背景
在MQTT测试中，需要等待路由器连接到MQTT服务器。之前的实现存在以下问题：
1. 每次检查都刷新页面，效率低下
2. 只支持中文"已连接"状态
3. 没有异常容错机制
4. 页面刷新较慢时容易检测失败

## 改进后的实现

### 核心方法
在 `core/router_client.py` 中添加了通用方法：

```python
def wait_for_mqtt_connection(self,
                             status_xpath: str = '//*[@id="mqtt_list"]/div[2]/div[1]/div[4]/span',
                             max_wait: int = 300,
                             check_interval: int = 5) -> bool:
    """
    等待MQTT连接建立，兼容中英文状态

    Args:
        status_xpath: MQTT状态元素的XPath
        max_wait: 最大等待时间(秒)
        check_interval: 检查间隔(秒)

    Returns:
        bool: 连接是否成功
    """
```

### 功能特性

#### 1. 支持中英文状态检测
自动识别以下状态关键词：

**连接成功**:
- 中文: `已连接`, `连接成功`
- 英文: `connected`, `connect success`
- 大小写不敏感

**连接失败**:
- 中文: `失败`, `错误`, `断开`
- 英文: `failed`, `error`, `disconnect`

#### 2. 智能刷新策略
- 检查间隔: 5秒
- 刷新频率: 每3次检查才刷新一次页面
- 首次检查不刷新（刚配置完成）
- 减少不必要的页面刷新，提高检测效率

#### 3. 异常容错机制
- 捕获检查过程中的异常
- 异常发生时继续重试，不中断检测
- 输出详细的错误信息便于调试

#### 4. 详细的进度输出
```
  当前MQTT状态: Connected (第1次检查)
  当前MQTT状态: Connected (第2次检查)
  ✅ MQTT已连接（耗时 10 秒，检查 2 次）
```

## 使用示例

### 在测试用例中使用

```python
from test_cases.base_test import BaseTest

class MyMqttTest(BaseTest):
    def execute(self):
        # ... 配置MQTT客户端 ...

        # 等待连接建立
        if not self.router_client.wait_for_mqtt_connection(
            status_xpath='//*[@id="mqtt_list"]/div[2]/div[1]/div[4]/span',
            max_wait=300,      # 最多等待300秒
            check_interval=5   # 每5秒检查一次
        ):
            print("MQTT连接失败")
            return False

        print("MQTT连接成功，继续测试...")
        # ... 后续测试步骤 ...
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `status_xpath` | str | `//*[@id="mqtt_list"]/div[2]/div[1]/div[4]/span` | MQTT状态元素的XPath |
| `max_wait` | int | 300 | 最大等待时间（秒） |
| `check_interval` | int | 5 | 检查间隔（秒） |

### 不同场景的XPath

根据路由器Web页面的不同，状态元素的XPath可能不同：

```python
# 场景1: MQTT列表第一个连接
status_xpath = '//*[@id="mqtt_list"]/div[2]/div[1]/div[4]/span'

# 场景2: MQTT列表第二个连接
status_xpath = '//*[@id="mqtt_list"]/div[2]/div[2]/div[4]/span'

# 场景3: 自定义位置
status_xpath = '//*[@id="your_custom_xpath"]'
```

## 最佳实践

### 1. 合理设置超时时间
```python
# MQTT服务器在本地或内网
self.router_client.wait_for_mqtt_connection(max_wait=60)

# MQTT服务器在公网，网络较慢
self.router_client.wait_for_mqtt_connection(max_wait=300)
```

### 2. 调整检查间隔
```python
# 快速检查（适合开发调试）
self.router_client.wait_for_mqtt_connection(check_interval=3)

# 正常检查（默认，推荐）
self.router_client.wait_for_mqtt_connection(check_interval=5)

# 慢速检查（网络很慢时）
self.router_client.wait_for_mqtt_connection(check_interval=10)
```

### 3. 错误处理
```python
try:
    if not self.router_client.wait_for_mqtt_connection():
        # 连接失败，执行清理
        self.cleanup()
        raise Exception("MQTT连接失败")

    # 连接成功，继续测试
    self._run_mqtt_tests()

except Exception as e:
    print(f"测试失败: {e}")
    return False
```

## 性能对比

### 优化前
- 每次检查: 刷新页面(3秒) + 等待(3秒) = 6秒
- 10次检查: 60秒
- 仅支持中文

### 优化后
- 首次检查: 0秒（不刷新）
- 后续检查: 每3次刷新一次
  - 不刷新时: 5秒
  - 刷新时: 2秒(刷新) + 5秒 = 7秒
- 10次检查: 约 47秒
- 支持中英文

**效率提升约 22%**，同时增强了兼容性和容错性。

## 常见问题

### Q1: 为什么不每次都刷新页面？
**A**: 页面刷新很慢（2-3秒），而MQTT状态通常会自动更新。只在必要时刷新可以大幅提高检测效率。

### Q2: 如何判断需要刷新页面？
**A**: 每3次检查刷新一次页面。这个策略平衡了状态更新的及时性和检测效率。

### Q3: 如果状态一直是"连接中"怎么办？
**A**: 方法会在超时后返回 `False`。"连接中"不属于成功或失败关键词，会持续检查直到超时。

### Q4: 可以用于其他服务的连接检测吗？
**A**: 可以！只需要修改 `status_xpath` 参数，指向目标服务的状态元素即可。

## 相关文件

- `core/router_client.py:2122` - 核心实现方法
- `test_cases/mqtt_test/mqtt_router_command_reboot_test.py:246` - 使用示例
- `scripts/test_mqtt_status_detection.py` - 单元测试

---
**最后更新**: 2025-11-25
