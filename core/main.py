from .controller import Controller
from .utils import load_config
import traceback
import sys
import threading
import tkinter as tk
from tkinter import messagebox

def input_task(controller, root):
    """在另一个窗口中获取任务输入"""
    input_window = tk.Toplevel(root)
    input_window.title("输入任务")
    input_window.geometry("500x150")
    
    # 说明标签
    label = tk.Label(input_window, text="请输入要执行的任务:")
    label.pack(pady=10)
    
    # 任务输入框
    task_entry = tk.Entry(input_window, width=50)
    task_entry.pack(pady=5, padx=20, fill=tk.X)
    task_entry.focus_set()  # 设置焦点
    
    def submit_task():
        task = task_entry.get().strip()
        if task:
            input_window.destroy()
            controller.ui.add_action(f"收到新任务: {task}")
            controller.run_task_in_thread(task)
        else:
            messagebox.showwarning("警告", "请输入有效的任务描述")
    
    # 确认按钮
    submit_btn = tk.Button(input_window, text="开始执行", command=submit_task)
    submit_btn.pack(pady=10)
    
    # 处理回车键
    task_entry.bind("<Return>", lambda event: submit_task())

def create_main_menu(controller, root):
    """创建主菜单"""
    menubar = tk.Menu(root)
    
    # 任务菜单
    task_menu = tk.Menu(menubar, tearoff=0)
    task_menu.add_command(label="新建任务", command=lambda: input_task(controller, root))
    task_menu.add_command(label="停止当前任务", command=controller.stop_task)
    task_menu.add_separator()
    task_menu.add_command(label="退出", command=root.quit)
    menubar.add_cascade(label="任务", menu=task_menu)
    
    # 设置菜单
    root.config(menu=menubar)
    
    # 添加一个新任务按钮到UI界面
    button_frame = tk.Frame(root)
    button_frame.pack(fill=tk.X, padx=10, pady=5)
    
    new_task_btn = tk.Button(button_frame, text="新建任务", 
                            command=lambda: input_task(controller, root))
    new_task_btn.pack(side=tk.LEFT, padx=5)
    
    stop_task_btn = tk.Button(button_frame, text="停止任务", 
                             command=controller.stop_task)
    stop_task_btn.pack(side=tk.LEFT, padx=5)

def main():
    controller = None
    try:
        # 创建控制器实例
        controller = Controller()
        
        # 获取UI的根窗口并添加菜单
        root = controller.ui.root
        create_main_menu(controller, root)
        
        # 在主线程中启动UI（这会阻塞直到UI关闭）
        controller.start_ui()
        
    except Exception as e:
        print(f"程序初始化失败: {e}")
        print("错误详情:")
        print(traceback.format_exc())
        sys.exit(1)
    finally:
        # 清理资源
        if controller:
            controller.close()

if __name__ == "__main__":
    main() 