"""
WinForm ComboBox 专用处理工具
解决WinForm应用中ComboBox选项获取和选择的问题
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import logging


class WinFormComboBoxHandler:
    """WinForm ComboBox专用处理器"""
    
    def __init__(self, driver, logger=None):
        self.driver = driver
        self.log = logger or logging.getLogger(__name__)
    
    def select_option(self, combobox_element, option_text, timeout=10):
        """
        选择ComboBox选项的主入口方法
        使用多种策略确保选择成功
        """
        self.log.info(f"开始选择WinForm ComboBox选项: {option_text}")
        
        # 策略1: 键盘导航选择（最可靠的WinForm方式）
        if self._select_by_keyboard_navigation(combobox_element, option_text):
            return True
        
        # 策略2: 点击展开 + 精确定位选择
        if self._select_by_click_and_locate(combobox_element, option_text, timeout):
            return True
        
        # 策略3: SendKeys直接输入（适用于可编辑ComboBox）
        if self._select_by_send_keys(combobox_element, option_text):
            return True
        
        # 策略4: 模拟用户操作序列
        if self._select_by_user_simulation(combobox_element, option_text):
            return True
        
        self.log.error(f"所有策略均失败，无法选择选项: {option_text}")
        return False
    
    def _select_by_keyboard_navigation(self, combobox_element, option_text):
        """
        策略1: 键盘导航选择
        这是WinForm ComboBox最可靠的选择方式
        """
        try:
            self.log.debug("尝试策略1: 键盘导航选择")
            
            # 1. 确保ComboBox获得焦点
            combobox_element.click()
            time.sleep(0.3)
            
            # 2. 按Home键回到第一个选项
            combobox_element.send_keys(Keys.HOME)
            time.sleep(0.2)
            
            # 3. 使用方向键遍历选项
            max_attempts = 20  # 最多尝试20个选项
            for i in range(max_attempts):
                # 获取当前选中的选项文本
                current_text = self._get_current_selected_text(combobox_element)
                self.log.debug(f"当前选项 {i+1}: {current_text}")
                
                # 检查是否匹配目标选项
                if current_text and option_text in current_text:
                    self.log.info(f"找到匹配选项: {current_text}")
                    # 按Enter确认选择
                    combobox_element.send_keys(Keys.ENTER)
                    time.sleep(0.3)
                    return True
                
                # 按下箭头键移动到下一个选项
                combobox_element.send_keys(Keys.ARROW_DOWN)
                time.sleep(0.2)
            
            self.log.debug("键盘导航未找到匹配选项")
            return False
            
        except Exception as e:
            self.log.debug(f"键盘导航策略失败: {e}")
            return False
    
    def _select_by_click_and_locate(self, combobox_element, option_text, timeout):
        """
        策略2: 点击展开 + 精确定位选择
        改进的点击定位策略，针对WinForm特性优化
        """
        try:
            self.log.debug("尝试策略2: 点击展开 + 精确定位选择")
            
            # 1. 强制展开下拉框
            self._force_expand_dropdown(combobox_element)
            
            # 2. 获取ComboBox位置信息
            cb_rect = self._get_element_rect(combobox_element)
            
            # 3. 使用多种定位策略查找选项
            options = self._find_dropdown_options(option_text, cb_rect, timeout)
            
            # 4. 点击匹配的选项
            if options:
                for option in options:
                    try:
                        if option.is_displayed() and option.is_enabled():
                            option.click()
                            self.log.info(f"成功点击选项: {option_text}")
                            time.sleep(0.3)
                            return True
                    except Exception as e:
                        self.log.debug(f"点击选项失败: {e}")
                        continue
            
            return False
            
        except Exception as e:
            self.log.debug(f"点击定位策略失败: {e}")
            return False
    
    def _select_by_send_keys(self, combobox_element, option_text):
        """
        策略3: SendKeys直接输入
        适用于可编辑的ComboBox
        """
        try:
            self.log.debug("尝试策略3: SendKeys直接输入")
            
            # 1. 清空并输入选项文本
            combobox_element.click()
            time.sleep(0.2)
            combobox_element.send_keys(Keys.CONTROL + "a")  # 全选
            time.sleep(0.1)
            combobox_element.send_keys(option_text)
            time.sleep(0.3)
            
            # 2. 按Tab或Enter确认
            combobox_element.send_keys(Keys.TAB)
            time.sleep(0.3)
            
            # 3. 验证是否成功
            current_text = self._get_current_selected_text(combobox_element)
            if current_text and option_text in current_text:
                self.log.info(f"SendKeys策略成功: {current_text}")
                return True
            
            return False
            
        except Exception as e:
            self.log.debug(f"SendKeys策略失败: {e}")
            return False
    
    def _select_by_user_simulation(self, combobox_element, option_text):
        """
        策略4: 模拟用户操作序列
        模拟真实用户的操作步骤
        """
        try:
            self.log.debug("尝试策略4: 模拟用户操作序列")
            
            # 1. 双击ComboBox（某些WinForm需要双击才能展开）
            combobox_element.click()
            time.sleep(0.1)
            combobox_element.click()
            time.sleep(0.5)
            
            # 2. 按F4键展开（WinForm标准快捷键）
            combobox_element.send_keys(Keys.F4)
            time.sleep(0.8)
            
            # 3. 输入选项的首字母快速定位
            if option_text:
                first_char = option_text[0].upper()
                combobox_element.send_keys(first_char)
                time.sleep(0.3)
                
                # 4. 使用方向键微调
                for _ in range(3):  # 最多尝试3次微调
                    current_text = self._get_current_selected_text(combobox_element)
                    if current_text and option_text in current_text:
                        combobox_element.send_keys(Keys.ENTER)
                        self.log.info(f"用户模拟策略成功: {current_text}")
                        return True
                    combobox_element.send_keys(Keys.ARROW_DOWN)
                    time.sleep(0.2)
            
            return False
            
        except Exception as e:
            self.log.debug(f"用户模拟策略失败: {e}")
            return False
    
    def _force_expand_dropdown(self, combobox_element):
        """强制展开下拉框"""
        try:
            # 方法1: 点击ComboBox
            combobox_element.click()
            time.sleep(0.3)
            
            # 方法2: 发送向下箭头键
            combobox_element.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.5)
            
            # 方法3: 发送Alt+向下箭头（标准展开快捷键）
            combobox_element.send_keys(Keys.ALT + Keys.ARROW_DOWN)
            time.sleep(0.5)
            
        except Exception as e:
            self.log.debug(f"强制展开下拉框失败: {e}")
    
    def _get_element_rect(self, element):
        """获取元素的位置信息"""
        try:
            rect_str = element.get_attribute("BoundingRectangle")
            if rect_str:
                return eval(rect_str)
        except Exception as e:
            self.log.debug(f"获取元素位置失败: {e}")
        return {"l": 0, "t": 0, "r": 1000, "b": 1000}
    
    def _find_dropdown_options(self, option_text, cb_rect, timeout):
        """使用多种策略查找下拉选项"""
        options = []
        
        # 策略A: WinForm特有的LISTBOX容器
        try:
            wait = WebDriverWait(self.driver, timeout)
            listbox_xpath = "//*[contains(@ClassName, 'WindowsForms10.LISTBOX') or contains(@ClassName, 'ComboLBox')]"
            listboxes = wait.until(EC.presence_of_all_elements_located((By.XPATH, listbox_xpath)))
            
            for listbox in listboxes:
                if listbox.is_displayed():
                    # 查找listbox内的选项
                    list_options = listbox.find_elements(By.XPATH, ".//*")
                    for opt in list_options:
                        opt_text = opt.get_attribute("Name") or opt.get_attribute("LegacyIAccessible.Value") or ""
                        if option_text in opt_text:
                            options.append(opt)
                            
        except Exception as e:
            self.log.debug(f"LISTBOX策略失败: {e}")
        
        # 策略B: 直接搜索包含目标文本的元素
        try:
            text_xpath = f"//*[(contains(@Name, '{option_text}') or contains(@LegacyIAccessible.Value, '{option_text}')) and @IsOffscreen='false']"
            text_options = self.driver.find_elements(By.XPATH, text_xpath)
            options.extend([opt for opt in text_options if opt.is_enabled()])
        except Exception as e:
            self.log.debug(f"文本搜索策略失败: {e}")
        
        # 策略C: 查找位置相关的选项（在ComboBox下方）
        try:
            all_elements = self.driver.find_elements(By.XPATH, "//*[@IsOffscreen='false']")
            for elem in all_elements:
                try:
                    elem_rect = self._get_element_rect(elem)
                    # 检查元素是否在ComboBox下方
                    if (elem_rect["t"] > cb_rect["b"] and 
                        elem_rect["l"] >= cb_rect["l"] - 50 and 
                        elem_rect["r"] <= cb_rect["r"] + 50):
                        
                        elem_text = elem.get_attribute("Name") or elem.get_attribute("LegacyIAccessible.Value") or ""
                        if option_text in elem_text:
                            options.append(elem)
                except:
                    continue
        except Exception as e:
            self.log.debug(f"位置相关策略失败: {e}")
        
        return options
    
    def _get_current_selected_text(self, combobox_element):
        """获取当前选中的选项文本"""
        try:
            # 尝试多种属性获取文本
            text = (combobox_element.get_attribute("Name") or 
                   combobox_element.get_attribute("LegacyIAccessible.Value") or 
                   combobox_element.get_attribute("Value.Value") or "")
            return text.strip()
        except Exception as e:
            self.log.debug(f"获取当前选中文本失败: {e}")
            return ""
    
    def verify_selection(self, combobox_element, expected_text):
        """验证选择结果"""
        try:
            time.sleep(0.3)  # 等待选择生效
            current_text = self._get_current_selected_text(combobox_element)
            is_match = expected_text in current_text if current_text else False
            self.log.debug(f"验证选择结果: 期望='{expected_text}', 实际='{current_text}', 匹配={is_match}")
            return is_match
        except Exception as e:
            self.log.debug(f"验证选择结果失败: {e}")
            return False