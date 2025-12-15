# PythonModuleCheckTest heredoc语法错误修复

## 修复日期
2025-12-12

## 问题描述

### 错误现象
```
File "/tmp/selftest.py", line 57, in <module>
    SELFTEST_EOF
NameError: name 'SELFTEST_EOF' is not defined
```

### 问题根源
在 `test_cases/app_tests/python_module_check_test.py:503` 中，heredoc结束符格式不正确：

**修复前的代码**:
```python
# 转义脚本内容中的特殊字符
script_content = self.SELFTEST_SCRIPT.replace('\\', '\\\\').replace('$', '\\$').replace('`', '\\`')

# 创建上传命令
upload_cmd = f"cat > {script_path} << 'SELFTEST_EOF'\n{self.SELFTEST_SCRIPT}\nSELFTEST_EOF"
```

**问题**:
1. heredoc结束符 `SELFTEST_EOF` 后面缺少换行符
2. 结束符没有真正单独成一行
3. 结果导致 `SELFTEST_EOF` 被当作Python代码的一部分

## 修复方案

### 修改内容
**修复后的代码** (第499-501行):
```python
# 创建上传命令 (heredoc格式，确保结束符单独成一行)
# 注意：SELFTEST_EOF 必须单独成一行，前后不能有任何字符
upload_cmd = f"cat > {script_path} << 'SELFTEST_EOF'\n{self.SELFTEST_SCRIPT}\nSELFTEST_EOF\n"
```

### 关键改动
1. ✅ **移除了未使用的代码**: 删除了第500行的 `script_content` 变量（从未使用）
2. ✅ **修复heredoc结束符**: 在 `SELFTEST_EOF` 后添加 `\n`，确保结束符单独成一行
3. ✅ **添加注释**: 说明heredoc格式要求

### 正确的heredoc格式
```bash
cat > /tmp/selftest.py << 'SELFTEST_EOF'
# selftest.py
import sys
print('Hello')

SELFTEST_EOF

```

**关键点**:
- 结束符必须单独成一行
- 结束符前后不能有任何字符（包括空格）
- 结束符后需要换行符（保证执行完整性）

## 验证结果

### 修复后的heredoc命令结构
```
第1行: cat > /tmp/test.py << 'SELFTEST_EOF'
第2-N行: [脚本内容]
第N+1行: [空行]
第N+2行: SELFTEST_EOF
```

✅ 结束符正确单独成一行，heredoc语法正确

## 影响范围

**修复的测试用例**: `PythonModuleCheckTest` (python3.9核心库和拓展库自动化验证)

**相关测试**: 可能间接影响其他Python SDK测试用例的执行：
- PahoMqttLibraryTest
- PymodbusLibraryTest
- PyserialLibraryTest

## 测试建议

1. 重新运行 `PythonModuleCheckTest` 验证修复
2. 检查SSH连接是否正常（SSH失败会回退到串口方式）
3. 如果仍然失败，检查串口连接配置

## 后续改进建议

如果heredoc方式仍然不稳定，可以考虑：

### 方案2：使用base64编码（更可靠）
```python
import base64
script_b64 = base64.b64encode(self.SELFTEST_SCRIPT.encode()).decode()
upload_cmd = f"echo '{script_b64}' | base64 -d > {script_path}"
```

### 方案3：使用printf（避免换行问题）
```python
escaped_script = self.SELFTEST_SCRIPT.replace("'", "'\\''")
upload_cmd = f"printf '%s' '{escaped_script}' > {script_path}"
```

---
**修复人员**: Claude
**文档版本**: v1.0
