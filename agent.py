# -*- coding: utf-8 -*-
"""待办清单智能体：基于 function calling 调用本地工具管理待办事项。"""

import json
import os

from openai import OpenAI

# 模型接入配置
API_KEY = os.getenv("LLM_API_KEY", "")
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"

# 待办数据的持久化文件
TODO_FILE = "todo.md"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def add_todo(content: str) -> str:
    """向待办文件追加一条未完成事项。"""
    with open(TODO_FILE, "a", encoding="utf-8") as f:
        f.write(f"- [ ] {content}\n")
    return f"已添加待办：{content}"


def list_todos() -> str:
    """读取待办文件的全部内容。"""
    if not os.path.exists(TODO_FILE):
        return "当前没有任何待办事项。"

    with open(TODO_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()

    return content or "当前没有任何待办事项。"


def finish_todo(keyword: str) -> str:
    """将包含关键词的未完成事项标记为已完成。"""
    if not os.path.exists(TODO_FILE):
        return "没有找到待办文件。"

    with open(TODO_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    changed = False
    new_lines = []
    for line in lines:
        if keyword in line and "[ ]" in line:
            new_lines.append(line.replace("- [ ]", "- [x]"))
            changed = True
        else:
            new_lines.append(line)

    with open(TODO_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return f"已标记完成：{keyword}" if changed else f"没有找到包含「{keyword}」的待办。"


# 工具名到实现函数的映射，供调用分发使用
TOOL_MAP = {
    "add_todo": add_todo,
    "list_todos": list_todos,
    "finish_todo": finish_todo,
}

# 工具声明，description 决定模型何时选择该工具
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "add_todo",
            "description": "当用户想要新增、记录、添加一条待办事项或任务时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "待办的具体内容"}
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_todos",
            "description": "当用户想查看、列出、朗读当前所有待办事项时调用。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish_todo",
            "description": "当用户表示某件事已经完成、做完了、要勾掉时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "要标记完成的待办里的关键词"}
                },
                "required": ["keyword"],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "你是一个待办清单助理。用户会用自然语言让你管理任务。"
    "你需要判断是否需要调用工具来完成用户的要求，"
    "调用完成后用简洁自然的中文告诉用户结果。"
)


def chat_once(messages: list) -> str:
    """执行一轮对话，处理工具调用直到模型给出最终回复。

    messages 会被就地修改，用于在多轮之间保留上下文。
    """
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
        )
        msg = response.choices[0].message

        # 模型请求调用工具：执行后把结果回传，继续下一轮推理
        if msg.tool_calls:
            messages.append(msg)

            for call in msg.tool_calls:
                fn_name = call.function.name

                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                print(f"  [调用工具] {fn_name}({args})")

                if fn_name in TOOL_MAP:
                    result = TOOL_MAP[fn_name](**args)
                else:
                    result = f"未知工具：{fn_name}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": str(result),
                })

            continue

        # 模型未请求工具，视为最终回复
        messages.append({"role": "assistant", "content": msg.content})
        return msg.content


def main():
    """命令行入口，维护对话历史并循环接收输入。"""
    if not API_KEY:
        print("请先设置环境变量 LLM_API_KEY")
        return

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("=" * 50)
    print("待办助理已启动，输入 exit 退出")
    print("试试说：帮我记一下明天要交作业")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "退出"):
            print("再见！")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            print(f"\nAI：{chat_once(messages)}")
        except Exception as e:
            print(f"\n[出错了] {e}")
            # 移除本次输入，避免失败请求污染上下文
            messages.pop()


if __name__ == "__main__":
    main()
