import importlib
import importlib.util
from importlib import reload
import inspect
import pkgutil
import time
import traceback
import os
import sys
import io
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from models.test_config import TestConfig, TestRequest, TestMode, RouterConfig


class StdoutCapture:
    """捕获stdout输出并同时写入日志"""

    def __init__(self, log_func, original_stdout):
        self.log_func = log_func
        self.original_stdout = original_stdout
        self.buffer = ""

    def write(self, text):
        # 写入原始stdout
        if self.original_stdout:
            self.original_stdout.write(text)
            self.original_stdout.flush()

        # 累积文本
        self.buffer += text

        # 按行处理
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            if line.strip():  # 只记录非空行
                # 避免重复记录已经格式化的日志行
                if not line.startswith('['):
                    self.log_func(line, "OUTPUT")

    def flush(self):
        if self.original_stdout:
            self.original_stdout.flush()
        # 处理剩余的buffer
        if self.buffer.strip():
            if not self.buffer.startswith('['):
                self.log_func(self.buffer.strip(), "OUTPUT")
            self.buffer = ""


class TestRunner:
    """测试执行器 - 支持实时日志和文件保存"""

    def __init__(self):
        print("初始化 TestRunner")

        # 首先初始化所有必要的属性
        self.log_buffer = []  # 先初始化 log_buffer
        self.current_log_file = None
        self.log_callback = None
        self.is_test_running = False

        # 确保日志目录存在
        self.log_dir = "E:\\GIT\\ROUTER_TEST\\logs"
        os.makedirs(self.log_dir, exist_ok=True)

        # 现在可以安全地调用 _log 方法了
        self._log("开始初始化 TestRunner")

        self.test_results = []
        self.last_run_summary = {
            "overall_result": "NOT_RUN",
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "error": 0,
                "duration": 0
            },
            "details": []
        }

        # 新增：保存最后一次测试请求和失败用例
        self.last_test_request = None  # 保存最后一次测试请求
        self.failed_cases = []  # 保存失败的测试用例类名列表

        # 新增：记录test_cases目录的最后扫描时间
        self._last_scan_time = 0
        self._test_cases_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_cases')

        self._log("开始发现测试用例")
        self.available_cases = self._discover_test_cases()
        self._update_scan_time()
        self._log(f"TestRunner 初始化完成，发现 {len(self.available_cases)} 个测试用例")

    def set_log_callback(self, callback: Optional[Callable]):
        """设置日志回调函数，用于实时推送到前端"""
        self.log_callback = callback
        self._log(f"日志回调函数已{'设置' if callback else '清除'}")

    def _log(self, message: str, level="INFO"):
        """统一的日志记录方法"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        formatted_message = f"[{timestamp}] [{level}] {message}"

        # 输出到控制台（处理emoji编码问题）
        try:
            print(formatted_message)
        except UnicodeEncodeError:
            # Windows控制台GBK编码不支持emoji，替换为文本
            safe_message = formatted_message.encode('gbk', errors='replace').decode('gbk')
            print(safe_message)

        # 保存到缓冲区
        self.log_buffer.append(formatted_message)

        # 写入日志文件
        if self.current_log_file:
            try:
                with open(self.current_log_file, 'a', encoding='utf-8') as f:
                    f.write(formatted_message + '\n')
            except Exception as e:
                print(f"写入日志文件失败: {e}")

        # 实时推送到前端
        if self.log_callback and self.is_test_running:
            try:
                log_data = {
                    'timestamp': timestamp,
                    'level': level,
                    'message': message,
                    'full_message': formatted_message
                }
                self.log_callback(log_data)
            except Exception as e:
                print(f"日志回调失败: {e}")

    def _send_progress(self, progress: int, completed: int, total: int):
        """发送进度更新到前端"""
        if self.log_callback and self.is_test_running:
            try:
                progress_data = {
                    'type': 'progress',
                    'progress': progress,
                    'completed': completed,
                    'total': total
                }
                self.log_callback(progress_data)
                # 添加调试日志
                print(f"[DEBUG] 发送进度: {completed}/{total} ({progress}%)", flush=True)
            except Exception as e:
                print(f"进度回调失败: {e}")
        else:
            # 添加调试日志
            print(f"[DEBUG] 进度未发送 - log_callback={self.log_callback is not None}, is_test_running={self.is_test_running}", flush=True)

    def _clear_python_cache(self):
        """清除测试用例的Python缓存"""
        import shutil
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            test_cases_dir = os.path.join(project_root, 'test_cases')

            cache_cleared = False
            # 清除test_cases目录下的__pycache__
            for root, dirs, files in os.walk(test_cases_dir):
                if '__pycache__' in dirs:
                    cache_dir = os.path.join(root, '__pycache__')
                    try:
                        shutil.rmtree(cache_dir)
                        cache_cleared = True
                    except Exception:
                        pass

                # 清除.pyc和.pyo文件
                for file in files:
                    if file.endswith(('.pyc', '.pyo')):
                        try:
                            os.remove(os.path.join(root, file))
                            cache_cleared = True
                        except Exception:
                            pass

            if cache_cleared:
                self._log("✅ 测试用例缓存已自动清除")
        except Exception as e:
            self._log(f"⚠️  清除测试用例缓存时出错: {e}", "WARNING")

    def _start_logging(self, test_request: TestRequest):
        """开始记录日志"""
        self.is_test_running = True
        self.log_buffer = []  # 清空缓冲区

        # 创建日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_run_{timestamp}.log"
        self.current_log_file = os.path.join(self.log_dir, filename)

        self._log(f"开始测试执行 - 模式: {test_request.test_mode.value}")
        self._log(f"路由器: {test_request.router_config.router_ip}")
        self._log(f"日志文件: {self.current_log_file}")

    def _stop_logging(self):
        """停止记录日志"""
        self.is_test_running = False
        if self.current_log_file:
            self._log(f"测试执行完成，日志已保存到: {self.current_log_file}")
        self.current_log_file = None


    def get_recent_logs(self, count=100):
        """获取最近的日志"""
        return self.log_buffer[-count:] if self.log_buffer else []

    def get_log_file_path(self):
        """获取当前日志文件路径"""
        return self.current_log_file

    @contextmanager
    def _capture_stdout(self):
        """捕获stdout输出的上下文管理器"""
        original_stdout = sys.stdout
        capture = StdoutCapture(self._log, original_stdout)
        sys.stdout = capture
        try:
            yield
        finally:
            capture.flush()  # 确保所有缓冲内容都被处理
            sys.stdout = original_stdout

    def _discover_test_cases(self) -> List[Dict[str, Any]]:
        """发现所有可用的测试用例"""
        self._log("=== 开始发现测试用例 ===")
        tests = []

        # 定义要扫描的测试包
        test_packages = [
            'test_cases.wan_tests',
            'test_cases.cellular_tests',
            'test_cases.mqtt_test',               # MQTT测试
            'test_cases.industrial_tests',        # 工业协议测试
            'test_cases.app_tests',
            'test_cases.stability',               # 稳定性测试
            'test_cases.port_conflict_tests'      # 端口冲突检测测试
        ]

        for package_name in test_packages:
            try:
                self._log(f"尝试导入测试包: {package_name}")
                package = importlib.import_module(package_name)
                self._log(f"✅ 成功导入包: {package_name}")
                package_tests = self._find_tests_in_package(package, package_name)
                tests.extend(package_tests)
                self._log(f"在包 {package_name} 中找到 {len(package_tests)} 个测试用例")
            except ImportError as e:
                self._log(f"❌ 无法导入测试包 {package_name}: {e}", "ERROR")
            except Exception as e:
                self._log(f"❌ 导入测试包 {package_name} 时发生错误: {e}", "ERROR")

        self._log(f"总共发现 {len(tests)} 个测试用例")
        return tests

    def _find_tests_in_package(self, package, package_name: str) -> List[Dict[str, Any]]:
        """在指定包中查找测试用例"""
        tests = []

        # 遍历包中的所有模块
        for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
            if is_pkg:
                continue  # 跳过子包

            full_module_name = f"{package_name}.{module_name}"
            try:
                module = importlib.import_module(full_module_name)

                # 查找模块中的测试类
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (self._is_test_class(obj) and
                            name != 'BaseTest'):  # 排除基类

                        # 创建一个简单的配置来获取属性值
                        dummy_config = TestConfig(
                            router_config=RouterConfig(
                                router_ip="192.168.1.1",
                                username="admin",
                                password="admin",
                                model="UR35"
                            ),
                            test_mode=TestMode.REGRESSION
                        )

                        try:
                            test_instance = obj(dummy_config)
                            test_name = test_instance.test_name
                            description = getattr(test_instance, 'description', '')
                            is_regression = getattr(test_instance, 'is_regression', False)
                            category = getattr(test_instance, 'category',
                                               self._infer_category(package_name, module_name))

                            test_info = {
                                'name': test_name,  # 使用实际的测试名称
                                'class_name': name,
                                'module_path': full_module_name,
                                'is_regression': is_regression,
                                'description': description,
                                'category': category
                            }
                            tests.append(test_info)
                            self._log(f"发现测试用例: {test_info['name']} (类名: {name}, 分类: {category})")

                        except Exception as e:
                            self._log(f"警告: 创建测试实例失败 {name}, 使用默认值: {e}", "WARNING")
                            # 如果创建实例失败，使用类名作为后备
                            test_info = {
                                'name': name,
                                'class_name': name,
                                'module_path': full_module_name,
                                'is_regression': False,
                                'description': '',
                                'category': self._infer_category(package_name, module_name)
                            }
                            tests.append(test_info)
                            self._log(
                                f"发现测试用例: {test_info['name']} (类名: {name}, 分类: {test_info['category']})")

            except Exception as e:
                self._log(f"警告: 导入模块 {full_module_name} 失败: {e}", "WARNING")

        return tests

    def _infer_category(self, package_name: str, module_name: str) -> str:
        """根据包名和模块名推断分类"""
        # 这里可以根据您的实际包结构来调整分类逻辑
        if 'wan_tests' in package_name:
            if 'pppoe' in module_name.lower():
                return '功能用例/网络/接口/广域网'
            elif 'static' in module_name.lower():
                return '功能用例/网络/接口/广域网'
            else:
                return '功能用例/网络/接口/广域网'
        elif 'cellular_tests' in package_name:
            if 'network' in module_name.lower():
                return '功能用例/网络/接口/蜂窝网络'
            else:
                return '功能用例/网络/接口/蜂窝网络'
        elif 'port_conflict' in package_name or 'port_conflict' in module_name.lower():
            # 端口冲突检测测试用例
            return '功能用例/端口冲突检测'
        elif 'app_tests' in package_name:
            if 'python' in module_name.lower():
                return '功能用例/APP/python'
            else:
                return '功能用例/APP'
        elif 'stability' in package_name:
            return '稳定性用例'
        else:
            return '功能用例/网络'

    def _is_test_class(self, obj) -> bool:
        """判断一个类是否是测试类"""
        return (hasattr(obj, 'test_name') and
                hasattr(obj, 'execute') and
                hasattr(obj, 'setup'))

    def get_available_cases(self, regression_only: bool = False) -> List[Dict[str, Any]]:
        """获取可用测试用例列表

        会自动检测test_cases目录是否有更新，如有则自动刷新测试用例列表
        """
        # 自动检测并刷新（如果需要）
        self._check_and_refresh_if_needed()

        if regression_only:
            return [case for case in self.available_cases if case.get('is_regression', False)]
        return self.available_cases

    def run_tests(self, test_request: TestRequest) -> Dict[str, Any]:
        """执行测试"""
        # 开始记录日志
        self._start_logging(test_request)

        try:
            return self._run_tests_internal(test_request)
        except Exception as e:
            self._log(f"测试执行过程中发生未预期的错误: {str(e)}", "ERROR")
            self._log(traceback.format_exc(), "ERROR")
            raise
        finally:
            # 停止记录日志
            self._stop_logging()

    def _run_tests_internal(self, test_request: TestRequest) -> Dict[str, Any]:
        """内部测试执行方法"""
        # 在执行测试前自动清除Python缓存
        self._clear_python_cache()

        self._log("=== run_tests 方法开始 ===")
        self._log(f"测试模式: {test_request.test_mode.value}")
        self._log(f"路由器配置: {test_request.router_config}")
        self._log(f"超时设置: {test_request.timeout}")
        self._log(f"恢复默认: {test_request.restore_default}")
        self._log(f"选中的用例: {test_request.selected_cases}")
        self._log(f"可用的测试用例总数: {len(self.available_cases)}")

        for i, case in enumerate(self.available_cases):
            self._log(f"可用用例 {i}: {case['name']} (类名: {case['class_name']})")

        start_time = time.time()

        # 根据测试模式获取要执行的测试用例
        if test_request.test_mode == TestMode.SPECIFIC:
            self._log("=== 指定测试模式 ===")
            # 同时支持按名称和类名匹配
            cases_to_run = []
            for case in self.available_cases:
                self._log(f"检查用例: {case['name']} (类名: {case['class_name']})")
                if case['name'] in test_request.selected_cases or case['class_name'] in test_request.selected_cases:
                    cases_to_run.append(case)
                    self._log(f"✅ 匹配到用例: {case['name']} (类名: {case['class_name']})")

            self._log(f"选中的用例: {test_request.selected_cases}")
            self._log(f"匹配到的用例: {[case['name'] for case in cases_to_run]}")
        elif test_request.test_mode == TestMode.REGRESSION:
            self._log("=== 回归测试模式 ===")
            cases_to_run = [case for case in self.available_cases
                            if case.get('is_regression', False)]
            self._log(f"回归测试用例: {[case['name'] for case in cases_to_run]}")
        elif test_request.test_mode == TestMode.ALL:
            self._log("=== 全部测试模式 ===")
            cases_to_run = self.available_cases
            self._log(f"全部测试用例: {[case['name'] for case in cases_to_run]}")
        else:
            self._log("=== 其他测试模式 ===")
            cases_to_run = self.available_cases
            self._log(f"其他模式用例: {[case['name'] for case in cases_to_run]}")

        self._log(f"将要执行 {len(cases_to_run)} 个测试用例")

        # 发送初始进度
        self._send_progress(0, 0, len(cases_to_run))

        if len(cases_to_run) == 0:
            self._log("❌ 没有找到要执行的测试用例！", "ERROR")
            return {
                "overall_result": "ERROR",
                "summary": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "error": 1,
                    "duration": 0
                },
                "details": [{
                    'test_name': 'No Tests',
                    'status': 'ERROR',
                    'message': '没有找到要执行的测试用例',
                    'duration': 0
                }]
            }

        results = []
        passed = 0
        failed = 0
        error = 0

        # 逐个执行测试用例 - 增强容错处理
        for i, case_info in enumerate(cases_to_run):
            self._log(f"\n{'=' * 50}")
            self._log(f"执行第 {i + 1}/{len(cases_to_run)} 个用例: {case_info['name']}")
            self._log(f"{'=' * 50}")

            try:
                result = self._run_single_test(case_info, test_request)
                results.append(result)

                if result['status'] == 'PASS':
                    passed += 1
                    self._log(f"用例 {case_info['name']} 执行成功")
                elif result['status'] == 'FAIL':
                    failed += 1
                    self._log(f"用例 {case_info['name']} 执行失败: {result['message']}")
                else:
                    error += 1
                    self._log(f"用例 {case_info['name']} 执行错误: {result['message']}")

                # 发送进度更新
                progress = round((i + 1) / len(cases_to_run) * 100)
                self._send_progress(progress, i + 1, len(cases_to_run))

            except Exception as e:
                self._log(f"执行测试 {case_info['name']} 时发生未捕获的异常: {str(e)}", "ERROR")
                self._log(traceback.format_exc(), "ERROR")
                error_result = {
                    'test_name': case_info['name'],
                    'status': 'ERROR',
                    'message': f"测试执行过程中发生未捕获的异常: {str(e)}",
                    'duration': 0,
                    'stack_trace': traceback.format_exc()
                }
                results.append(error_result)
                error += 1

                # 发送进度更新（即使出错也更新进度）
                progress = round((i + 1) / len(cases_to_run) * 100)
                self._send_progress(progress, i + 1, len(cases_to_run))

                # 即使发生异常，也继续执行下一个测试用例
                self._log(f"继续执行下一个测试用例...")

        total_duration = round(time.time() - start_time, 2)
        overall_result = "PASS" if failed == 0 and error == 0 else "FAIL"

        # 构建完整的结果对象
        final_result = {
            "overall_result": overall_result,
            "summary": {
                "total": len(cases_to_run),
                "passed": passed,
                "failed": failed,
                "error": error,
                "duration": total_duration
            },
            "details": results,
            "log_file": self.current_log_file  # 包含日志文件路径
        }

        # 更新实例变量
        self.test_results = results
        self.last_run_summary = final_result

        # 新增：保存最后一次测试请求
        self.last_test_request = test_request
        self._log(f"已保存最后一次测试请求配置")

        # 新增：保存失败的测试用例类名
        self.failed_cases = []
        for result in results:
            if result['status'] in ['FAIL', 'ERROR']:
                # 找到对应的用例信息
                for case in cases_to_run:
                    if case['name'] == result['test_name']:
                        self.failed_cases.append(case['class_name'])
                        break
        self._log(f"失败用例列表: {self.failed_cases}")

        self._log(f"\n{'=' * 60}")
        self._log(f"测试执行完成")
        self._log(f"{'=' * 60}")
        self._log(f"总计: {len(cases_to_run)}, 通过: {passed}, 失败: {failed}, 错误: {error}, 耗时: {total_duration}秒")
        self._log(f"总体结果: {overall_result}")
        if self.current_log_file:
            self._log(f"详细日志已保存到: {self.current_log_file}")

        return final_result

    def _run_single_test(self, case_info: Dict[str, Any], test_request: TestRequest) -> Dict[str, Any]:
        """执行单个测试用例"""
        self._log(f"=== 开始执行测试: {case_info['name']} ===")
        self._log(f"测试类: {case_info['class_name']}")
        self._log(f"模块路径: {case_info['module_path']}")
        start_time = time.time()

        try:
            # 动态导入并实例化测试类
            self._log(f"1. 导入模块: {case_info['module_path']}")

            # 检查模块是否已导入，如果是则重新加载
            if case_info['module_path'] in sys.modules:
                self._log(f"  模块已存在，重新加载以获取最新代码...")
                module = sys.modules[case_info['module_path']]
                module = reload(module)
            else:
                module = importlib.import_module(case_info['module_path'])

            self._log(f"✅ 模块导入成功")

            self._log(f"2. 获取测试类: {case_info['class_name']}")
            test_class = getattr(module, case_info['class_name'])
            self._log(f"✅ 测试类获取成功: {test_class}")

            # 创建配置
            self._log(f"3. 创建测试配置...")
            config = TestConfig(
                router_config=test_request.router_config,
                test_mode=test_request.test_mode,
                timeout=test_request.timeout,
                restore_default=test_request.restore_default
            )
            self._log(f"✅ 配置创建成功: {config}")

            # 创建测试实例并执行
            self._log(f"4. 创建测试实例...")
            test_instance = test_class(config)
            self._log(f"✅ 测试实例创建成功: {test_instance}")

            # 获取实际的测试名称（从实例中获取，而不是从case_info）
            actual_test_name = getattr(test_instance, 'test_name', case_info['name'])
            self._log(f"✅ 测试名称: {actual_test_name}")

            try:
                # 使用stdout捕获来记录所有print输出
                with self._capture_stdout():
                    self._log(f"5. 执行setup方法...")
                    test_instance.setup()
                    self._log(f"setup完成")

                    self._log(f"6. 执行execute方法...")
                    test_instance.execute()
                    self._log(f"execute完成")

                status = 'PASS'
                message = '测试通过'

            except AssertionError as e:
                status = 'FAIL'
                message = f"断言失败: {str(e)}"
                self._log(f"测试 {actual_test_name} 断言失败: {str(e)}", "ERROR")
                self._log(f"断言失败堆栈: {traceback.format_exc()}", "ERROR")
            except Exception as e:
                status = 'FAIL'
                message = f"测试执行失败: {str(e)}"
                self._log(f"测试 {actual_test_name} 执行失败: {str(e)}", "ERROR")
                self._log(f"执行失败堆栈: {traceback.format_exc()}", "ERROR")
            finally:
                try:
                    # cleanup也需要捕获stdout
                    with self._capture_stdout():
                        self._log(f"7. 执行cleanup方法...")
                        test_instance.cleanup()
                        self._log(f"cleanup完成")
                except Exception as e:
                    self._log(f"测试清理过程中出错: {str(e)}", "WARNING")

                # 额外的安全机制：即使cleanup失败，也要尝试关闭浏览器
                try:
                    if hasattr(test_instance, 'router_client') and test_instance.router_client:
                        if hasattr(test_instance.router_client, 'driver') and test_instance.router_client.driver:
                            self._log("额外安全机制：强制关闭浏览器...")
                            test_instance.router_client.driver.quit()
                            test_instance.router_client.driver = None
                            self._log("✅ 浏览器已强制关闭")
                except Exception as e:
                    self._log(f"⚠️ 强制关闭浏览器失败: {str(e)}", "WARNING")

            duration = round(time.time() - start_time, 2)

            result = {
                'test_name': actual_test_name,  # 使用实际的测试名称
                'category': case_info.get('category', ''),  # 测试项
                'status': status,
                'message': message,
                'duration': duration
            }

            self._log(f"测试 {actual_test_name} 完成，结果: {status}, 耗时: {duration}秒")
            return result

        except Exception as e:
            duration = round(time.time() - start_time, 2)
            actual_test_name = case_info.get('name', '未知测试')
            self._log(f"❌ 测试 {actual_test_name} 初始化错误: {str(e)}", "ERROR")
            self._log(f"初始化错误堆栈: {traceback.format_exc()}", "ERROR")

            # 初始化错误时也要尝试清理浏览器
            try:
                if 'test_instance' in locals():
                    if hasattr(test_instance, 'router_client') and test_instance.router_client:
                        if hasattr(test_instance.router_client, 'driver') and test_instance.router_client.driver:
                            self._log("初始化错误：尝试关闭浏览器...")
                            test_instance.router_client.driver.quit()
                            test_instance.router_client.driver = None
                            self._log("✅ 浏览器已关闭")
            except Exception as cleanup_error:
                self._log(f"⚠️ 初始化错误后关闭浏览器失败: {str(cleanup_error)}", "WARNING")

            error_result = {
                'test_name': actual_test_name,
                'category': case_info.get('category', ''),  # 测试项
                'status': 'ERROR',
                'message': f"测试初始化错误: {str(e)}",
                'duration': duration
            }
            return error_result

    def refresh_test_cases(self):
        """重新扫描测试用例"""
        self._log("=== 重新扫描测试用例 ===")
        old_count = len(self.available_cases)

        # 重新发现测试用例
        self.available_cases = self._discover_test_cases()
        self._update_scan_time()

        new_count = len(self.available_cases)

        self._log(f"重新扫描完成 - 原有 {old_count} 个用例，现在 {new_count} 个用例")

        if new_count > old_count:
            self._log(f"✅ 发现 {new_count - old_count} 个新测试用例")
        elif new_count < old_count:
            self._log(f"⚠️ 减少了 {old_count - new_count} 个测试用例")
        else:
            self._log("✅ 测试用例数量没有变化")

        return self.available_cases

    def _update_scan_time(self):
        """更新最后扫描时间为test_cases目录的最新修改时间"""
        try:
            self._last_scan_time = self._get_test_cases_dir_mtime()
        except Exception as e:
            self._log(f"⚠️ 更新扫描时间失败: {e}", "WARNING")
            self._last_scan_time = time.time()

    def _get_test_cases_dir_mtime(self) -> float:
        """获取test_cases目录及其子目录中所有.py文件的最新修改时间"""
        max_mtime = 0
        try:
            for root, dirs, files in os.walk(self._test_cases_dir):
                for file in files:
                    if file.endswith('.py') and not file.startswith('__'):
                        file_path = os.path.join(root, file)
                        try:
                            mtime = os.path.getmtime(file_path)
                            if mtime > max_mtime:
                                max_mtime = mtime
                        except:
                            continue
        except Exception as e:
            self._log(f"⚠️ 获取目录修改时间失败: {e}", "WARNING")
        return max_mtime if max_mtime > 0 else time.time()

    def _check_and_refresh_if_needed(self) -> bool:
        """检查test_cases目录是否有更新，如有则自动刷新测试用例

        Returns:
            bool: 是否进行了刷新
        """
        try:
            current_mtime = self._get_test_cases_dir_mtime()
            if current_mtime > self._last_scan_time:
                self._log(f"🔄 检测到测试用例文件变化，自动刷新...", "INFO")
                old_count = len(self.available_cases)
                self.available_cases = self._discover_test_cases()
                self._update_scan_time()
                new_count = len(self.available_cases)

                if new_count != old_count:
                    self._log(f"✅ 自动刷新完成：{old_count} → {new_count} 个测试用例", "INFO")
                else:
                    self._log(f"✅ 自动刷新完成：测试用例数量未变化 ({new_count}个)", "INFO")
                return True
        except Exception as e:
            self._log(f"⚠️ 自动刷新检查失败: {e}", "WARNING")
        return False

    def get_test_results(self) -> List[Dict[str, Any]]:
        """获取测试结果"""
        return self.test_results

    def get_last_run_summary(self) -> Dict[str, Any]:
        """获取最后一次运行的汇总结果"""
        return self.last_run_summary

    def get_test_summary(self) -> Dict[str, Any]:
        """获取测试汇总信息（兼容性方法）"""
        return self.last_run_summary

    def get_failed_cases(self) -> List[str]:
        """获取失败的测试用例类名列表

        Returns:
            List[str]: 失败用例的类名列表
        """
        return self.failed_cases

    def get_last_test_request(self) -> Optional[TestRequest]:
        """获取最后一次测试请求

        Returns:
            Optional[TestRequest]: 最后一次测试请求，如果没有则返回None
        """
        return self.last_test_request

    def rerun_failed_tests(self) -> Dict[str, Any]:
        """重新运行失败的测试用例

        Returns:
            Dict[str, Any]: 测试结果
        """
        if not self.failed_cases:
            self._log("没有失败的测试用例需要重跑", "WARNING")
            return {
                "overall_result": "ERROR",
                "summary": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "error": 1,
                    "duration": 0
                },
                "details": [{
                    'test_name': 'No Failed Tests',
                    'status': 'ERROR',
                    'message': '没有失败的测试用例',
                    'duration': 0
                }]
            }

        if not self.last_test_request:
            self._log("没有找到上次测试的配置", "ERROR")
            return {
                "overall_result": "ERROR",
                "summary": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "error": 1,
                    "duration": 0
                },
                "details": [{
                    'test_name': 'No Last Request',
                    'status': 'ERROR',
                    'message': '没有找到上次测试的配置',
                    'duration': 0
                }]
            }

        self._log(f"重新运行 {len(self.failed_cases)} 个失败的测试用例")
        self._log(f"失败用例列表: {self.failed_cases}")

        # 创建新的测试请求，使用失败用例的类名
        rerun_request = TestRequest(
            router_config=self.last_test_request.router_config,
            test_mode=TestMode.SPECIFIC,
            selected_cases=self.failed_cases,  # 使用失败用例的类名
            timeout=self.last_test_request.timeout,
            restore_default=self.last_test_request.restore_default
        )

        return self.run_tests(rerun_request)

    def rerun_last_test(self) -> Dict[str, Any]:
        """重新运行上次的测试（完整重跑）

        Returns:
            Dict[str, Any]: 测试结果
        """
        if not self.last_test_request:
            self._log("没有找到上次测试的配置", "ERROR")
            return {
                "overall_result": "ERROR",
                "summary": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "error": 1,
                    "duration": 0
                },
                "details": [{
                    'test_name': 'No Last Request',
                    'status': 'ERROR',
                    'message': '没有找到上次测试的配置',
                    'duration': 0
                }]
            }

        self._log(f"重新运行上次测试")
        self._log(f"测试模式: {self.last_test_request.test_mode.value}")
        self._log(f"选中的用例: {self.last_test_request.selected_cases}")

        return self.run_tests(self.last_test_request)