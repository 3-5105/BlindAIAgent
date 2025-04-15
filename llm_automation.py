from openai import OpenAI
from list_elements import GetScreenInfo, PoceEp
import re
import json
import time
import traceback

# 在文件顶部添加常量定义
MAX_HISTORY_RECORDS = 5  # 保留最近5次对话记录

try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
except FileNotFoundError:
    print("错误：未找到 config.json 文件")
    exit(1)
except json.JSONDecodeError:
    print("错误：config.json 文件格式不正确")
    exit(1)
except Exception as e:
    print(f"读取配置文件时发生错误: {e}")
    exit(1)

# 从配置文件中获取设置
openai_config = config['OpenAI']
prompts_config = config['Prompts']

api_key = openai_config['api_key']
model = openai_config.get('model', 'deepseek-chat')
base_url = openai_config.get('base_url', 'https://api.deepseek.com')

history_task = []
last_error = None  # 新增全局变量，用于存储上一次的错误信息

# 初始化 OpenAI 客户端
client = OpenAI(api_key=api_key, base_url=base_url)

task_prompt_system = prompts_config.get('task_prompt', {}).get('system', '')
task_prompt_user = prompts_config.get('task_prompt', {}).get('user', '')

def send_to_llm_task(task_str, screen_info, outline, retries=3):
    global history_task
    global last_error  # 引用全局变量
    
    # 准备错误信息
    error_info = ""
    if last_error:
        error_info = f"\n\n上次操作错误信息：{last_error}"
        last_error = None  # 清空错误信息
    
    for attempt in range(retries):
        try:
            # 创建当前任务的prompt，包含错误信息
            current_prompt = task_prompt_user.format(screen_info=screen_info) + error_info
            formatted_system_prompt = task_prompt_system.format(task_str=task_str, outline=outline)
            
            # 准备消息列表
            messages = [
                {"role": "system", "content": formatted_system_prompt},
                *history_task,  # 添加历史对话
                {"role": "user", "content": current_prompt}
            ]
            
            # 调用 API
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=False
            )
            
            # 更新历史任务
            history_task.extend([
                {"role": "user", "content": current_prompt},
                {"role": "assistant", "content": response.choices[0].message.content}
            ])
            
            # 如果历史记录超过最大限制，移除最旧的记录
            if len(history_task) > MAX_HISTORY_RECORDS * 2:  # 乘以2因为每次对话包含user和assistant两条记录
                history_task = history_task[-MAX_HISTORY_RECORDS * 2:]
            
            print("LLM 响应： #########################################################")
            print(response.choices[0].message.content)
            print("#########################################################")

            return response.choices[0].message.content
        except Exception as e:
            print(f"意外错误: {e}")
            break
    return None

def parse_and_execute(response):
    global last_error  # 引用全局变量
    
    if not response:
        return False

    patterns = {
        "input": r'input\((\d+),\s*"(.*?)"\)',
        "press": r"press\((.*?)\)",
        "click": r"click\((\d+)\)",
        "double": r"double\((\d+)\)",
        "right": r"right\((\d+)\)",
        "move": r"move\((\d+)\)",
        "drag": r"drag\((\d+)\)"
    }

    try:
        executed = False
        for action, pattern in patterns.items():
            matches = re.findall(pattern, response)
            for match in matches:
                try:
                    if action == "input":
                        index = int(match[0])
                        text = match[1]
                        result = PoceEp(index, action, text)
                    elif action == "press":
                        key = match
                        result = PoceEp(0, action, key)
                    else:
                        index = int(match)
                        result = PoceEp(index, action, "")
                    
                    if not result["success"]:
                        # 存储错误信息
                        last_error = result["error"]
                        if "stack_trace" in result:
                            last_error += f"\nStack trace:\n{result['stack_trace']}"
                        print(f"Action failed: {last_error}")
                    executed = True
                except Exception as e:
                    # 存储异常信息
                    last_error = f"Error executing action: {str(e)}\n{traceback.format_exc()}"
                    print(last_error)
        return executed
    except Exception as e:
        last_error = f"执行操作时发生错误: {e}\n{traceback.format_exc()}"
        print(last_error)
        return False

def run_task(task_str):
    global history_task
    # 初始化历史任务为列表
    history_task = []
    outline = generate_outline(task_str)

    while True:
        time.sleep(1)
        screen_info = GetScreenInfo()
        screen_info += "上一步操作已被执行，继续下一步操作\n\n"
        print("正在处理您的请求...")
        response = send_to_llm_task(task_str, screen_info, outline)

        if response:
            for line in response.split("\n"):
                print(f"LLM 响应：\n{line}")
                if parse_and_execute(line):
                    print("操作已执行。")
                    time.sleep(2)
        else:
            print("未能获取有效的 LLM 响应。")

def generate_outline(user_input):
    try:
        # Get outline prompts from config
        outline_prompt_system = prompts_config.get('outline_prompt', {}).get('system', '')
        outline_prompt_user = prompts_config.get('outline_prompt', {}).get('user', '')
        
        # Format prompts with user input
        system_prompt = outline_prompt_system
        user_prompt = outline_prompt_user.format(user_input=user_input)
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Call API
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False
        )
        
        # Return the generated outline
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"生成大纲时发生错误: {e}")
        return None

def main():
    user_input = input("请输入您的指令（或输入'退出'结束）：")
    if user_input.lower() == '退出':
        exit()
            
    time.sleep(2)
    print("正在处理您的请求...")
    run_task(user_input)

if __name__ == "__main__":
    main() 