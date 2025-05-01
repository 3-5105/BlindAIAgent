import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time

class MonitorWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BlindAIAgent 监视器")
        self.root.geometry("900x600")
        
        # 创建数据队列和存储列表
        self.llm_queue = queue.Queue()
        self.action_queue = queue.Queue()
        self.screen_queue = queue.Queue()
        
        # 存储历史记录的列表
        self.llm_items = []
        self.action_items = []
        self.screen_items = []
        
        # 创建控制面板
        self.control_frame = ttk.Frame(self.root)
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 添加暂停/继续按钮
        self.pause_button = ttk.Button(self.control_frame, text="暂停", command=self.toggle_pause)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        # 添加自动激活窗口控制复选框
        self.auto_activate_var = tk.BooleanVar(value=False)  # 默认不选中
        self.auto_activate_check = ttk.Checkbutton(
            self.control_frame, 
            text="任务过程中自动激活窗口", 
            variable=self.auto_activate_var
        )
        self.auto_activate_check.pack(side=tk.LEFT, padx=15)
        
        """
        # 添加自动切换标签页控制
        self.auto_switch_var = tk.BooleanVar(value=True)  # 默认选中
        self.auto_switch_check = ttk.Checkbutton(
            self.control_frame, 
            text="自动切换到新消息标签", 
            variable=self.auto_switch_var, 
            command=self.toggle_auto_switch
        )
        self.auto_switch_check.pack(side=tk.LEFT, padx=15)
        """
        
        # 创建笔记本(选项卡)控件
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建LLM响应选项卡
        self.llm_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.llm_frame, text="LLM响应")
        
        # 分割LLM响应界面，左侧为列表，右侧为详情
        self.llm_paned = ttk.PanedWindow(self.llm_frame, orient=tk.HORIZONTAL)
        self.llm_paned.pack(fill=tk.BOTH, expand=True)
        
        # 添加列表框
        self.llm_list_frame = ttk.Frame(self.llm_paned)
        self.llm_listbox = tk.Listbox(self.llm_list_frame, width=30)
        self.llm_listbox.pack(fill=tk.BOTH, expand=True)
        self.llm_listbox.bind('<<ListboxSelect>>', self.on_llm_select)
        self.llm_paned.add(self.llm_list_frame)
        
        # 添加文本框
        self.llm_content_frame = ttk.Frame(self.llm_paned)
        self.llm_text = scrolledtext.ScrolledText(self.llm_content_frame, wrap=tk.WORD)
        self.llm_text.pack(fill=tk.BOTH, expand=True)
        self.llm_paned.add(self.llm_content_frame)
        
        # 创建执行操作选项卡
        self.action_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.action_frame, text="执行操作")
        
        # 分割执行操作界面
        self.action_paned = ttk.PanedWindow(self.action_frame, orient=tk.HORIZONTAL)
        self.action_paned.pack(fill=tk.BOTH, expand=True)
        
        # 添加列表框
        self.action_list_frame = ttk.Frame(self.action_paned)
        self.action_listbox = tk.Listbox(self.action_list_frame, width=30)
        self.action_listbox.pack(fill=tk.BOTH, expand=True)
        self.action_listbox.bind('<<ListboxSelect>>', self.on_action_select)
        self.action_paned.add(self.action_list_frame)
        
        # 添加文本框
        self.action_content_frame = ttk.Frame(self.action_paned)
        self.action_text = scrolledtext.ScrolledText(self.action_content_frame, wrap=tk.WORD)
        self.action_text.pack(fill=tk.BOTH, expand=True)
        self.action_paned.add(self.action_content_frame)
        
        # 创建屏幕信息选项卡
        self.screen_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.screen_frame, text="屏幕信息")
        
        # 分割屏幕信息界面
        self.screen_paned = ttk.PanedWindow(self.screen_frame, orient=tk.HORIZONTAL)
        self.screen_paned.pack(fill=tk.BOTH, expand=True)
        
        # 添加列表框
        self.screen_list_frame = ttk.Frame(self.screen_paned)
        self.screen_listbox = tk.Listbox(self.screen_list_frame, width=30)
        self.screen_listbox.pack(fill=tk.BOTH, expand=True)
        self.screen_listbox.bind('<<ListboxSelect>>', self.on_screen_select)
        self.screen_paned.add(self.screen_list_frame)
        
        # 添加文本框
        self.screen_content_frame = ttk.Frame(self.screen_paned)
        self.screen_text = scrolledtext.ScrolledText(self.screen_content_frame, wrap=tk.WORD)
        self.screen_text.pack(fill=tk.BOTH, expand=True)
        self.screen_paned.add(self.screen_content_frame)
        
        # 控制变量
        self.running = True
        self.paused = False
        
        # 暂停事件，用于挂起主线程
        self.pause_event = threading.Event()
        self.pause_event.set()  # 默认不暂停
        
        # 自动切换标签页标志
        self.auto_switch_tab = True
        
        # 设置定时器更新UI
        self.schedule_update()
    
    def toggle_auto_switch(self):
        """切换是否自动切换标签页"""
        self.auto_switch_tab = self.auto_switch_var.get()
    
    def bring_to_front(self):
        """将窗口置顶"""
        # 只有在自动激活选项启用时才执行
        if self.auto_activate_var.get():
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.attributes('-topmost', False)  # 将窗口置顶后恢复正常状态，避免一直保持在顶层
            self.root.focus_force()  # 强制获取焦点
    
    def toggle_pause(self):
        """切换暂停/继续状态"""
        self.paused = not self.paused
        if self.paused:
            self.pause_button.config(text="继续")
            self.pause_event.clear()  # 清除事件信号，阻塞等待
        else:
            self.pause_button.config(text="暂停")
            self.pause_event.set()  # 设置事件信号，恢复执行
    
    def wait_if_paused(self):
        """如果暂停，则等待恢复"""
        self.pause_event.wait()
    
    def on_llm_select(self, event):
        """LLM列表选择事件"""
        selection = event.widget.curselection()
        if selection:
            index = selection[0]
            if 0 <= index < len(self.llm_items):
                self.llm_text.delete(1.0, tk.END)
                self.llm_text.insert(tk.END, self.llm_items[index]['content'])
    
    def on_action_select(self, event):
        """操作列表选择事件"""
        selection = event.widget.curselection()
        if selection:
            index = selection[0]
            if 0 <= index < len(self.action_items):
                self.action_text.delete(1.0, tk.END)
                self.action_text.insert(tk.END, self.action_items[index]['content'])
    
    def on_screen_select(self, event):
        """屏幕信息列表选择事件"""
        selection = event.widget.curselection()
        if selection:
            index = selection[0]
            if 0 <= index < len(self.screen_items):
                self.screen_text.delete(1.0, tk.END)
                self.screen_text.insert(tk.END, self.screen_items[index]['content'])
    
    def add_llm_response(self, response):
        """添加LLM响应到队列"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        item = {
            'timestamp': timestamp,
            'content': f"[{timestamp}]\n{response}\n{'-'*50}\n"
        }
        self.llm_queue.put(item)
    
    def add_action(self, action):
        """添加执行的操作到队列"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        item = {
            'timestamp': timestamp,
            'content': f"[{timestamp}] {action}\n"
        }
        self.action_queue.put(item)
    
    def add_screen_info(self, info):
        """添加屏幕信息到队列"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        item = {
            'timestamp': timestamp,
            'content': f"[{timestamp}]\n{info}\n{'-'*50}\n"
        }
        self.screen_queue.put(item)
    
    def update_displays(self):
        """更新显示内容，由定时器调用"""
        if not self.running:
            return
            
        has_new_llm = False
        has_new_action = False
        has_new_screen = False
        
        # 更新LLM响应
        while not self.llm_queue.empty():
            item = self.llm_queue.get()
            self.llm_items.append(item)
            item_index = len(self.llm_items)
            self.llm_listbox.insert(tk.END, f"[{item_index}] {item['timestamp']}")
            has_new_llm = True
        
        # 更新执行操作
        while not self.action_queue.empty():
            item = self.action_queue.get()
            self.action_items.append(item)
            item_index = len(self.action_items)
            self.action_listbox.insert(tk.END, f"[{item_index}] {item['timestamp']}")
            has_new_action = True
        
        # 更新屏幕信息
        while not self.screen_queue.empty():
            item = self.screen_queue.get()
            self.screen_items.append(item)
            item_index = len(self.screen_items)
            self.screen_listbox.insert(tk.END, f"[{item_index}] {item['timestamp']}")
            has_new_screen = True
        
        # 如果有新信息且启用了自动切换标签页，则切换到对应标签页并选择最新项
        if self.auto_switch_tab:
            if has_new_llm:
                self.notebook.select(0)  # 切换到LLM响应选项卡
                last_index = len(self.llm_items) - 1
                self.llm_listbox.selection_clear(0, tk.END)
                self.llm_listbox.selection_set(last_index)
                self.llm_listbox.see(last_index)
                self.llm_text.delete(1.0, tk.END)
                self.llm_text.insert(tk.END, self.llm_items[last_index]['content'])
            elif has_new_action:
                self.notebook.select(1)  # 切换到执行操作选项卡
                last_index = len(self.action_items) - 1
                self.action_listbox.selection_clear(0, tk.END)
                self.action_listbox.selection_set(last_index)
                self.action_listbox.see(last_index)
                self.action_text.delete(1.0, tk.END)
                self.action_text.insert(tk.END, self.action_items[last_index]['content'])
            elif has_new_screen:
                self.notebook.select(2)  # 切换到屏幕信息选项卡
                last_index = len(self.screen_items) - 1
                self.screen_listbox.selection_clear(0, tk.END)
                self.screen_listbox.selection_set(last_index)
                self.screen_listbox.see(last_index)
                self.screen_text.delete(1.0, tk.END)
                self.screen_text.insert(tk.END, self.screen_items[last_index]['content'])
        
        # 重新调度更新
        self.schedule_update()
    
    def schedule_update(self):
        """调度更新，使用tkinter自己的after方法"""
        if self.running:
            self.root.after(100, self.update_displays)
    
    def start(self):
        """启动UI主循环，应在主线程调用"""
        self.root.mainloop()
    
    def close(self):
        """关闭窗口"""
        self.running = False
        self.root.destroy()

# 单独运行此文件时的测试代码
if __name__ == "__main__":
    window = MonitorWindow()
    
    # 添加一些测试数据
    window.add_llm_response("这是一个测试LLM响应\n包含多行内容")
    window.add_action("点击按钮：确定")
    window.add_screen_info("当前屏幕包含：登录界面\n用户名输入框\n密码输入框\n登录按钮")
    
    window.start() 