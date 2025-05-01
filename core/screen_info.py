from dataclasses import dataclass, field
from typing import List
import uiautomation as auto
import psutil
import json
import os
import re
from .debug import debug_print

@dataclass
class ElementInfo:
    item: auto.Control
    name: str = ""
    children: List['ElementInfo'] = field(default_factory=list)
    window_title: str = ""
    index: int = 0
    
    @property
    def type(self):
        return self.item.ControlTypeName

class ScreenInfoCollector:
    def __init__(self, max_text_length=500):
        self.elements = []
        self.optable = []
        self.g_index = 0
        self.result = ""
        self.max_text_length = max_text_length
        self.excluded_windows = self.load_excluded_windows()

    def load_excluded_windows(self):
        """加载需要从屏幕信息收集中排除的窗口列表"""
        try:
            if os.path.exists("config/exwindows.json"):
                with open("config/exwindows.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("excluded_windows", [])
            return []
        except Exception as e:
            print(f"加载排除窗口列表失败: {str(e)}")
            return []

    def is_window_excluded(self, window_title, window_process_name):
        """检查窗口是否应该被排除在收集范围外"""
        for exclusion in self.excluded_windows:
            try:
                title_match = False
                process_match = False
                title_pattern = exclusion.get("title_pattern", "")
                process_pattern = exclusion.get("process_pattern", "")
                if title_pattern:
                    title_match = re.search(title_pattern, window_title)
                if process_pattern:
                    process_match = re.search(process_pattern, window_process_name)
                if title_match or process_match:
                    debug_print(f"排除窗口: {window_title} {window_process_name}")
                    return True
            except re.error:
                continue
        return False

    def get_window_process_name(self, window):
        """获取窗口的进程名称"""
        try:
            pid = window.ProcessId if window else 0
            process = psutil.Process(pid)
            return process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            print(f"获取进程名称时出错: {e}")
            return "未知"

    def collect_elements(self, element, elements_list=None):
        """递归收集所有UI元素"""
        if elements_list is None:
            elements_list = []
        
        window = element.GetTopLevelControl()
        window_title = window.Name if window else ""
        
        element_info = ElementInfo(
            item=element,
            name=element.Name,
            window_title=window_title,
        )
        elements_list.append(element_info)
        self.elements = elements_list
        
        for child in element.GetChildren():
            self.collect_elements(child, element_info.children)

        return elements_list

    def get_window_elements(self, element):
        """获取窗口中的所有元素"""
        self.result = ""
        #debug_print("#get_window_elements" + " " + element.Name)
        self.elements = self.collect_elements(element)
        #debug_print("#collect_elements done")

        def process_elements(elements_list, indent=0):
            i = -1
            while i < len(elements_list):
                i += 1
                if i >= len(elements_list):
                    break
            
                # 处理嵌套的组控件
                if elements_list[i].type == "GroupControl" and len(elements_list[i].children) == 0:
                    elements_list.pop(i)
                    i -= 1
                    continue

                # 处理嵌套的文本控件，限制最大字数
                if elements_list[i].type == "TextControl":
                    j = i + 1
                    # 先合并所有连续的文本控件
                    while j < len(elements_list) and elements_list[j].type == "TextControl":
                        elements_list[i].name += elements_list[j].name
                        elements_list.pop(j)
                    
                    # 合并完成后检查长度，如果超过限制则截断
                    if len(elements_list[i].name) > self.max_text_length:
                        elements_list[i].name = elements_list[i].name[:self.max_text_length]

                # 处理嵌套的组控件
                while (elements_list[i].type == "GroupControl" and 
                       len(elements_list[i].children) == 1 and
                       elements_list[i].children[0].type != "GroupControl"):
                    elements_list[i] = elements_list[i].children[0]

                # 检查元素可见性
                """
                is_visible = self.is_element_visible(elements_list[i])
                if not is_visible:
                    continue
                """

                # 构建元素信息字符串
                typestr = elements_list[i].type.replace('Control', '')
                elements_list[i].index = self.g_index
                
                # 添加状态指示
                status = ""
                if "RadioButton" in typestr:
                    selectionItemPattern = elements_list[i].item.GetSelectionItemPattern()
                    status = " (已选中)" if selectionItemPattern.IsSelected else " (未选中)"

                elif "CheckBox" in typestr:
                    togglePattern = elements_list[i].item.GetPattern(auto.PatternId.TogglePattern)
                    if togglePattern:
                        state = togglePattern.ToggleState
                        if state == auto.ToggleState.On:
                            status = " (已选中)"
                        elif state == auto.ToggleState.Off:
                            status = " (未选中)"

                    
                elif "MenuItem" in typestr and not elements_list[i].item.IsEnabled:
                    status = " (不可用)"
                
                line = f"{self.g_index} " + f"({typestr}) {elements_list[i].name}{status}\n"
                if re.fullmatch(r'^\s*\d+\s+\(\*\)\n$', line):
                    continue

                element_info = ElementInfo(
                    item=elements_list[i].item,
                    name=elements_list[i].name,
                    window_title=elements_list[i].window_title,
                    index=self.g_index
                )

                if elements_list[i].name.strip():
                    self.result += line
                    self.optable.append(element_info)
                    
                self.g_index += 1

                if len(elements_list[i].children) > 0:
                    process_elements(elements_list[i].children, indent + 4)
                
        process_elements(self.elements)
        self.result = self.result.rstrip()
        return self.result

    def get_screen_info(self):
        """获取所有可见窗口及其元素的信息"""
        self.result = ""
        self.g_index = 0
        self.optable = []
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                windows = auto.WindowControl(searchDepth=1).GetParentControl().GetChildren() # type: ignore
                for window in windows:
                    try:
                        window_title = window.Name
                        window_process_name = self.get_window_process_name(window)
                        
                        if self.is_window_excluded(window_title, window_process_name):
                            continue
                            
                        self.result += f"窗口标题: {window_title}\n"
                        self.result += f"窗口所属进程名称: {window_process_name}\n"
                        
                        self.result += self.get_window_elements(window)
                        self.result += "\n\n"
                    except Exception as e:
                        print(f"处理窗口 {window.Name if hasattr(window, 'Name') else '未知'} 时出错: {str(e)}")
                        continue
                
                return self.result
                
            except Exception as e:
                print(f"获取屏幕信息时出错: {str(e)}。将在2秒后重试...")
                retry_count += 1
        
        print(f"重试{max_retries}次后失败")
        return "获取屏幕信息失败" 