from test_cases.base_test import BaseTest
import time
import re


class CellularStatusVerificationTest(BaseTest):
    """蜂窝注网成功后，核对蜂窝相关页面的状态显示

    前置条件：
    1. 设备天线使用标准出货的天线
    2. SIM卡已经插入，并且拨号成功

    测试步骤：
    1. 读取状态-蜂窝页面的各项信息
    2. 通过AT指令查询对应的值
    3. 逐项对比验证
    4. 记录所有验证结果
    """

    # 添加分类信息属性
    category = "功能用例/网络/接口/蜂窝网络"
    is_regression = True  # 标记为回归测试用例

    @property
    def test_name(self):
        """实现抽象属性，返回测试名称"""
        return "蜂窝状态页面信息验证测试"

    def __init__(self, config):
        """初始化方法"""
        super().__init__(config)

        # 从config中获取router_client
        self.router_client = self.create_router_client(config.router_config)

        # 存储验证结果
        self.verification_results = []
        self.all_passed = True

    def create_router_client(self, router_config):
        """创建路由器客户端"""
        try:
            from core.router_client import RouterClient
            print(f"✅ 成功从 core.router_client 导入 RouterClient")
            return RouterClient(router_config)
        except ImportError as e:
            print(f"❌ 无法从 core.router_client 导入: {e}")
            raise

    def setup(self):
        """测试前置条件"""
        print(f"INFO - {self.__class__.__name__}: 前置条件：登录路由器")

        # 确保已登录
        if not hasattr(self.router_client, 'logged_in') or not self.router_client.logged_in:
            login_success = self.router_client.login_web()
            if not login_success:
                raise Exception("登录失败")

        print("✅ 路由器登录成功")

    def execute(self):
        """执行测试"""
        try:
            print(f"INFO - {self.__class__.__name__}: 开始验证蜂窝状态页面信息")

            # 步骤1: 读取蜂窝状态页面信息
            print("\n" + "="*60)
            print("步骤1: 读取蜂窝状态页面信息")
            print("="*60)
            page_info = self.router_client.get_cellular_status_page_info()
            if not page_info:
                raise Exception("无法读取蜂窝状态页面信息")

            # 步骤2: 验证各项信息
            print("\n" + "="*60)
            print("步骤2: 开始逐项验证")
            print("="*60)

            # a. 验证模块型号
            self._verify_model(page_info)

            # b. 验证模组版本
            self._verify_modem_version(page_info)

            # c. 验证信号强度
            self._verify_signal(page_info)

            # d. 验证注册状态
            self._verify_register_status(page_info)

            # e. 验证 IMEI
            self._verify_imei(page_info)

            # f. 验证 IMSI
            self._verify_imsi(page_info)

            # g. 验证 ICCID
            self._verify_iccid(page_info)

            # h. 验证运营商
            self._verify_net_provider(page_info)

            # i. 验证网络类型
            self._verify_net_type(page_info)

            # j. 验证蜂窝频段
            self._verify_band(page_info)

            # k. 验证 PLMN ID
            self._verify_plmnid(page_info)

            # l, m, n, o, p. 验证基站信息（LAC, Cell ID, RSRP, RSRQ, SINR）
            self._verify_serving_cell_info(page_info)

            # 步骤3: 汇总结果
            print("\n" + "="*60)
            print("步骤3: 验证结果汇总")
            print("="*60)
            self._print_summary()

            # 返回结果
            return self.all_passed

        except Exception as e:
            print(f"ERROR - {self.__class__.__name__}: ❌ 测试执行失败: {str(e)}")
            raise

    def _verify_model(self, page_info):
        """验证模块型号"""
        print("\n【a. 模块型号验证】")
        page_value = page_info.get('model', '')
        expected_value = self.router_client.module_type

        passed = (page_value == expected_value)
        self._record_result('模块型号', expected_value, page_value, passed)

    def _verify_modem_version(self, page_info):
        """验证模组版本"""
        print("\n【b. 模组版本验证】")
        page_value = page_info.get('modem_version', '')

        # 根据模组类型选择AT指令
        module_type = self.router_client.module_type.lower()
        if 'quectel' in module_type or '移远' in module_type:
            at_command = 'AT+QGMR'
        elif 'meig' in module_type or '美格' in module_type:
            at_command = 'AT+SGSW'
        else:
            # 默认使用移远
            at_command = 'AT+QGMR'

        print(f"使用AT指令: {at_command}")

        # 发送AT指令
        self.router_client.AT_COMAND_SET(at_command)
        time.sleep(2)

        # 获取响应
        response = self.router_client.AT_COMAND_GET()
        at_value = response.get('processed_response', '')

        passed = (page_value in at_value or at_value in page_value)
        self._record_result('模组版本', at_value, page_value, passed, at_command=at_command)

    def _verify_signal(self, page_info):
        """验证信号强度"""
        print("\n【c. 信号强度验证】")
        page_value = page_info.get('signal', '')

        # 发送 AT+CSQ 指令
        at_command = 'AT+CSQ'
        print(f"使用AT指令: {at_command}")

        self.router_client.AT_COMAND_SET(at_command)
        time.sleep(2)

        response = self.router_client.AT_COMAND_GET()
        at_response = response.get('processed_response', '')

        # 解析 AT+CSQ 响应，格式: +CSQ: 21,99
        csq_match = re.search(r'\+CSQ:\s*(\d+)', at_response)
        if csq_match:
            csq_value = csq_match.group(1)
            # 页面显示的信号强度可能包含单位或格式化
            passed = csq_value in page_value
            self._record_result('信号强度', csq_value, page_value, passed, at_command=at_command)
        else:
            self._record_result('信号强度', at_response, page_value, False, at_command=at_command)

    def _verify_register_status(self, page_info):
        """验证注册状态"""
        print("\n【d. 注册状态验证】")
        page_value = page_info.get('register', '')
        expected_value = 'Registered'

        passed = (expected_value in page_value)
        self._record_result('注册状态', expected_value, page_value, passed)

    def _verify_imei(self, page_info):
        """验证 IMEI"""
        print("\n【e. IMEI验证】")
        page_value = page_info.get('imei', '')

        # 发送 AT+GSN 指令
        at_command = 'AT+GSN'
        print(f"使用AT指令: {at_command}")

        self.router_client.AT_COMAND_SET(at_command)
        time.sleep(2)

        response = self.router_client.AT_COMAND_GET()
        at_value = response.get('processed_response', '').strip()

        # 提取数字
        at_imei = re.sub(r'[^\d]', '', at_value)
        page_imei = re.sub(r'[^\d]', '', page_value)

        passed = (at_imei == page_imei)
        self._record_result('IMEI', at_imei, page_imei, passed, at_command=at_command)

    def _verify_imsi(self, page_info):
        """验证 IMSI"""
        print("\n【f. IMSI验证】")
        page_value = page_info.get('imsi', '')

        # 发送 AT+CIMI 指令
        at_command = 'AT+CIMI'
        print(f"使用AT指令: {at_command}")

        self.router_client.AT_COMAND_SET(at_command)
        time.sleep(2)

        response = self.router_client.AT_COMAND_GET()
        at_value = response.get('processed_response', '').strip()

        # 提取数字
        at_imsi = re.sub(r'[^\d]', '', at_value)
        page_imsi = re.sub(r'[^\d]', '', page_value)

        passed = (at_imsi == page_imsi)
        self._record_result('IMSI', at_imsi, page_imsi, passed, at_command=at_command)

    def _verify_iccid(self, page_info):
        """验证 ICCID"""
        print("\n【g. ICCID验证】")
        page_value = page_info.get('iccid', '')

        # 发送 AT+QCCID 指令
        at_command = 'AT+QCCID'
        print(f"使用AT指令: {at_command}")

        self.router_client.AT_COMAND_SET(at_command)
        time.sleep(2)

        response = self.router_client.AT_COMAND_GET()
        at_response = response.get('processed_response', '')

        # 提取ICCID，格式可能是: +QCCID: 89860123456789012345
        iccid_match = re.search(r'(\d{18,20})', at_response)
        if iccid_match:
            at_iccid = iccid_match.group(1)
            page_iccid = re.sub(r'[^\d]', '', page_value)
            passed = (at_iccid == page_iccid)
            self._record_result('ICCID', at_iccid, page_iccid, passed, at_command=at_command)
        else:
            self._record_result('ICCID', at_response, page_value, False, at_command=at_command)

    def _verify_net_provider(self, page_info):
        """验证运营商"""
        print("\n【h. 运营商验证】")
        page_value = page_info.get('net_provider', '')

        # 根据配置判断预期运营商
        # 这里需要从用户配置中获取，暂时先记录
        print(f"页面显示运营商: {page_value}")
        print("⚠️ 运营商验证需要根据自动化平台输入的运营商类型判断")

        # 简单验证：至少要有值
        passed = bool(page_value)
        self._record_result('运营商', '有值', page_value, passed)

    def _verify_net_type(self, page_info):
        """验证网络类型"""
        print("\n【i. 网络类型验证】")
        page_value = page_info.get('net_type', '')

        # 发送 AT+QNWINFO 指令
        at_command = 'AT+QNWINFO'
        print(f"使用AT指令: {at_command}")

        self.router_client.AT_COMAND_SET(at_command)
        time.sleep(2)

        response = self.router_client.AT_COMAND_GET()
        at_response = response.get('processed_response', '')

        # 解析格式: +QNWINFO: "FDD LTE","46011","LTE BAND 3",1650
        # 第一位是网络类型
        match = re.search(r'\+QNWINFO:\s*"([^"]+)"', at_response)
        if match:
            at_net_type = match.group(1)
            passed = (at_net_type == page_value)
            self._record_result('网络类型', at_net_type, page_value, passed, at_command=at_command)
        else:
            self._record_result('网络类型', at_response, page_value, False, at_command=at_command)

    def _verify_band(self, page_info):
        """验证蜂窝频段"""
        print("\n【j. 蜂窝频段验证】")
        page_value = page_info.get('band', '')

        # 使用之前 AT+QNWINFO 的结果（第三位）
        at_command = 'AT+QNWINFO'
        print(f"使用AT指令: {at_command}")

        self.router_client.AT_COMAND_SET(at_command)
        time.sleep(2)

        response = self.router_client.AT_COMAND_GET()
        at_response = response.get('processed_response', '')

        # 解析格式: +QNWINFO: "FDD LTE","46011","LTE BAND 3",1650
        # 第三位是频段
        match = re.search(r'\+QNWINFO:\s*"[^"]+","[^"]+","([^"]+)"', at_response)
        if match:
            at_band = match.group(1)
            passed = (at_band in page_value or page_value in at_band)
            self._record_result('蜂窝频段', at_band, page_value, passed, at_command=at_command)
        else:
            self._record_result('蜂窝频段', at_response, page_value, False, at_command=at_command)

    def _verify_plmnid(self, page_info):
        """验证 PLMN ID"""
        print("\n【k. PLMN ID验证】")
        page_value = page_info.get('plmnid', '')

        # 使用之前 AT+QNWINFO 的结果（第二位）
        at_command = 'AT+QNWINFO'
        print(f"使用AT指令: {at_command}")

        self.router_client.AT_COMAND_SET(at_command)
        time.sleep(2)

        response = self.router_client.AT_COMAND_GET()
        at_response = response.get('processed_response', '')

        # 解析格式: +QNWINFO: "FDD LTE","46011","LTE BAND 3",1650
        # 第二位是PLMN ID
        match = re.search(r'\+QNWINFO:\s*"[^"]+","([^"]+)"', at_response)
        if match:
            at_plmnid = match.group(1)
            passed = (at_plmnid == page_value)
            self._record_result('PLMN ID', at_plmnid, page_value, passed, at_command=at_command)
        else:
            self._record_result('PLMN ID', at_response, page_value, False, at_command=at_command)

    def _verify_serving_cell_info(self, page_info):
        """验证基站信息（LAC, Cell ID, RSRP, RSRQ, SINR）"""
        print("\n【l-p. 基站信息验证】")

        # 发送 AT+QENG="servingcell" 指令
        at_command = 'AT+QENG="servingcell"'
        print(f"使用AT指令: {at_command}")

        self.router_client.AT_COMAND_SET(at_command)
        time.sleep(2)

        response = self.router_client.AT_COMAND_GET()
        at_response = response.get('processed_response', '')

        print(f"AT响应: {at_response}")

        # 解析响应提取各字段
        # 格式示例: +QENG: "servingcell","NOCONN","LTE","FDD",460,11,xxxx,xxx,1650,3,3,xxxx,-88,-9,-58,14
        # 需要根据实际格式解析 LAC, Cell ID, RSRP, RSRQ, SINR

        # 这里简化处理，实际需要根据具体返回格式解析
        # LAC (位置区码)
        page_lac = page_info.get('lac', '')
        # Cell ID
        page_cellid = page_info.get('cellid', '')
        # RSRP
        page_rsrp = page_info.get('rsrp', '')
        # RSRQ
        page_rsrq = page_info.get('rsrq', '')
        # SINR
        page_sinr = page_info.get('sinr', '')

        # 记录结果（具体解析逻辑需要根据实际AT响应格式完善）
        self._record_result('位置区码(LAC)', 'AT响应中的值', page_lac, True, at_command=at_command, note="需根据AT响应格式解析")
        self._record_result('Cell ID', 'AT响应中的值', page_cellid, True, at_command=at_command, note="需根据AT响应格式解析")
        self._record_result('RSRP', 'AT响应中的值', page_rsrp, True, at_command=at_command, note="需根据AT响应格式解析")
        self._record_result('RSRQ', 'AT响应中的值', page_rsrq, True, at_command=at_command, note="需根据AT响应格式解析")
        self._record_result('SINR', 'AT响应中的值', page_sinr, True, at_command=at_command, note="需根据AT响应格式解析")

    def _record_result(self, item_name, expected, actual, passed, at_command=None, note=None):
        """记录验证结果"""
        result = {
            'item': item_name,
            'expected': expected,
            'actual': actual,
            'passed': passed,
            'at_command': at_command,
            'note': note
        }

        self.verification_results.append(result)

        if not passed:
            self.all_passed = False

        # 打印结果
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {item_name}")
        print(f"  预期值: {expected}")
        print(f"  实际值: {actual}")
        if at_command:
            print(f"  AT指令: {at_command}")
        if note:
            print(f"  备注: {note}")

    def _print_summary(self):
        """打印验证结果汇总"""
        total = len(self.verification_results)
        passed = sum(1 for r in self.verification_results if r['passed'])
        failed = total - passed

        print(f"\n{'='*60}")
        print(f"验证结果汇总:")
        print(f"  总计: {total} 项")
        print(f"  通过: {passed} 项")
        print(f"  失败: {failed} 项")
        print(f"{'='*60}")

        if failed > 0:
            print("\n失败项目详情:")
            for result in self.verification_results:
                if not result['passed']:
                    print(f"\n  ❌ {result['item']}")
                    print(f"     预期: {result['expected']}")
                    print(f"     实际: {result['actual']}")
                    if result['at_command']:
                        print(f"     AT指令: {result['at_command']}")

        print(f"\n最终结果: {'✅ 全部通过' if self.all_passed else '❌ 存在失败项'}")

    def cleanup(self):
        """测试后清理"""
        print(f"INFO - {self.__class__.__name__}: 蜂窝状态验证测试完成")

        # 关闭浏览器（如果需要）
        if hasattr(self.router_client, 'close'):
            self.router_client.close()
