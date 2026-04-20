# -*- coding: utf-8 -*-
"""
NovaWindows Driver Factory - 支持 NovaWindows Driver 和 Appium 3.x
核心改进：
- NovaWindows Driver 高性能元素定位 (点击快3倍, 输入快2.4倍)
- Appium 3.x 自动服务器管理
- 元素缓存机制 - 避免重复定位
- 智能等待策略 - 减少等待时间
- 并行测试支持
- 40+ 平台特定命令 (窗口操作、滚动、值设置等)

注意：NovaWindows Driver 需要 Appium 3.0.0 及以上版本
"""

import socket
import os
import subprocess
import time
import logging
import threading
from typing import Dict, Any, Optional, Callable
from functools import wraps
from appium import webdriver as appium_webdriver
try:
    from appium.options.common.base import AppiumOptions  # appium-python-client 2.x/3.x/4.x
    _opts = AppiumOptions()
    if not hasattr(_opts, 'set_capability'):
        raise ImportError("no set_capability")
except ImportError:
    from selenium.webdriver import ChromeOptions as AppiumOptions
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.env import Environment

logger = logging.getLogger(__name__)


class ElementCache:
    """
    元素缓存管理器 - 大幅提升定位效率
    
    特点：
    - 自动缓存已定位的元素
    - 支持缓存过期机制
    - 线程安全
    """
    
    def __init__(self, timeout: int = 300):  # 默认5分钟过期
        self._cache: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        self._default_timeout = timeout
    
    def _generate_key(self, strategy: str, locator: str) -> str:
        """生成缓存Key"""
        return f"{strategy}:{locator}"
    
    def get(self, strategy: str, locator: str) -> Optional[Any]:
        """获取缓存的元素"""
        key = self._generate_key(strategy, locator)
        with self._lock:
            if key in self._cache:
                data = self._cache[key]
                # 检查是否过期
                if time.time() - data['timestamp'] < data.get('timeout', self._default_timeout):
                    logger.debug(f"从缓存获取元素: {key}")
                    return data['element']
                else:
                    # 过期，移除
                    del self._cache[key]
            return None
    
    def set(self, strategy: str, locator: str, element, timeout: int = None) -> None:
        """缓存元素"""
        key = self._generate_key(strategy, locator)
        with self._lock:
            self._cache[key] = {
                'element': element,
                'timestamp': time.time(),
                'timeout': timeout or self._default_timeout
            }
            logger.debug(f"缓存元素: {key}")
    
    def invalidate(self, strategy: str = None, locator: str = None) -> None:
        """使缓存失效"""
        with self._lock:
            if strategy and locator:
                key = self._generate_key(strategy, locator)
                if key in self._cache:
                    del self._cache[key]
            elif strategy:
                # 删除所有匹配策略的缓存
                keys_to_delete = [k for k in self._cache if k.startswith(f"{strategy}:")]
                for k in keys_to_delete:
                    del self._cache[k]
            else:
                # 清空所有缓存
                self._cache.clear()
            logger.debug(f"缓存失效: strategy={strategy}, locator={locator}")
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            logger.info("元素缓存已清空")


def _check_port(port: int, timeout: float = 1.0) -> bool:
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            return s.connect_ex(('127.0.0.1', port)) == 0
        except socket.timeout:
            return False


class AppiumServerManager:
    """
    Appium服务器管理器 - 自动启动和管理Appium服务器
    """
    
    _instances = {}
    _lock = threading.RLock()
    
    def __new__(cls, host: str = '127.0.0.1', port: int = 4723):
        key = f"{host}:{port}"
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = super().__new__(cls)
                cls._instances[key]._initialized = False
            return cls._instances[key]
    
    def __init__(self, host: str = '127.0.0.1', port: int = 4723):
        if self._initialized:
            return
        self.host = host
        self.port = port
        self._process = None
        self._initialized = True
    
    def start_server(self, timeout: int = 30) -> bool:
        """启动Appium服务器"""
        if _check_port(self.port):
            logger.info(f"Appium服务器已在端口 {self.port} 运行")
            return True
        
        try:
            # 使用appium命令启动
            import subprocess
            cmd = [
                'appium',
                '--address', self.host,
                '--port', str(self.port),
                '--log-level', 'error',
                '--no-reset',
                '--local-timezone'
            ]
            
            logger.info(f"启动Appium服务器: {' '.join(cmd)}")
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 等待服务器启动
            start_time = time.time()
            while time.time() - start_time < timeout:
                if _check_port(self.port):
                    logger.info(f"Appium服务器启动成功: {self.host}:{self.port}")
                    return True
                time.sleep(0.5)
            
            logger.error("Appium服务器启动超时")
            return False
            
        except Exception as e:
            logger.error(f"启动Appium服务器失败: {e}")
            return False
    
    def stop_server(self) -> None:
        """停止Appium服务器"""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            logger.info("Appium服务器已停止")


