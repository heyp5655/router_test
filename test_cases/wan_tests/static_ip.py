from test_cases.base_test import BaseTest
import time


class PPPoETest(BaseTest):
    @property
    def test_name(self) -> str:
        return "静态ip连接测试"

    @property
    def is_regression(self) -> bool:
        return True

    def setup(self):
        """测试前置条件"""
        self.logger.info("开始静态ip连接测试")
        # 确保登录成功
        login_success = self.router_client.login_web()
        if not login_success:
            raise Exception("路由器登录失败")

    def execute(self):
        """执行静态ip连接测试"""
        try:
            self.logger.info("配置静态ip参数")

            # 配置PPPoE
            static_config = {
                "ipv4": "192.168.50.16",
                "netmask": "255.255.255.0",
                "gateway": "192.168.50.1",
            }

            success = self.router_client.configure_wan_pppoe(static_config)

            if not success:
                raise Exception("静态ip配置失败")

            # 等待连接建立
            self.logger.info("等待静态ip连接建立...")
            time.sleep(5)  # 缩短等待时间用于调试

            # 检查连接状态
            self.logger.info("检查WAN口连接状态")
            is_connected = self.router_client.check_wan_status()

            if not is_connected:
                raise Exception("静态ip连接失败")

            self.test_result["details"] = {
                "wan_type": "静态ip",
                "connection_status": "connected"
            }
            self.logger.info("✅ 静态ip连接测试通过")

        except Exception as e:
            self.logger.error(f"静态ip测试执行失败: {str(e)}")
            raise

    def cleanup(self):
        """测试清理"""
        self.logger.info("静态ip测试完成")