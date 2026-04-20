# NovaWindows Driver 迁移指南

## 概述

本项目已从 Appium Windows Driver 迁移到 **NovaWindows Driver**，以获得更好的性能、稳定性和自动化效率。NovaWindows Driver 是一个专门为 Windows 桌面应用设计的 Appium 驱动，**需要 Appium 3.0.0 及以上版本**，解决了 WinAppDriver 已停止维护后的一系列问题。

### 主要改进

| 特性 | Appium-Windows-Driver (旧) | NovaWindows Driver (新) |
|------|---------------------------|--------------------------|
| 点击速度 | 8.5 秒 | 2.8 秒 (快 3 倍) |
| 输入速度 | 9.5 秒 | 4.0 秒 (快 2.4 倍) |
| XPath 优化 | 标准 UIAutomation | 自研优化算法 |
| RawView 支持 | 不支持 | 支持 |
| PowerShell 后端 | 无 | 内置 (无需额外配置) |
| 平台命令 | 基础 | 丰富 (40+ 命令) |

### NovaWindows Driver 优势

- **极速性能**：点击快 3 倍，输入快 2.4 倍
- **XPath 优化**：自研算法，无需牺牲性能即可使用 XPath 相对定位
- **RawView 元素**：可访问 ControlView/ContentView 隐藏的元素
- **增强输入**：解决键盘布局问题，支持快捷键和修饰键
- **平台命令**：40+ 平台特定命令（窗口操作、滚动、值设置等）
- **零配置**：仅需 PowerShell（Windows 已预装），无需开发者模式

## 环境要求

### 1. 系统要求
- Windows 10 或更高版本
- Node.js 18+ (Appium 3.x 需要)
- Python 3.8+
- 管理员权限（推荐）

### 2. 安装 Appium 3.x

> **注意**：NovaWindows Driver 需要 Appium 3.0.0 及以上版本，不兼容 Appium 2.x。

```bash
# 安装 Appium 3.x (测试版)
npm install -g appium@next

# 或安装最新稳定版 (如果已发布)
npm install -g appium@latest
```

#### 步骤3: 安装 NovaWindows Driver
```bash
appium driver install --source=npm appium-novawindows-driver

# 或安装特定版本
appium driver install --source=npm appium-novawindows-driver@1.3.1
```

#### 步骤4: 验证安装
```bash
# 检查 Appium 版本
appium --version

# 检查已安装的驱动
appium driver list
```

输出应类似：
```
$ appium --version
3.21.0

$ appium driver list
✔ Driver windows@5.1.10 is OK
✔ Driver novawindows@1.3.1 is OK
```

### 3. 更新 Python 依赖

```bash
pip install -r requirements.txt
```

## 启动 Appium

### 方法一：使用启动脚本 (推荐)
运行 `start_appium.bat` 脚本：
```batch
start_appium.bat
```

### 方法二：手动启动
```batch
appium --address 127.0.0.1 --port 4723 --log-level error
```

## 配置说明

### 1. 配置文件 (config/env.ini)

```ini
[windows_app]
# Windows应用配置 - NovaWindows Driver
location = D:\Program Files (x86)\微分科技\Load Studio\发油系统\LoadMaster.exe
app_name = 欢迎使用微分科技装车管理系统

# Appium服务器配置
appium_host = 127.0.0.1
appium_port = 4723

# NovaWindows 性能优化配置
element_cache_enabled = True          # 启用元素缓存
element_cache_timeout = 300         # 缓存超时（秒）
smart_wait_enabled = True           # 启用智能等待
smart_wait_poll_interval = 0.3       # 轮询间隔
implicit_wait = 2                    # 隐式等待（秒）
```

### 2. 页面元素配置 (data/pages/login_page.yaml)

```yaml
# 登录页面配置 - NovaWindows 格式
app_config:
  app_path: "D:\\Program Files (x86)\\微分科技\\Load Studio\\发油系统\\LoadMaster.exe"
  main_window_title: "欢迎使用微分科技装车管理系统"

elements:
  username_input:
    automation_id: "1001"  # 使用 AutomationId 定位

  password_input:
    automation_id: "txtUserPwd"

  login_button:
    automation_id: "btnLogin"

  main_window:
    automation_id: "frmMain"
    name: "装车管理系统"
```

## NovaWindows 专用 Capabilities

| Capability | 说明 | 示例 |
|------------|------|------|
| `platformName` | 必须��为 `Windows` | `Windows` |
| `automationName` | 必须设为 `NovaWindows` | `NovaWindows` |
| `smoothPointerMove` | 鼠标移动缓动函数 | `ease-in`, `cubic-bezier(0.42, 0, 0.58, 1)` |
| `delayBeforeClick` | 点击前延迟(毫秒) | `0` |
| `delayAfterClick` | 点击后延迟(毫秒) | `50` |
| `appTopLevelWindow` | 已运行应用的窗口句柄 | `12345`, `0x12345` |
| `shouldCloseApp` | 会话结束后是否关闭应用 | `true` |
| `appArguments` | 启动参数 | `--debug` |
| `appWorkingDir` | 工作目录 | `C:\MyApp` |
| `prerun` | 会话启动前执行的 PowerShell 脚本 | `{script: '...'} `|
| `postrun` | 会话停止后执行的 PowerShell 脚本 | `{command: '...'} `|

## 平台特定命令

NovaWindows 提供了丰富的平台命令，可通过 `driver.execute_script('windows: <command>', args)` 调用：

### 窗口操作
```python
# 最大化窗口
driver.execute_script('windows: maximize', window_element)

# 最小化窗口
driver.execute_script('windows: minimize', window_element)

# 关闭窗口
driver.execute_script('windows: close', window_element)

# 恢复窗口
driver.execute_script('windows: restore', window_element)
```

