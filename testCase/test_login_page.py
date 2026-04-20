#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
登录页面测试用例
"""

import pytest

import pytest

from utils.config_manager import ConfigManager
from utils.super_handler_factory import create_handler



class TestLoginPage:
    @pytest.fixture(autouse=True)
    def setup_test_resources(self, page_test_factory):
        """自动设置测试资源"""
        self.resources = page_test_factory
        self.driver = self.resources['driver']
        self.login_page = self.resources['page']  # LoginPage实例（页面对象）
        self.login_handler = self.resources['handler']  # LoginHandler实例（业务逻辑）
        self.login_config = self.resources['page_config']
        self.log = self.resources['log']  # 日志记录器
        self.config_manager = ConfigManager()

        # 注意：main_handler等已在conftest.py中创建，这里不再重复创建
        # 如果需要其他handler，可以使用现有的driver实例

        self.customer_handler = create_handler('customer_management_page', driver=self.driver)
        self.customer_management_data = self.config_manager.get_test_data('customer_management_page')
        # 但通常情况下，一个测试类只专注于一个页面，跨页面操作应该在handler层完成

    def setup_method(self):
        """每个测试方法执行前的设置"""
        # 确保输入框为空
        if hasattr(self, 'login_page') and self.login_page is not None:
            self.login_page.clear_input_fields()

    def teardown_method(self):
        """每个测试方法执行后的清理"""
        pass

    def test_valid_login(self):
        """测试有效凭据登录"""
        # 添加调试信息
        self.log.info(f"valid_credentials value: {self.login_config}")
        
        # 检查login_config是否为None
        if self.login_config is None:
            self.log.error("login_config is None, 无法继续测试")
            pytest.fail("login_config is None, 无法继续测试")
        
        # 获取测试数据
        valid_credentials = self.login_config.get('test_data', {}).get('valid_login', {})
        self.log.info(f"valid_credentials: {valid_credentials}")
        
        if not valid_credentials:
            self.log.error("无法获取有效的登录凭据")
            pytest.fail("无法获取有效的登录凭据")
        
        # 执行登录操作
        username = valid_credentials.get('username', '')
        password = valid_credentials.get('password', '')
        
        self.log.info(f"使用用户名: {username}, 密码: {password} 进行登录测试")
        
        self.log.info("开始调用 login_handler.login_with_retry")
        login_result = self.login_handler.login(username, password)
        
        #打印日志登录结果
        if login_result:
            self.log.info("login_result 为 True，登录成功")
        #新增客户
        add_customer_scenario=self.customer_management_data.get("add_customer_scenario",{})
        add_result = self.customer_handler.add_customer_and_verify(
            short_name=add_customer_scenario.get("short_name", ""),
            full_name=add_customer_scenario.get("full_name", ""),
            code=add_customer_scenario.get("code", ""),
            link_man=add_customer_scenario.get("link_man", ""),
            link_phone=add_customer_scenario.get("link_phone", ""),
            confirm=add_customer_scenario.get("confirm", ""),
            timeout=10.0
        )
        if add_result["success"]:
            self.log.info("✓ 新增客户成功")
        else:
            self.log.error("✗ 新增客户失败")
        #查询客户
        query_customer_scenario = self.customer_management_data.get("query_customer", {})
        query_customer_result = self.customer_handler.query_customer(search_key=query_customer_scenario.get("search_key", ""), timeout=10.0)
        if query_customer_result["success"]:
            self.log.info("✓ 查询客户成功")
        else:
            self.log.error("✗ 查询客户失败")
        #修改客户
        alter_customer_success_scenario=self.customer_management_data.get("alter_customer_success",{})
        alter_result = self.customer_handler.alter_customer_and_verify(
            short_name=alter_customer_success_scenario.get("short_name", ""),
            full_name=alter_customer_success_scenario.get("full_name", ""),
            code=alter_customer_success_scenario.get("code", ""),
            link_man=alter_customer_success_scenario.get("link_man", ""),
            link_phone=alter_customer_success_scenario.get("link_phone", ""),
        )
        if alter_result["success"]:
            self.log.info("✓ 修改客户成功")
        else:
            self.log.error("✗ 修改客户失败")
        #删除客户
        delete_customer_scenario=self.customer_management_data.get("delete_customer_success",{})
        delete_result = self.customer_handler.delete_customer_and_verify(search_key=delete_customer_scenario.get("search_key", ""))
        if delete_result["success"]:
            self.log.info("✓ 删除客户成功")
        else:
            self.log.error("✗ 删除客户失败")



    def test_invalid_login(self):
        """测试无效凭据登录"""
        # 获取测试数据
        invalid_credentials = self.login_config.get('invalid_credentials', {})
        test_cases = invalid_credentials.get('test_cases', [])
        
        for i, test_case in enumerate(test_cases):
            self.log.info(f"开始测试: 无效凭据登录 - 场景{i+1} - 用户: {test_case.get('username', '空')}")
            
            # 执行登录操作
            username = test_case.get('username', '')
            password = test_case.get('password', '')
            
            login_result = self.login_handler.login_with_failure(
                username, password,
                max_retries=invalid_credentials.get('max_retries', 1),
                retry_delay=invalid_credentials.get('retry_delay', 1)
            )
            
            # 验证登录失败结果
            if login_result:
                self.log.info("✓ 登录失败,弹出提示框正确")
            else:
                self.log.error("✗ 登录失败，验证未通过")

    # def test_login_response_time(self):
    #     """测试登录响应时间"""
    #     self.log.info("测试登录响应时间")
    #
    #     # 获取测试数据
    #     performance_test = self.login_config.get('performance_test', {})
    #     test_username = performance_test.get('username', 'testuser')
    #     test_password = performance_test.get('password', 'testpass')
    #     max_response_time = performance_test.get('max_response_time', 5.0)  # 默认5秒
    #
    #     # 清空输入框
    #     self.login_page.clear_input_fields()
    #
    #     # 执行登录并测量响应时间
    #     start_time = time.time()
    #     login_success = self.login_page.login(test_username, test_password)
    #     end_time = time.time()
    #
    #     response_time = end_time - start_time
    #     self.log.info(f"登录响应时间: {response_time:.2f}秒")
    #
    #     # 验证响应时间
    #     assert response_time <= max_response_time, f"登录响应时间({response_time:.2f}s)超过最大允许时间({max_response_time}s)"
    #     self.log.info("✓ 登录性能测试通过")


if __name__ == '__main__':
    print("登录功能测试")
    print("运行命令: pytest test_login_page.py -v --alluredir=./reports")
    print("查看报告: allure serve ./reports")