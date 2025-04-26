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
    def __init__(self):
        self.elements = []
        self.optable = []
        self.g_index = 0
        self.result = ""
        self.excluded_windows = self.load_excluded_windows()

    def load_excluded_windows(self):
        """Load the list of windows to exclude from screen info collection"""
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
        """Check if a window should be excluded from collection"""
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
        """Get the process name for a window"""
        try:
            pid = window.ProcessId if window else 0
            process = psutil.Process(pid)
            return process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            print(f"Error getting process name: {e}")
            return "Unknown"

    """
    def is_element_visible(self, element_info):
        # Check if an element is visible on screen
        try:
            rect = element_info.item.BoundingRectangle
            if rect.width == 0 or rect.height == 0:
                return False
            
            return True
        except Exception as e:
            print(f"检查控件可见性时出错: {str(e)}")
            return False
    """

    def collect_elements(self, element, elements_list=None):
        """Recursively collect all UI elements"""
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
        """Get all elements in a window"""
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
            
                #debug_print(f"process_elements {i}  " + elements_list[i].name)

                # Handle nested group controls
                if elements_list[i].type == "GroupControl" and len(elements_list[i].children) == 0:
                    elements_list.pop(i)
                    i -= 1
                    continue

                # Handle nested text controls
                if elements_list[i].type == "TextControl":
                    j = i + 1
                    while j < len(elements_list) and elements_list[j].type == "TextControl":
                        elements_list[i].name += elements_list[j].name
                        elements_list.pop(j)

                # Handle nested group controls
                while (elements_list[i].type == "GroupControl" and 
                       len(elements_list[i].children) == 1 and
                       elements_list[i].children[0].type != "GroupControl"):
                    elements_list[i] = elements_list[i].children[0]

                # Check element visibility
                """
                is_visible = self.is_element_visible(elements_list[i])
                if not is_visible:
                    continue
                """

                # Build element info string
                typestr = elements_list[i].type.replace('Control', '')
                elements_list[i].index = self.g_index
                
                # Add status indicators
                status = ""
                if typestr in ["CheckBox", "RadioButton"]:
                    status = " (已选中)" if elements_list[i].item.GetToggleState() else " (未选中)"
                elif typestr in ["Button", "MenuItem"] and not elements_list[i].item.IsEnabled:
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
        """Get information about all visible windows and their elements"""
        self.result = ""
        self.g_index = 0
        self.optable = []
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                windows = auto.WindowControl(searchDepth=1).GetParentControl().GetChildren()
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
                print(f"Error getting screen info: {str(e)}. Retrying in 2 seconds...")
                retry_count += 1
        
        print(f"重试{max_retries}次后失败")
        return "获取屏幕信息失败" 