### 元素操作
```python
# 点击元素（直接调用 InvokePattern）
driver.execute_script('windows: invoke', element)

# 展开元素（如树节点、下拉框）
driver.execute_script('windows: expand', element)

# 折叠元素
driver.execute_script('windows: collapse', element)

# 滚动到视图
driver.execute_script('windows: scrollIntoView', element)

# 设置值（文本框等）
driver.execute_script('windows: setValue', [element, "新值"])

# 获取值
value = driver.execute_script('windows: getValue', element)

# 切换复选框
driver.execute_script('windows: toggle', checkbox_element)
```

### 选择模式操作
```python
# 选择元素
driver.execute_script('windows: select', element)

# 添加到选择
driver.execute_script('windows: addToSelection', element)

# 从选择中移除
driver.execute_script('windows: removeFromSelection', element)

# 获取已选项目
selected = driver.execute_script('windows: selectedItem', list_element)
```

### 剪贴板操作
```python
# 设置剪贴板
import base64
b64_content = base64.b64encode("Hello".encode()).decode()
driver.execute_script('windows: setClipboard', {'b64Content': b64_content, 'contentType': 'plaintext'})

# 获取剪贴板
content = driver.execute_script('windows: getClipboard', {'contentType': 'plaintext'})
```

### 鼠标操作
```python
# 点击（支持坐标、修饰键、多次点击）
driver.execute_script('windows: click', {
    'elementId': element.id,
    'modifierKeys': ['ctrl', 'shift'],
    'times': 2
})

# 滚动
driver.execute_script('windows: scroll', {
    'elementId': scrollable.id,
    'deltaY': 5
})

# 悬停
driver.execute_script('windows: hover', {
    'startElementId': element1.id,
    'endElementId': element2.id,
    'durationMs': 500
})

# 拖拽
driver.execute_script('windows: clickAndDrag', {
    'startElementId': source.id,
    'endElementId': target.id,
    'durationMs': 500
})
```

### 键盘操作
```python
# 自定义键盘输入
driver.execute_script('windows: keys', {
    'actions': [
        {'virtualKeyCode': 0x10, 'down': True},  # Shift 按下
        {'text': 'hello'},
        {'virtualKeyCode': 0x10, 'down': False}  # Shift 松开
    ]
})
```

### 文件操作
```python
# 删除文件
driver.execute_script('windows: deleteFile', {'path': 'C:\\Temp\\file.txt'})

# 删除文件夹
driver.execute_script('windows: deleteFolder', {'path': 'C:\\Temp\\MyFolder', 'recursive': True})
```

### 应用控制
```python
# 重新启动应用
driver.execute_script('windows: launchApp')

# 关闭应用
driver.execute_script('windows: closeApp')
```

## 迁移检查清单

- [ ] 安装 Appium 3.x: `npm install -g appium@next`
- [ ] 安装 NovaWindows Driver: `appium driver install --source=npm appium-novawindows-driver`
- [ ] 更新 Python 依赖: `pip install -r requirements.txt`
- [ ] 更新 `utils/driver_factory.py` 中的 `automationName` 配置（已自动更新）
- [ ] 更新配置文件 `config/env.ini`（如需要）
- [ ] 停止旧的 Appium 服务
- [ ] 启动新的 Appium 服务: `start_appium.bat`
- [ ] 运行测试验证

## 代码变更说明

### 1. Driver 获取方式 (无需修改)

```python
# 保持不变
from utils.driver_factory import DriverFactory
driver = DriverFactory.get_windows_driver()
```

### 2. 元素定位 (无需修改)

```python
# 保持不变
element = page.locate_element(automation_id="btnLogin")
element.click()
```

### 3. 新增功能

```python
# 使用 NovaWindows 平台命令
driver.execute_script('windows: setValue', [element, "新值"])
driver.execute_script('windows: scrollIntoView', element)
```

## 从 Appium-Windows-Driver 迁移的代码变化

### 核心变更：automationName

只需将 `automationName` 从 `Windows` 改为 `NovaWindows`：

**driver_factory.py 变更：**
```python
# 旧版本 (Appium Windows Driver)
options.set_capability('automationName', 'Windows')

# 新版本 (NovaWindows Driver)
options.set_capability('automationName', 'NovaWindows')
```

### 其他变更

1. **无需变更**：
   - 元素定位方式（automation_id, name, xpath 等）
   - 页面对象代码
   - Handler 业务逻辑
   - 测试用例

2. **可选变更**：
   - 使用 NovaWindows 平台命令优化性能
   - 配置 `delayBeforeClick`/`delayAfterClick` 优化稳定性

## 常见问题

### 1. 驱动安装失败
```bash
# 清除缓存后重试
appium driver uninstall novawindows
appium driver install --source=npm appium-novawindows-driver
```

### 2. 元素定位失败
- 使用 Inspect.exe 检查元素属性
- 尝试不同的定位策略（automation_id > name > xpath）
- 禁用缓存查看原始定位速度

### 3. NovaWindows 命令不工作
- 确保 `automationName` 设置为 `NovaWindows`
- 检查命令语法是否正确
- 查看 Appium 日志获取详细错误信息

### 4. PowerShell 脚本执行
如需使用 prerun/postrun 能力，需要在启动 Appium 时启用：
```bash
appium --allow-insecure=power_shell
```

## 更新日志

### v3.0.0 (2026-04-14)
- 从 Appium Windows Driver 迁移到 NovaWindows Driver
- 点击速度提升 3 倍（8.5秒 → 2.8秒）
- 输入速度提升 2.4 倍（9.5秒 → 4.0秒）
- 新增 40+ 平台特定命令
- 支持 RawView 元素访问
- 支持 XPath 优化算法