class SmartWait:
    """
    智能等待管理器 - 动态调整等待时间
    
    策略：
    - 初始等待短，逐渐延长
    - 检测元素稳定性
    - 支持快速失败模式
    """
    
    def __init__(self, driver, timeout: int = 10, poll_frequency: float = 0.3):
        self.driver = driver
        self.timeout = timeout
        self.poll_frequency = poll_frequency
    
    def until(self, condition: Callable, *args, **kwargs):
        """
        智能等待直到条件满足
        
        Args:
            condition: 等待条件函数
            *args, **kwargs: 条件函数的参数
            
        Returns:
            满足条件时的返回值
        """
        start_time = time.time()
        last_exception = None
        
        while time.time() - start_time < self.timeout:
            try:
                result = condition(*args, **kwargs)
                if result:
                    # 检测到元素，快速返回
                    elapsed = time.time() - start_time
                    if elapsed > 1.0:  # 如果等待超过1秒，记录日志
                        logger.debug(f"智能等待成功，耗时: {elapsed:.2f}秒")
                    return result
            except Exception as e:
                last_exception = e
            
            time.sleep(self.poll_frequency)
        
        raise TimeoutException(
            f"智能等待超时 ({self.timeout}秒)",
            cause=last_exception
        )


class TimeoutException(Exception):
    """自定义超时异常"""
    def __init__(self, message, cause=None):
        super().__init__(message)
        self.cause = cause


