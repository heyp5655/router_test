from flask import Flask, request, jsonify, Response, stream_with_context, session, send_file
import json
import traceback
import sys
import os
import time
import threading
from queue import Queue, Empty

# 设置stdout为unbuffered，避免输出被缓冲
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
else:
    # Python 3.6及更早版本的兼容方式
    import functools
    print = functools.partial(print, flush=True)

# ==================== 管理员权限检测和自动提升 ====================
def is_admin():
    """检查当前是否以管理员权限运行"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """以管理员权限重新启动当前程序"""
    try:
        import ctypes

        # 获取当前Python解释器路径
        python_exe = sys.executable

        # 获取当前脚本路径
        script = os.path.abspath(__file__)

        # 获取命令行参数
        params = ' '.join([script] + sys.argv[1:])

        print("="*70)
        print("检测到程序需要管理员权限")
        print("正在请求管理员权限并重新启动...")
        print("="*70)

        # 使用ShellExecuteW以管理员权限启动
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # lpOperation (以管理员身份运行)
            python_exe,     # lpFile (Python解释器)
            params,         # lpParameters (脚本和参数)
            None,           # lpDirectory
            1               # nShowCmd (SW_NORMAL)
        )

        if ret > 32:  # ShellExecute成功返回值大于32
            print("✅ 已请求管理员权限，程序将重新启动")
            print("请在UAC提示中点击\"是\"以继续")
            sys.exit(0)
        else:
            print("❌ 请求管理员权限失败")
            print("请手动以管理员身份运行此程序")
            return False

    except Exception as e:
        print(f"❌ 请求管理员权限时出错: {e}")
        print("请手动以管理员身份运行此程序")
        return False

# 在程序启动时检查管理员权限
if sys.platform == 'win32':
    if not is_admin():
        print("\n" + "="*70)
        print("⚠️  检测到程序未以管理员权限运行")
        print("测试过程中需要修改网络配置，必须使用管理员权限")
        print("="*70 + "\n")

        # 尝试自动提升权限
        if not run_as_admin():
            print("\n" + "="*70)
            print("无法自动获取管理员权限")
            print("请按以下步骤手动操作：")
            print("1. 右键点击 PowerShell 或 CMD")
            print("2. 选择 '以管理员身份运行'")
            print("3. 在管理员终端中运行: python app.py")
            print("="*70 + "\n")

            # 给用户10秒时间阅读提示
            time.sleep(10)
            sys.exit(1)
    else:
        print("\n" + "="*70)
        print("✅ 程序已以管理员权限运行")
        print("="*70 + "\n")
# ==================== 管理员权限检测结束 ====================

# 自动清除Python缓存
def clear_python_cache():
    """清除项目中的Python缓存文件"""
    import shutil
    project_root = os.path.dirname(os.path.abspath(__file__))
    cache_cleared = False

    try:
        # 清除__pycache__目录
        for root, dirs, files in os.walk(project_root):
            if '__pycache__' in dirs:
                cache_dir = os.path.join(root, '__pycache__')
                try:
                    shutil.rmtree(cache_dir)
                    cache_cleared = True
                except Exception as e:
                    pass

            # 清除.pyc和.pyo文件
            for file in files:
                if file.endswith(('.pyc', '.pyo')):
                    try:
                        os.remove(os.path.join(root, file))
                        cache_cleared = True
                    except Exception as e:
                        pass

        if cache_cleared:
            print("✅ Python缓存已自动清除")
    except Exception as e:
        print(f"⚠️  清除缓存时出错: {e}")

# 启动时清除缓存
print("正在清除Python缓存...")
clear_python_cache()

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.test_runner import TestRunner
    from models.test_config import TestRequest, RouterConfig, TestMode
    from utils.excel_exporter import ExcelExporter

    print("✅ 成功导入所有模块")
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("尝试备用导入方式...")

    # 备用导入方式
    import core.test_runner as test_runner_module
    import models.test_config as test_config_module
    import utils.excel_exporter as excel_exporter_module

    TestRunner = test_runner_module.TestRunner
    TestRequest = test_config_module.TestRequest
    RouterConfig = test_config_module.RouterConfig
    TestMode = test_config_module.TestMode
    ExcelExporter = excel_exporter_module.ExcelExporter

# 创建 Flask 应用
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # 用于 session
test_runner = TestRunner()

# 全局变量用于实时日志和测试配置
log_queues = {}
pending_test_request = None  # 存储待执行的测试请求

# 添加 CORS 支持
@app.after_request
def after_request(response):
    """添加 CORS 头并禁用缓存"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.before_request
