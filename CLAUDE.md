# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Windows桌面应用自动化测试框架（LoadMaster装车管理系统）。基于Page Object + Handler设计模式，支持NovaWindows Driver和Web自动化。

## 环境配置

### 必需依赖
```bash
# Node.js (Appium需要)
Node.js 18+

# 安装Appium 3.x和NovaWindows Driver
npm install -g appium@next
appium driver install --source=npm appium-novawindows-driver

# Python依赖
pip install -r requirements.txt
```

### 启动服务
```batch
start_appium.bat    # Windows启动Appium服务
start_winappdriver.bat  # 启动WinAppDriver
```

## 运行测试

```bash
# 运行所有测试
python -m pytest

# 运行特定文件
python -m pytest testCase/test_loadmaster.py

# 运行特定测试类/方法
python -m pytest testCase/test_loadmaster.py::TestLoadMaster::test_login_success

# 生成Allure报告
python -m pytest --alluredir=./report/result
```

## 架构分层

```
testCase (测试用例) → handlers (业务逻辑) → pageObject (页面对象) → BasePage
                                ↓                    ↓
                          config (配置)        utils (工具类)
```

- **testCase/**: pytest测试用例，调用Handler执行业务流程
- **handlers/**: 业务逻辑处理层，组合PageObject方法实现业务流程，包含导航逻辑
- **pageObject/**: 页面对象层，封装UI元素定位和操作（BasePage + 具体Page）
- **utils/**: 基础设施（DriverFactory, ConfigManager, DbHelper, Logger）
- **config/**: env.ini主配置文件
- **data/pages/**: YAML页面元素配置

## 核心模块

### BasePage (pageObject/base_page.py)
所有Page对象的基类，提供：
- 元素定位：`locate_element`, `click_element`, `send_keys_to_element`
- 窗口切换：`switch_to_window`, `locate_window`
- 表格操作：`get_table_data_as_json`, `click_table_row`, `query_table_after_operation`
- 弹窗处理：`handle_operation_prompt`, `handle_prompt_window`

### BaseHandler (handlers/base_handler.py)
所有Handler的基类，提供统一的页面对象初始化和导航混入。

### DriverFactory (utils/driver_factory.py)
管理Windows驱动生命周期，获取NovaWindows/Appium驱动实例。

### ConfigManager (utils/config_manager.py)
加载YAML页面配置，自动合并common_dialogs.yaml中的公共弹窗配置。

## 开发流程

### 新页面开发
1. 创建 `data/pages/{page_name}_page.yaml`（包含app_config和elements）
2. AI根据YAML生成PageObject类（继承BasePage）
3. AI生成Handler类（组合PageObject方法实现业务流程）
4. 生成test_data模板：`python utils/generate_test_data_template.py handlers.xxx_handler XxxHandler`
5. 编写测试用例

### YAML配置结构
```yaml
app_config:
  main_window_name: "窗口标题"
  head_keys: ["列1", "列2"]  # 表格表头

elements:
  button_name:
    automation_id: "btnId"
    type: "Button"
  content_table:
    name: "DataGridView"

test_data:
  scenario_name:
    _description: "场景描述"
    _method: "handler_method"
    param: "value"
```

## 关键约定

- 元素定位优先使用 `automation_id`
- Handler方法返回 `{'success': bool, 'error': str, ...}` 字典
- 使用 `handle_operation_prompt('confirm'/'cancel')` 处理通用弹窗
- 表格操作前需先 `switch_to_window` 切换到目标窗口

## 相关文档

- `docs/PAGE_DEVELOPMENT_GUIDE.md` - 页面开发完整指南
- `handlers/CLAUDE.md` - Handler模块详情
- `pageObject/CLAUDE.md` - PageObject模块详情
- `utils/CLAUDE.md` - 工具类模块详情