# cr_utils

`cr_utils` 是一个实用工具库，包含日志管理、单例模式、注册表、成本管理、多功能函数和数据协议等模块，帮助你快速构建和管理 Python 项目。

## 主要模块和功能

### Logger

提供日志管理功能，方便统一日志输出和自定义日志行为。

### Singleton

实现单例模式，确保类只有一个实例。

### Registry

提供注册表功能，便于管理和调用各种插件或功能模块。

### CostManagers

成本管理工具，用于监控和管理资源消耗。

### Function 模块功能函数

- `set_variable_with_default`：设置环境变量。
- `killall_processes`：结束所有指定的进程。
- `make_main`：设置 debug 等功能。
- `make_async` / `make_sync`：辅助函数，实现异步和同步的转换。
- `custom_before_log` / `custom_after_log`：日志自定义钩子。
- `read_jsonl` / `write_jsonl`：读取和写入 JSON Lines 格式文件。
- `encode_image`：图片编码功能。

### Protocol

- `DataProto`：定义数据协议格式，规范数据交互，便于参数传递。

### LLM 相关

- `Chater`：聊天机器人或对话管理器。
- `extract_any_blocks`、`extract_code_blocks`、`extract_json_blocks`：从文本中提取不同格式的数据块。

## 安装

```bash
pip install cr_utils
```