def handle_preflight():
    """处理预检请求"""
    if request.method == "OPTIONS":
        response = jsonify({"status": "success"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response


@app.route('/')
def index():
    """主页面"""
    try:
        # 直接读取HTML文件内容并返回
        with open('templates/index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        response = Response(html_content, mimetype='text/html')
        # 额外设置这个响应的缓存头
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        return f"Error loading template: {str(e)}", 500


@app.route('/api/test-cases')
def get_test_cases():
    """获取测试用例列表"""
    try:
        regression_only = request.args.get('regression_only', 'false').lower() == 'true'
        cases = test_runner.get_available_cases(regression_only)

        # 为前端提供更多信息，包括类名和分类路径
        enhanced_cases = []
        for case in cases:
            enhanced_case = {
                'name': case['name'],
                'class_name': case['class_name'],  # 添加类名信息
                'description': case['description'],
                'is_regression': case['is_regression'],
                'category': case.get('category', '')  # 添加分类路径信息
            }
            enhanced_cases.append(enhanced_case)

        return jsonify(enhanced_cases)
    except Exception as e:
        print(f"获取测试用例列表时出错: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/serial-ports')
def get_serial_ports():
    """获取本地电脑可用的串口列表"""
    try:
        import serial.tools.list_ports

        # 获取所有串口
        ports = serial.tools.list_ports.comports()

        # 构建返回数据
        serial_ports = []
        for port in ports:
            port_info = {
                'device': port.device,  # 如 COM3
                'description': port.description,  # 描述信息
                'hwid': port.hwid  # 硬件ID
            }
            serial_ports.append(port_info)

        print(f"检测到 {len(serial_ports)} 个串口设备")
        for port in serial_ports:
            print(f"  - {port['device']}: {port['description']}")

        return jsonify(serial_ports)
    except Exception as e:
        print(f"获取串口列表时出错: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/run-tests', methods=['POST'])
def run_tests():
    """执行测试 - 传统方式（保持兼容性）"""
    try:
        data = request.json
        print(f"=== 收到测试请求 ===")
        print(f"请求数据: {json.dumps(data, indent=2, ensure_ascii=False)}")

        # 构建路由器配置
        router_config = RouterConfig(
            router_ip=data['router_ip'],
            username=data['username'],
            password=data['password'],
            model=data['model'],
            module_type=data.get('module_type', 'auto'),
            serial_port=data.get('serial_port', 'COM3'),
            serial_baudrate=data.get('serial_baudrate', 115200),
            industrial_serial_port=data.get('industrial_serial_port', 'COM4'),
            mqtt_broker=data.get('mqtt_broker', '192.168.50.46'),
            mqtt_port=data.get('mqtt_port', 1883),
            modbus_server_ip=data.get('modbus_server_ip', '192.168.50.108'),
            modbus_port=data.get('modbus_port', 5020)
        )

        print(f"构建的路由器配置: {router_config}")

        # 处理测试模式
        test_mode_str = data['test_mode']
        print(f"前端传递的测试模式: {test_mode_str}")

        try:
            test_mode = TestMode(test_mode_str)
        except ValueError:
            # 如果前端传递了未知的测试模式，根据是否有选中的用例来决定
            if data.get('selected_cases'):
                test_mode = TestMode.SPECIFIC
            else:
                test_mode = TestMode.REGRESSION
            print(f"转换测试模式 '{test_mode_str}' 为 '{test_mode.value}'")

        # 构建测试配置
        test_request = TestRequest(
            router_config=router_config,
            test_mode=test_mode,
            selected_cases=data.get('selected_cases', []),
            timeout=data.get('timeout', 300),
            restore_default=data.get('restore_default', True)
        )

        print(f"构建的测试请求: {test_request}")
        print(f"开始执行测试，模式: {test_request.test_mode.value}, 选择的用例: {test_request.selected_cases}")

        result = test_runner.run_tests(test_request)

        print(f"测试执行完成，结果: {result['overall_result']}")
        return jsonify(result)

    except Exception as e:
        print(f"❌ 执行测试时出错: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "overall_result": "ERROR"
        }), 500


@app.route('/api/start-test-stream', methods=['POST'])
def start_test_stream():
    """启动测试（第一步：接收配置）"""
    global pending_test_request
    try:
        data = request.json
        print(f"=== 收到流式测试请求 ===")
        print(f"请求数据: {json.dumps(data, indent=2, ensure_ascii=False)}")

        # 构建路由器配置
        router_config = RouterConfig(
            router_ip=data['router_ip'],
            username=data['username'],
            password=data['password'],
            model=data['model'],
            module_type=data.get('module_type', 'auto'),
            serial_port=data.get('serial_port', 'COM3'),
            serial_baudrate=data.get('serial_baudrate', 115200),
            industrial_serial_port=data.get('industrial_serial_port', 'COM4'),
            mqtt_broker=data.get('mqtt_broker', '192.168.50.46'),
            mqtt_port=data.get('mqtt_port', 1883),
            modbus_server_ip=data.get('modbus_server_ip', '192.168.50.108'),
            modbus_port=data.get('modbus_port', 5020)
        )

        # 处理测试模式
        test_mode_str = data['test_mode']
        try:
            test_mode = TestMode(test_mode_str)
        except ValueError:
            if data.get('selected_cases'):
                test_mode = TestMode.SPECIFIC
            else:
                test_mode = TestMode.REGRESSION

        # 构建测试配置并存储到全局变量
        pending_test_request = TestRequest(
            router_config=router_config,
            test_mode=test_mode,
            selected_cases=data.get('selected_cases', []),
            timeout=data.get('timeout', 300),
            restore_default=data.get('restore_default', True)
        )

        print("✅ 测试配置已保存，等待日志流连接...")
        return jsonify({"success": True, "message": "测试配置已接收，请连接日志流"})

    except Exception as e:
        print(f"❌ 启动测试时出错: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/run-tests-stream', methods=['GET'])
def run_tests_stream():
    """执行测试并实时返回日志流（第二步：EventSource 连接）"""
    global pending_test_request

    if pending_test_request is None:
        return jsonify({"error": "没有待执行的测试配置"}), 400

    test_request = pending_test_request
    pending_test_request = None  # 清空全局变量

    def generate():
        """生成实时日志流"""
        try:
            # 发送开始消息
            start_message = {'type': 'start', 'message': '开始执行测试...'}
            yield f"data: {json.dumps(start_message, ensure_ascii=False)}\n\n"

            # 创建日志队列
            log_queue = Queue()

            # 定义日志回调函数
            def log_callback(log_data):
                """日志回调函数"""
                try:
                    log_queue.put({'type': 'log', 'data': log_data})
                except Exception as e:
                    print(f"日志回调队列操作失败: {e}")

            # 设置日志回调
            test_runner.set_log_callback(log_callback)

            # 在后台线程中执行测试
            def run_tests_in_thread():
                try:
                    print("测试线程开始运行")
                    result = test_runner.run_tests(test_request)
                    print(f"测试线程完成，结果: {result}")
                    log_queue.put({'type': 'result', 'data': result})
                except Exception as e:
                    print(f"测试线程异常: {e}")
                    import traceback
                    error_data = {
                        'type': 'error',
                        'message': str(e),
                        'traceback': traceback.format_exc()
                    }
                    log_queue.put(error_data)

            # 启动测试线程
            test_thread = threading.Thread(target=run_tests_in_thread)
            test_thread.daemon = True
            test_thread.start()

            # 实时发送日志
            last_heartbeat = time.time()
            while True:
                try:
                    # 从队列获取日志，超时0.5秒
                    log_data = log_queue.get(timeout=0.5)

                    if log_data.get('type') == 'result':
                        # 发送最终结果
                        result_message = {'type': 'result', 'data': log_data['data']}
                        yield f"data: {json.dumps(result_message, ensure_ascii=False)}\n\n"
                        break
                    elif log_data.get('type') == 'error':
                        # 发送错误信息
                        error_message = {
                            'type': 'error',
                            'message': log_data['message']
                        }
                        yield f"data: {json.dumps(error_message, ensure_ascii=False)}\n\n"
                        break
                    elif log_data.get('type') == 'progress':
                        # 发送进度更新
                        progress_message = {
                            'type': 'progress',
                            'progress': log_data['progress'],
                            'completed': log_data['completed'],
                            'total': log_data['total']
                        }
                        yield f"data: {json.dumps(progress_message, ensure_ascii=False)}\n\n"
                    else:
                        # 发送普通日志
                        log_message = {'type': 'log', 'data': log_data['data']}
                        yield f"data: {json.dumps(log_message, ensure_ascii=False)}\n\n"

                    last_heartbeat = time.time()

                except Empty:
                    # 检查测试线程是否还在运行
                    if not test_thread.is_alive():
                        # 线程已结束但未发送结果，可能是异常退出
                        error_message = {'type': 'error', 'message': '测试线程异常退出'}
                        yield f"data: {json.dumps(error_message, ensure_ascii=False)}\n\n"
                        break

                    # 每10秒发送一次心跳包
                    if time.time() - last_heartbeat > 10:
                        yield "data: {\"type\": \"heartbeat\", \"timestamp\": " + str(time.time()) + "}\n\n"
                        last_heartbeat = time.time()
                    continue

        except Exception as e:
            error_message = {'type': 'error', 'message': f'流生成器错误: {str(e)}'}
            yield f"data: {json.dumps(error_message, ensure_ascii=False)}\n\n"
        finally:
            # 清除回调函数
            test_runner.set_log_callback(None)
            print("实时日志流已关闭")

    response = Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        }
    )
    return response


@app.route('/api/test-logs/recent', methods=['GET'])
def get_recent_logs():
    """获取最近的测试日志"""
    try:
        logs = test_runner.get_recent_logs(100)
        return jsonify({
            "success": True,
            "logs": logs
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/test-logs/file', methods=['GET'])
def get_log_file_path():
    """获取当前日志文件路径"""
    try:
        log_file = test_runner.get_log_file_path()
        return jsonify({
            "success": True,
            "log_file": log_file
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/save-config', methods=['POST'])
def save_config():
    """保存配置到文件"""
    try:
        data = request.json
        config_data = {
            'router_config': data.get('router_config', {}),
            'test_config': data.get('test_config', {}),
            'test_mode': data.get('test_mode', 'regression'),
            'selected_cases': data.get('selected_cases', [])
        }

        # 保存配置到文件
        with open('test_config.json', 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        return jsonify({"success": True, "message": "配置已保存"})
    except Exception as e:
        print(f"保存配置时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/load-config')
def load_config():
    """从文件加载配置"""
    try:
        with open('test_config.json', 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        return jsonify(config_data)
    except FileNotFoundError:
        return jsonify({
            "router_config": {
                "router_ip": "192.168.1.1",
                "username": "admin",
                "password": "admin",
                "model": "UR35",
                "module_type": "auto"
            },
            "test_config": {
                "timeout": 300,
                "restore_default": True
            },
            "test_mode": "regression",
            "selected_cases": []
        })
    except Exception as e:
        print(f"加载配置时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/export-report', methods=['POST'])
def export_report():
    """导出测试报告为Excel"""
    try:
        data = request.json

        # 调试信息：打印接收到的数据
        print("\n=== 导出报告 - 接收到的数据 ===")
        print(f"results数量: {len(data.get('results', []))}")
        print(f"config: {data.get('config', {})}")
        print(f"summary: {data.get('summary', {})}")

        # 提取测试结果数据
        results = data.get('results', [])
        config = data.get('config', {})
        summary = data.get('summary', {})

        if not results:
            return jsonify({
                "success": False,
                "error": "没有测试结果可导出"
            }), 400

        # 创建Excel导出器
        exporter = ExcelExporter(output_dir="reports")

        # 准备路由器配置信息
        router_config = {
            'router_ip': config.get('routerIp', ''),
            'model': config.get('model', ''),
            'username': config.get('username', ''),
        }

        # 准备测试汇总信息
        test_info = {
            'total': summary.get('total', 0),
            'passed': summary.get('passed', 0),
            'failed': summary.get('failed', 0),
            'error': summary.get('error', 0),
            'duration': summary.get('duration', 0),
            'overall_result': summary.get('overall_result', 'UNKNOWN')
        }

        print(f"准备导出 - test_info: {test_info}")

        # 生成Excel文件
        filepath = exporter.export_test_results(results, router_config, test_info)

        # 返回文件供下载
        return send_file(
            filepath,
            as_attachment=True,
            download_name=os.path.basename(filepath),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        print(f"导出报告时出错: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/refresh-test-cases', methods=['POST'])
def refresh_test_cases():
    """刷新测试用例列表"""
    try:
        print("=== 手动刷新测试用例 ===")
        # 强制重新发现测试用例
        test_runner.available_cases = test_runner._discover_test_cases()

        cases = test_runner.get_available_cases(regression_only=False)

        print(f"刷新后发现的测试用例数量: {len(cases)}")

        # 为前端提供更多信息，包括类名和分类路径
        enhanced_cases = []
        for case in cases:
            enhanced_case = {
                'name': case['name'],
                'class_name': case['class_name'],
                'description': case['description'],
                'is_regression': case['is_regression'],
                'category': case.get('category', '')
            }
            enhanced_cases.append(enhanced_case)

        return jsonify(enhanced_cases)
    except Exception as e:
        print(f"刷新测试用例列表时出错: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/test-stream-connection')
def test_stream_connection():
    """测试流连接"""

    def generate():
        for i in range(5):
            message = {'type': 'test', 'message': f'测试消息 {i + 1}', 'timestamp': time.time()}
            yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
            time.sleep(1)
        yield f"data: {json.dumps({'type': 'complete', 'message': '测试完成'}, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

if __name__ == '__main__':
    # 禁用重载器以避免导入问题
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)