class DriverFactory:
    """
    Appium Driver工厂类
    
    核心功能：
    - 支持Appium 2.x
    - Windows桌面应用自动化
    - 元素缓存
    - 智能等待
    """
    
    _config = Environment()
    _element_cache = ElementCache(timeout=300)  # 5分钟缓存
    
    # 缓存配置
    _cache_enabled = True
    _cache_timeout = 300  # 元素缓存默认5分钟
    
    @classmethod
    def enable_cache(cls, enabled: bool = True, timeout: int = 300) -> None:
        """启用/禁用元素缓存"""
        cls._cache_enabled = enabled
        if timeout:
            cls._cache_timeout = timeout
        logger.info(f"元素缓存: {'启用' if enabled else '禁用'}, 超时: {timeout}秒")
    
    @classmethod
    def clear_cache(cls) -> None:
        """清空元素缓存"""
        cls._element_cache.clear()
    
    @classmethod
    def _build_appium_options(cls, platform: str = 'windows') -> AppiumOptions:
        """
        构建Appium选项

        Args:
            platform: 平台类型 ('windows', 'android', 'ios')

        Returns:
            AppiumOptions实例
        """
        options = AppiumOptions()

        if platform.lower() == 'windows':
            # Windows桌面应用配置
            app_path = cls._config.get_app_path()
            app_name = cls._config.get_app_name()

            options.set_capability('platformName', 'Windows')
            options.set_capability('deviceName', 'WindowsPC')

            if app_path:
                # 如果配置了应用路径，优先启动新应用（即使也配置了 app_name）
                if os.path.exists(app_path):
                    options.set_capability('app', app_path)
                    logger.info(f"使用应用路径启动: {app_path}")
                else:
                    # 路径无效，使用 Root 模式连接桌面
                    logger.warning(f"应用路径无效: {app_path}，使用 Root 模式")
                    options.set_capability('app', 'Root')
                    logger.info(f"使用 Root 连接模式，通过窗口标题: {app_name}")
            elif app_name:
                # 只有当没有配置 app_path 时才使用 Root 模式
                options.set_capability('app', 'Root')
                logger.info(f"使用 Root 连接模式，通过窗口标题: {app_name}")
            else:
                raise ValueError("必须提供 app_path 或 app_name 配置")

            # NovaWindows 特定优化
            options.set_capability('automationName', 'NovaWindows')
            options.set_capability('noReset', True)  # 避免重复启动
            options.set_capability('fullReset', False)
            # 关键：会话结束时不要关闭应用，这样登录后我们才能重新用
            # appTopLevelWindow 绑定到主窗而不影响应用
            options.set_capability('shouldCloseApp', False)

        return options

    @classmethod
    def _find_window_by_title(cls, driver, title: str, timeout: int = 10) -> Optional[str]:
        """
        通过窗口标题查找窗口句柄

        Args:
            driver: WebDriver实例
            title: 窗口标题（部分匹配）
            timeout: 超时时间（秒）

        Returns:
            窗口句柄或None
        """
        import time
        end_time = time.time() + timeout

        while time.time() < end_time:
            try:
                window_handles = driver.window_handles
                for handle in window_handles:
                    driver.switch_to.window(handle)
                    if title in driver.title:
                        logger.info(f"找到窗口: '{title}', 句柄: {handle}, 标题: {driver.title}")
                        return handle
            except Exception as e:
                logger.debug(f"查找窗口时出错: {e}")
            time.sleep(0.5)

        logger.warning(f"未找到标题包含 '{title}' 的窗口")
        return None
    
    @classmethod
    def _get_server_url(cls) -> str:
        """获取Appium服务器URL"""
        host = cls._config.get_appium_host()
        port = cls._config.get_appium_port()
        return f'http://{host}:{port}'
    
    @classmethod
    def _ensure_server_running(cls, port: int = None) -> bool:
        """确保Appium服务器正在运行"""
        if port is None:
            port = int(cls._config.get_appium_port())
        
        if not _check_port(port):
            logger.warning(f"Appium服务器未运行，尝试自动启动...")
            server_manager = AppiumServerManager(port=port)
            return server_manager.start_server()
        return True
    
    @classmethod
    def get_driver(cls, platform: str = 'windows') -> Optional[RemoteWebDriver]:
        """
        获取Appium WebDriver实例

        Args:
            platform: 平台类型

        Returns:
            WebDriver实例或None
        """
        try:
            # 确保服务器运行
            if not cls._ensure_server_running():
                logger.error("无法启动Appium服务器")
                return None

            # 构建URL和选项
            server_url = cls._get_server_url()
            options = cls._build_appium_options(platform)

            # 创建Driver实例
            driver = appium_webdriver.Remote(
                command_executor=server_url,
                options=options
            )

            # 设置隐式等待（智能等待）
            driver.implicitly_wait(2)  # 基础等待，配合缓存使用

            # 如果配置了窗口标题，切换到该窗口
            app_name = cls._config.get_app_name()
            if app_name and not cls._config.get_app_path():
                # 只在没有应用路径时才尝试切换（避免冲突）
                target_handle = cls._find_window_by_title(driver, app_name, timeout=10)
                if target_handle:
                    driver.switch_to.window(target_handle)
                    logger.info(f"已切换到目标窗口: {app_name}")
                else:
                    logger.warning(f"未找到目标窗口 '{app_name}'，当前窗口: {driver.title}")

            logger.info(f"Appium Driver初始化成功 ({platform})")
            return driver

        except Exception as e:
            logger.error(f"Appium Driver初始化失败: {e}")
            return None
    
    @classmethod
    def get_windows_driver(cls) -> Optional[RemoteWebDriver]:
        """获取Windows应用Driver"""
        return cls.get_driver('windows')
    
    @classmethod
    def find_app_window_handle(
        cls,
        driver: RemoteWebDriver,
        title_contains: str,
        title_excludes: Optional[list] = None,
    ) -> Optional[str]:
        """
        在当前会话的 window_handles 里按标题查找目标窗口句柄（十六进制字符串形式，
        NovaWindows 的 window_handles 会列出桌面所有顶层窗口，所以需要标题过滤）。

        Args:
            driver: WebDriver实例
            title_contains: 标题必须包含的子串
            title_excludes: 标题必须不包含的子串列表

        Returns:
            匹配窗口的句柄（如 '0x000f1234'），找不到返回 None
        """
        title_excludes = title_excludes or []
        try:
            handles = driver.window_handles
        except Exception as e:
            logger.warning(f"读取 window_handles 失败: {e}")
            return None

        for handle in handles:
            try:
                driver.switch_to.window(handle)
                t = driver.title or ''
            except Exception:
                continue
            if title_contains in t and not any(ex in t for ex in title_excludes):
                logger.info(f"找到目标窗口: handle={handle}, title='{t}'")
                return handle
        return None

    @classmethod
    def reattach_to_window(
        cls,
        driver: RemoteWebDriver,
        window_handle: str,
        platform: str = 'windows',
    ) -> bool:
        """
        关键修复：NovaWindows 的 driver.switch_to.window() 不会把会话的 UIA 搜索根
        切到新窗口。多窗口应用（登录 -> 主界面）必须用 appTopLevelWindow 重建会话。

        此方法会：
        1) 结束当前会话（不关闭应用，因为我们设了 shouldCloseApp=False）
        2) 用同一个 driver 对象发起一个新会话，capabilities 里带上 appTopLevelWindow
        3) 就地更新 driver.session_id / driver.caps，保持调用方引用不变

        Args:
            driver: 需要重绑定的 WebDriver 实例
            window_handle: 目标窗口的 HWND（十六进制字符串，如 '0x000f1234'）
            platform: 平台（目前只用于 Windows）

        Returns:
            True 表示重绑定成功
        """
        from selenium.webdriver.remote.command import Command

        old_session = driver.session_id
        logger.info(
            f"开始重绑定 NovaWindows 会话到 appTopLevelWindow={window_handle} "
            f"(旧 session_id={old_session})"
        )

        # 1) 结束旧会话（不 quit，以便继续复用 driver 对象）
        try:
            driver.execute(Command.DELETE_SESSION)
        except Exception as e:
            logger.warning(f"结束旧会话失败（忽略）: {e}")
        driver.session_id = None

        # 2) 构造新会话的 capabilities
        caps = {
            'platformName': 'Windows',
            'appium:automationName': 'NovaWindows',
            'appium:appTopLevelWindow': window_handle,
            'appium:shouldCloseApp': False,
            'appium:noReset': True,
        }
        parameters = {
            'capabilities': {
                'firstMatch': [{}],
                'alwaysMatch': caps,
            },
            # 旧 JSONWire 兼容（部分 Appium 版本会读取）
            'desiredCapabilities': {k.replace('appium:', ''): v for k, v in caps.items()},
        }

        # 3) 发起新会话并写回 driver
        try:
            response = driver.execute(Command.NEW_SESSION, parameters)
        except Exception as e:
            logger.error(f"重绑定新会话失败: {e}")
            return False

        value = response.get('value') if isinstance(response, dict) else None
        new_session_id = None
        new_caps = {}
        if isinstance(value, dict):
            new_session_id = value.get('sessionId') or response.get('sessionId')
            new_caps = value.get('capabilities') or value
        if not new_session_id and isinstance(response, dict):
            new_session_id = response.get('sessionId')
            new_caps = response.get('value', {}) or {}

        if not new_session_id:
            logger.error(f"无法从响应中解析 sessionId: {response}")
            return False

        driver.session_id = new_session_id
        try:
            driver.caps = new_caps
        except Exception:
            pass

        # 会话变了，必须清空元素缓存（旧 element_id 都失效）
        cls._element_cache.clear()
        logger.info(f"✅ 会话已重绑定，新 session_id={new_session_id}")
        return True

    @classmethod
    def attach_to_existing_app(cls, window_handle: str) -> Optional[RemoteWebDriver]:
        """
        连接到已运行的应用程序
        
        Args:
            window_handle: 窗口句柄
            
        Returns:
            WebDriver实例或None
        """
        try:
            if not cls._ensure_server_running():
                return None
            
            server_url = cls._get_server_url()
            
            options = AppiumOptions()
            options.set_capability('platformName', 'Windows')
            options.set_capability('deviceName', 'WindowsPC')
            options.set_capability('appTopLevelWindow', window_handle)
            options.set_capability('automationName', 'NovaWindows')
            
            driver = appium_webdriver.Remote(
                command_executor=server_url,
                options=options
            )
            
            logger.info(f"成功连接到现有应用，窗口句柄: {window_handle}")
            return driver
            
        except Exception as e:
            logger.error(f"连接现有应用失败: {e}")
            return None
    
    @classmethod
    def quit_driver(cls, driver: RemoteWebDriver) -> None:
        """
        安全退出Driver
        
        Args:
            driver: WebDriver实例
        """
        if driver:
            try:
                # 先清空缓存
                if cls._cache_enabled:
                    cls._element_cache.clear()
                
                driver.quit()
                logger.info("Driver已安全退出")
            except Exception as e:
                logger.error(f"退出Driver时出错: {e}")


# 便捷函数
def get_windows_driver() -> Optional[RemoteWebDriver]:
    """获取Windows应用Driver"""
    return DriverFactory.get_windows_driver()


def enable_element_cache(enabled: bool = True, timeout: int = 300) -> None:
    """启用元素缓存"""
    DriverFactory.enable_cache(enabled, timeout)


def clear_element_cache() -> None:
    """清空元素缓存"""
    DriverFactory.clear_cache()


if __name__ == "__main__":
    # 测试Driver工厂
    print("Appium Driver Factory - 测试")
    driver = DriverFactory.get_windows_driver()
    if driver:
        print("✓ Driver创建成功")
        driver.quit()
    else:
        print("✗ Driver创建失败")
