from .screen_info import ScreenInfoCollector
from .llm_handler import LLMHandler
from .auto_operator import AutoOperator
from .utils import load_config
import time
from core.debug import debug_print
import re

class Controller:
    def __init__(self):
        self.config = load_config()
        self.screen_collector = ScreenInfoCollector()
        self.llm_handler = LLMHandler(self.config)
        self.auto_operator = AutoOperator(self.screen_collector)
        
    def run_task(self, task_str):
        """Main control loop that orchestrates the automation flow"""
        # Generate initial task outline
        outline = self.llm_handler.generate_outline(task_str)
        
        while True:
            try:
                
                # 1. Collect screen information
                screen_info = self.screen_collector.get_screen_info()
                screen_info += "上一步操作已被执行，继续下一步操作\n\n"
                debug_print(f"屏幕信息: {screen_info}")
                
                
                # 2. Send to LLM and get response
                llm_response = self.llm_handler.process_task(
                    task_str=task_str,
                    screen_info=screen_info,
                    outline=outline
                )
                


                if not llm_response:
                    print("未能获取有效的 LLM 响应。")
                    continue
                
                # 3. Execute the actions
                for line in llm_response.split("\n"):
                    if self.auto_operator.execute_action(line):
                        time.sleep(2)  # Wait between actions
                    else:
                        # If action failed, send error to LLM
                        error = self.auto_operator.get_last_error()
                        if error:
                            self.llm_handler.set_last_error(error)
                        
            except Exception as e:
                print(f"执行任务时发生错误: {e}")
                time.sleep(1)  # Brief pause before retrying

def main():
    controller = Controller()
    user_input = input("请输入要执行的任务: ")
    controller.run_task(user_input)

if __name__ == "__main__":
    main() 