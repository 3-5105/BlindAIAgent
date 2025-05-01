from .screen_info import ScreenInfoCollector
from .llm_handler import LLMHandler
from .auto_operator import AutoOperator
from .utils import load_config
from .ui_monitor import MonitorWindow
import time
from core.debug import debug_print
import threading


class Controller:
    def __init__(self):
        self.config = load_config()
        self.screen_collector = ScreenInfoCollector()
        self.llm_handler = LLMHandler(self.config)
        self.auto_operator = AutoOperator(self.screen_collector)
        
        # 创建监视器窗口
        self.ui = MonitorWindow()
        self.ui.add_llm_response("自动化系统已启动\n等待任务输入...")
        
        # 任务标志和线程
        self.task_thread = None
        self.running = True
        
    def start_ui(self):
        """在主线程中启动UI"""
        self.ui.start()
        
    def run_task_in_thread(self, task_str):
        """在单独的线程中运行任务"""
        if self.task_thread and self.task_thread.is_alive():
            self.ui.add_action("已有任务在运行，请等待完成或重启程序")
            return
            
        self.task_thread = threading.Thread(target=self.run_task, args=(task_str,))
        self.task_thread.daemon = True
        self.task_thread.start()
        
    def run_task(self, task_str):
        """Main control loop that orchestrates the automation flow"""
        # Generate initial task outline
        outline = self.llm_handler.generate_outline(task_str)
        
        # 显示任务信息到UI
        if self.ui:
            self.ui.add_llm_response(f"任务: {task_str}\n\n大纲:\n{outline}")
        
        while self.running:
            try:
                # 检查是否暂停
                if self.ui:
                    self.ui.wait_if_paused()
                
                # 1. Collect screen information
                screen_info = self.screen_collector.get_screen_info()
                screen_info += "上一步操作已被执行，继续下一步操作\n\n"
                debug_print(f"屏幕信息: {screen_info}")
                
                # 显示屏幕信息到UI
                if self.ui:
                    self.ui.add_screen_info(screen_info)
                
                # 2. Send to LLM and get response
                llm_response = self.llm_handler.process_task(
                    task_str=task_str,
                    screen_info=screen_info,
                    outline=outline
                )
                
                if not llm_response:
                    print("未能获取有效的 LLM 响应。")
                    # 显示错误到UI
                    if self.ui:
                        self.ui.add_llm_response("未能获取有效的 LLM 响应")
                    continue
                
                # 显示LLM响应到UI
                if self.ui:
                    self.ui.add_llm_response(llm_response)
                
                # 3. Execute the actions
                for line in llm_response.split("\n"):
                    if not self.running:
                        break
                    
                    # 执行每个动作前检查是否暂停
                    if self.ui:
                        self.ui.wait_if_paused()
                        
                    if self.auto_operator.execute_action(line):
                        # 显示执行的操作到UI
                        if self.ui:
                            self.ui.add_action(f"执行成功: {line}")
                        time.sleep(2)  # Wait between actions
                    else:
                        # If action failed, send error to LLM
                        error = self.auto_operator.get_last_error()
                        if error:
                            self.llm_handler.set_last_error(error)
                            # 显示错误到UI
                            if self.ui:
                                self.ui.add_action(f"执行失败: {line}\n错误: {error}")
                        
            except Exception as e:
                print(f"执行任务时发生错误: {e}")
                # 显示异常到UI
                if self.ui:
                    self.ui.add_action(f"执行任务时发生异常: {str(e)}")
                time.sleep(1)  # Brief pause before retrying
            finally:
                self.ui.bring_to_front()
    
    def stop_task(self):
        """停止当前任务"""
        self.running = False
        if self.task_thread and self.task_thread.is_alive():
            self.task_thread.join(timeout=2)
        self.running = True
    
    def close(self):
        """关闭UI和清理资源"""
        self.running = False
        if self.task_thread and self.task_thread.is_alive():
            self.task_thread.join(timeout=2)
        if self.ui:
            self.ui.close()

def main():
    controller = Controller()
    try:
        user_input = input("请输入要执行的任务: ")
        controller.run_task(user_input)
    finally:
        controller.close()

if __name__ == "__main__":
    main() 