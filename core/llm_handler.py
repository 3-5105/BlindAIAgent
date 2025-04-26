from openai import OpenAI
import traceback

class LLMHandler:
    def __init__(self, config):
        self.config = config
        self.history_task = []
        self.last_error = None
        self.MAX_CHARS = 30000
        
        # Initialize OpenAI client
        openai_config = config['OpenAI']
        self.api_key = openai_config['api_key']
        self.model = openai_config.get('model', 'deepseek-chat')
        self.base_url = openai_config.get('base_url', 'https://api.deepseek.com')
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        # Load prompts
        self.task_prompt_system = config['Prompts'].get('task_prompt', {}).get('system', '')
        self.task_prompt_user = config['Prompts'].get('task_prompt', {}).get('user', '')
        self.MAX_HISTORY_RECORDS = 5

    def _extract_summary(self, content):
        """Extract summary content marked with sum() from the response"""
        import re
        summaries = re.findall(r'sum\((.*?)\)', content, re.DOTALL)
        if summaries:
            return ' '.join(summaries)
        return None

    def _truncate_history(self):
        """Truncate history if total characters exceed MAX_CHARS"""
        total_chars = sum(len(msg["content"]) for msg in self.history_task)
        while total_chars > self.MAX_CHARS and self.history_task:
            # Remove oldest pair of messages
            if len(self.history_task) >= 2:
                total_chars -= len(self.history_task[0]["content"]) + len(self.history_task[1]["content"])
                self.history_task = self.history_task[2:]
            else:
                self.history_task = []
                break

    def process_task(self, task_str, screen_info, outline, retries=3):
        """Process the task with LLM and return the response"""
        for attempt in range(retries):
            try:
                # Create current prompt with error info if any
                error_info = f"\n\n上次操作错误信息：{self.last_error}" if self.last_error else ""
                self.last_error = None  # Clear error info
                
                current_prompt = self.task_prompt_user.format(screen_info=screen_info) + error_info
                formatted_system_prompt = self.task_prompt_system.format(task_str=task_str, outline=outline)
                
                # Prepare message list
                messages = [
                    {"role": "system", "content": formatted_system_prompt},
                    *self.history_task,  # Add conversation history
                    {"role": "user", "content": current_prompt}
                ]
                
                # Call API
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=False
                )
                
                # Get and print LLM response
                llm_response = response.choices[0].message.content
                print("LLM Response:\n", llm_response)
                
                # Extract summary and update history only if summary exists
                summary = self._extract_summary(llm_response)
                if summary:
                    self.history_task.extend([
                        {"role": "user", "content": current_prompt},
                        {"role": "assistant", "content": summary}
                    ])
                    # Truncate history if needed
                    self._truncate_history()
                
                return llm_response
                
            except Exception as e:
                print(f"LLM处理错误: {e}")
                if attempt == retries - 1:
                    return None

    def generate_outline(self, user_input):
        """Generate task outline using LLM"""
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
                messages=messages,
                stream=False
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"生成大纲时发生错误: {e}")
            return None

    def set_last_error(self, error, stack_trace=None):
        """Set the last error message"""
        self.last_error = error
        if stack_trace:
            self.last_error += f"\nStack trace:\n{stack_trace}" 