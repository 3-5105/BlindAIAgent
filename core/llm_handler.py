from openai import OpenAI
import traceback
import re

class LLMHandler:
    def __init__(self, config):
        self.config = config
        self.history_task = []
        self.last_error = None
        self.MAX_CHARS = 30000
        
        # 初始化OpenAI客户端
        openai_config = config['OpenAI']
        self.api_key = openai_config['api_key']
        self.model = openai_config.get('model', 'deepseek-chat')
        self.base_url = openai_config.get('base_url', 'https://api.deepseek.com')
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        # 加载提示词
        self.task_prompt_system = config['Prompts'].get('task_prompt', {}).get('system', '')
        self.task_prompt_user = config['Prompts'].get('task_prompt', {}).get('user', '')
        self.MAX_HISTORY_RECORDS = 5

    def _extract_summary(self, content):
        """从响应中提取标记为sum()的摘要内容"""
        import re
        summaries = re.findall(r'sum\((.*?)\)', content, re.DOTALL)
        if summaries:
            return ' '.join(summaries)
        return None
        
    def _remove_think_tags(self, content):
        """移除响应中<think></think>标签内的内容"""
        return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)

    def _truncate_history(self):
        """如果总字符数超过MAX_CHARS，则截断历史记录"""
        total_chars = sum(len(msg["content"]) for msg in self.history_task)
        while total_chars > self.MAX_CHARS and self.history_task:
            # 确保历史记录按用户-助手对的方式移除
            if len(self.history_task) >= 2:
                total_chars -= len(self.history_task[0]["content"]) + len(self.history_task[1]["content"])
                self.history_task = self.history_task[2:]
            else:
                # 如果只剩一条消息，直接清空
                total_chars -= len(self.history_task[0]["content"])
                self.history_task = []
                break

    def process_task(self, task_str, screen_info, outline, retries=3):
        """使用LLM处理任务并返回响应"""
        for attempt in range(retries):
            try:
                # 创建当前提示词，如有错误则包含错误信息
                error_info = f"\n\n上次操作错误信息：{self.last_error}" if self.last_error else ""
                self.last_error = None  # 清除错误信息
                
                current_prompt = self.task_prompt_user.format(screen_info=screen_info) + error_info
                formatted_system_prompt = self.task_prompt_system.format(task_str=task_str, outline=outline)
                
                # 准备消息列表
                messages = [
                    {"role": "system", "content": formatted_system_prompt},
                    *self.history_task,  # 添加对话历史
                    {"role": "user", "content": current_prompt}
                ]
                
                # 调用API
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=False
                )
                
                # 获取并打印LLM响应
                llm_response = response.choices[0].message.content
                print("LLM Response:\n", llm_response)
                
                # 移除<think>标签内容（如果存在）
                filtered_response = self._remove_think_tags(llm_response)
                
                # 更新历史记录
                self.history_task.extend([
                    {"role": "user", "content": current_prompt},
                    {"role": "assistant", "content": filtered_response}
                ])
                
                # 需要时截断历史记录
                self._truncate_history()
                
                return filtered_response
                
            except Exception as e:
                print(f"LLM处理错误: {e}")
                if attempt == retries - 1:
                    return None

    def generate_outline(self, user_input):
        """使用LLM生成任务大纲"""
        try:
            outline_prompt_system = self.config['Prompts'].get('outline_prompt', {}).get('system', '')
            outline_prompt_user = self.config['Prompts'].get('outline_prompt', {}).get('user', '')
            
            system_prompt = outline_prompt_system
            user_prompt = outline_prompt_user.format(user_input=user_input)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages, # type: ignore
                stream=False
            ) # type: ignore
            
            response_content = response.choices[0].message.content.strip()
            # 移除<think>标签内容
            filtered_response = self._remove_think_tags(response_content)
            
            return filtered_response
        except Exception as e:
            print(f"生成大纲时发生错误: {e}")
            return None

    def set_last_error(self, error, stack_trace=None):
        """设置最近的错误信息"""
        self.last_error = error
        if stack_trace:
            self.last_error += f"\nStack trace:\n{stack_trace}" 