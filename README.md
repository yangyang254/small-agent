# small-agent

一个能「说」也会「做」的智能体（Agent）。用自然语言告诉它要做什么，它会自动调用工具，把待办真实写入本地文件。

- **能说** —— 基于大模型的自然语言多轮对话
- **会做** —— 通过 function calling 调用本地工具，实际读写文件
- **有记忆** —— 维护对话历史，能理解「刚才那个」「第二件事」这类指代

## 需求描述

日常记录待办时，普通聊天机器人只能回复「好的，已记录」，但并不会真的把内容保存下来。本项目要解决的是这个问题：让模型在理解用户意图之后，**真正去执行操作**——创建文件、写入内容、修改状态。

## 业务流

```
用户输入自然语言
      ↓
大模型理解意图，判断是否需要调用工具
      ↓
选择工具并生成参数（如 add_todo / list_todos / finish_todo）
      ↓
执行本地函数，读写 todo.md
      ↓
工具结果回传模型
      ↓
模型组织成自然语言回复用户
```

## 实现说明

| 模块 | 说明 |
|---|---|
| 工具层 | 三个普通 Python 函数：`add_todo` / `list_todos` / `finish_todo`，负责实际读写 `todo.md` |
| 工具声明 | `TOOLS_SCHEMA` 向模型描述每个工具的用途与参数，模型据此决定何时调用 |
| Agent 主循环 | `chat_once()` 循环处理「模型请求调用工具 → 执行 → 回传结果」，直到模型给出最终回复 |
| 对话记忆 | `messages` 列表贯穿全程累积，模型每轮都能看到之前的对话内容 |

技术栈：Python 3.8+ / OpenAI 兼容接口 / function calling。

## 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/yangyang254/small-agent.git
cd small-agent
pip install -r requirements.txt
```

### 2. 配置模型密钥

任选一家厂商，均兼容 OpenAI 接口。修改 `agent.py` 中的 `BASE_URL` 与 `MODEL` 即可切换：

| 厂商 | BASE_URL | MODEL | 备注 |
|---|---|---|---|
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat` | 默认配置 |
| 阿里通义 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` | 有免费额度 |
| 智谱 AI | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` | flash 版免费 |
| 硅基流动 | `https://api.siliconflow.cn/v1` | `Qwen/Qwen2.5-7B-Instruct` | 有免费模型 |

设置密钥（推荐用环境变量，不要写死在代码里）：

```bash
# Linux / macOS
export LLM_API_KEY=你的密钥

# Windows CMD
set LLM_API_KEY=你的密钥
```

### 3. 运行

```bash
python agent.py
```

## 使用示例

```
你：帮我记一下明天要交智能体作业
  [调用工具] add_todo({'content': '明天要交智能体作业'})
AI：已经帮你记下「明天要交智能体作业」了。

你：再加一条，周三下午小组开会
  [调用工具] add_todo({'content': '周三下午小组开会'})
AI：好的，已添加「周三下午小组开会」。

你：我现在有哪些待办？
  [调用工具] list_todos({})
AI：你目前有 2 条待办：
    1. 明天要交智能体作业
    2. 周三下午小组开会

你：开会那件事做完了
  [调用工具] finish_todo({'keyword': '开会'})
AI：已把「周三下午小组开会」标记为完成。
```

运行结束后，同目录下会生成 `todo.md`，内容为真实写入的结果：

```markdown
- [ ] 明天要交智能体作业
- [x] 周三下午小组开会
```

## 项目结构

```
small-agent/
├── agent.py           # 主程序：工具定义 + Agent 主循环 + 命令行入口
├── requirements.txt   # 依赖
├── .env.example       # 环境变量示例
├── .gitignore
├── LICENSE
└── README.md
```

## 扩展方向

- **新增工具**：在 `TOOL_MAP` 中注册函数，并在 `TOOLS_SCHEMA` 中补充描述即可。
- **接入外部 API**：编写 `get_weather(city)` 之类的函数，用 `requests` 调用第三方接口后注册。
- **图形界面**：使用 `streamlit` 将 `chat_once()` 接入网页聊天界面。
- **MCP 封装**：将工具按 Model Context Protocol 规范暴露为 Server。

## 常见问题

| 现象 | 原因与处理 |
|---|---|
| `AuthenticationError` | 密钥未正确设置，检查 `LLM_API_KEY` 环境变量是否生效 |
| 模型只口头应答、不调用工具 | `description` 描述不够明确，补充「当用户……时调用」的触发条件 |
| 中文输出乱码 | 确保所有 `open()` 均带有 `encoding="utf-8"` |

## License

[MIT](LICENSE)
