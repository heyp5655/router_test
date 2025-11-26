# 测试结果Excel导出功能说明

## 功能概述
实现了路由器自动化测试平台的Excel格式测试报告导出功能，支持带格式化的Excel文件导出。

## 功能特性

### 1. Excel表格结构
按照用例步骤.xlsx中"测试结果"表的格式，包含以下列：
- **ID**: 序号
- **测试项**: 测试用例的分类（如：功能用例/网络/接口/蜂窝网络）
- **测试用例名称**: 具体的测试用例名称
- **测试结果**: PASS/FAIL/ERROR
- **备注**: 失败或错误时显示详细原因

### 2. 格式化样式

#### 表头样式
- 蓝色背景 (RGB: 4472C4)
- 白色字体
- 居中对齐
- 加粗
- 带边框

#### 测试结果单元格颜色
- **PASS** (通过):
  - 绿色背景 (RGB: C6EFCE)
  - 深绿色字体 (RGB: 006100)

- **FAIL** (失败):
  - 红色背景 (RGB: FFC7CE)
  - 深红色字体 (RGB: 9C0006)

- **ERROR** (错误):
  - 黄色背景 (RGB: FFEB9C)
  - 棕色字体 (RGB: 9C5700)

#### 备注栏
- 当测试结果为FAIL或ERROR时，自动填充失败原因
- 当测试结果为PASS时，备注栏为空

### 3. 测试汇总信息
在表格下方显示测试汇总信息：
- 路由器IP
- 路由器型号
- 测试时间
- 总用例数
- 通过数
- 失败数
- 错误数
- 总耗时
- 总体结果

## 文件结构

### 新增文件
1. **utils/excel_exporter.py** - Excel导出工具类
   - `ExcelExporter` 类：负责生成带格式的Excel报告
   - `export_test_results()` 方法：核心导出方法

### 修改文件
1. **app.py**
   - 导入 `send_file` 和 `ExcelExporter`
   - 修改 `/api/export-report` 路由，实现真正的Excel文件生成和下载

2. **core/test_runner.py**
   - `_run_single_test()` 方法中添加 `category` 字段到返回结果
   - 确保测试结果包含测试项信息

3. **templates/index.html**
   - 修改 `exportReport()` 方法
   - 改为调用后端API生成Excel文件
   - 自动下载生成的Excel文件

## 使用方法

### 通过Web界面导出
1. 运行测试用例
2. 等待测试完成
3. 点击"导出报告"按钮
4. 浏览器会自动下载Excel文件，文件名格式：`测试报告_YYYYMMDD_HHMMSS.xlsx`

### 文件保存位置
- 服务器端：`reports/` 目录
- 客户端：浏览器默认下载目录

## 技术实现

### 后端 (Python)
- 使用 `openpyxl` 库生成Excel文件
- 使用 `PatternFill` 设置单元格背景色
- 使用 `Font` 设置字体颜色和样式
- 使用 `Border` 添加边框
- 使用 `Alignment` 设置对齐方式

### 前端 (JavaScript)
- 使用 `fetch` API调用后端接口
- 接收 `blob` 格式的响应
- 使用 `URL.createObjectURL()` 创建下载链接
- 自动触发文件下载

## 测试验证

已通过测试脚本 `test_excel_export.py` 验证：
- ✅ 表头格式正确（蓝色背景，白色字体）
- ✅ PASS单元格为绿色背景
- ✅ FAIL单元格为红色背景
- ✅ ERROR单元格为黄色背景
- ✅ 失败和错误用例的备注栏正确显示失败原因
- ✅ 测试汇总信息完整显示

## 依赖项
- openpyxl (已安装，版本: 3.1.5)
- Flask (已安装)

## 注意事项
1. Excel文件采用UTF-8编码，支持中文显示
2. 文件会保存在服务器的 `reports/` 目录
3. 建议定期清理旧的报告文件
4. 导出功能需要测试完成后才能使用（需要有测试结果）
