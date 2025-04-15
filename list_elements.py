from dataclasses import dataclass, field
from typing import List
import pyautogui as pg
from pynput.keyboard import Controller
import uiautomation as auto
import pygetwindow as gw
import psutil
import time
import traceback  # 添加导入
import ctypes

# 添加 ElementInfo 数据类定义
@dataclass
class ElementInfo:
    item: auto.Control
    name: str = ""
    children: List['ElementInfo'] = field(default_factory=list)
    index: int = 0
    
    @property
    def type(self):
        return self.item.ControlTypeName

# 在文件顶部添加全局变量
elements = []
istab = 0
g_index = 0
result = ""

def get_window_process_name(window):
    """
    获取窗口所属的进程名称
    :param window: uiautomation 窗口对象
    :return: 进程名称
    """
    try:
        # 获取窗口的进程 ID
        pid = window.ProcessId
        # 获取进程对象
        process = psutil.Process(pid)
        # 返回进程名称
        return process.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
        print(f"Error getting process name: {e}")
        return "Unknown"


def collect_elements(element, elements_list=None):
    global elements
    if elements_list is None:
        elements_list = []
    
    # 收集当前元素的信息
    element_info = ElementInfo(item=element, name=element.Name)
    elements_list.append(element_info)
    elements = elements_list  # 更新全局变量
    
    # 递归收集子元素
    for child in element.GetChildren():
        collect_elements(child, element_info.children)

    return elements_list

def point_is_visible(x,y):
    try:
        # 获取当前激活窗口
        active_window = gw.getActiveWindow()
        
        # 获取激活窗口的客户区坐标
        client_rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetClientRect(active_window._hWnd, ctypes.byref(client_rect))
        
        # 将客户区坐标转换为屏幕坐标
        point = ctypes.wintypes.POINT(client_rect.left, client_rect.top)
        ctypes.windll.user32.ClientToScreen(active_window._hWnd, ctypes.byref(point))
        client_left, client_top = point.x, point.y
        
        point = ctypes.wintypes.POINT(client_rect.right, client_rect.bottom)
        ctypes.windll.user32.ClientToScreen(active_window._hWnd, ctypes.byref(point))
        client_right, client_bottom = point.x, point.y
        
        
        # 检查控件是否在客户区内
        return (x >= client_left and
                y >= client_top and
                x <= client_right and
                y <= client_bottom)
    
    except Exception as e:
        return False

def list_all_elements(element, indent=0, max_text_length=100):
    global istab
    indent = indent * istab
    global elements
    global g_index
    g_index = 0
    global result

    # 先收集所有元素信息
    elements = collect_elements(element)

    # 递归处理元素信息
    def process_elements(elements_list, indent):
        global g_index
        global istab
        indent = indent * istab
        global result

        i = 0
        while i < len(elements_list):

            # 删除没有子项的 GroupControl
            if elements_list[i].type == "GroupControl" and len(elements_list[i].children) == 0:
                elements_list.pop(i)
                continue

            # 合并连续的同级 TextControl
            if elements_list[i].type == "TextControl":
                j = i + 1
                while j < len(elements_list) and elements_list[j].type == "TextControl":
                    elements_list[i].name += elements_list[j].name
                    elements_list.pop(j)

            # 简化多层嵌套的、只有一个子项的 GroupControl
            while (elements_list[i].type == "GroupControl" and 
                   len(elements_list[i].children) == 1 and
                   elements_list[i].children[0].type != "GroupControl"):  # 添加条件防止无限循环
                elements_list[i] = elements_list[i].children[0]

            # 将当前元素的名称和控件类型添加到结果字符串
            typestr = elements_list[i].type.replace('Control', '')
            elements_list[i].index = g_index
            line = ' ' * indent + f"{g_index} " + f"({typestr}) {elements_list[i].name}\n"

            # 只有当括号外有内容时才添加该行
            if elements_list[i].name.strip():
                result += line
            g_index += 1

            # 处理子元素
            if len(elements_list[i].children) > 0:
                process_elements(elements_list[i].children, indent + 4)
            
            i += 1

    process_elements(elements, indent)
    # 去除多余的换行符
    result = result.rstrip()
    print(result)
    return result

def SetTab(tab):
    global istab
    istab = tab

def prepare_Window():
    active_window = gw.getActiveWindow()
    window_title = active_window.title
    
    if window_title == "Program Manager":
        auto.ShowDesktop()
    else:
        active_window.activate()
        active_window.restore()
        ctypes.windll.user32.BringWindowToTop(active_window._hWnd)

    ctypes.windll.user32.ShowWindow(active_window._hWnd, 3)



def GetScreenInfo():
    global result
    result = ""
    max_retries = 3  # 最大重试次数
    retry_count = 0

    #prepare_Window()
    while retry_count < max_retries:
        try:
            window = auto.GetForegroundControl()
            window_title = window.Name
            window_process_name = get_window_process_name(window)

            result += f"窗口标题: {window_title}\n"
            result += f"窗口所属进程名称: {window_process_name}\n"
            
            result += list_all_elements(window)
            
            return result
            
        except Exception as e:
            print(f"Error getting screen info: {str(e)}. Retrying in 2 seconds...")
            time.sleep(2)
            retry_count += 1
    
    print(f"重试{max_retries}次后失败")
    return "获取屏幕信息失败"

def PoceEp(index, actionType, inputText):
    global elements
    
    def find_element(elements_list, target_index):
        for element in elements_list:
            if element.index == target_index:
                return element.item
            found = find_element(element.children, target_index)
            if found:
                return found
        return None
    
    target_element = find_element(elements, index)
    
    if target_element is None:
        return {"success": False, "error": "目标元素未找到"}
    
    rect = target_element.BoundingRectangle
    if rect.width == 0 or rect.height == 0:
        return {"success": False, "error": "无效的元素尺寸"}
    
    center_x = (rect.left + rect.right) // 2
    center_y = (rect.top + rect.bottom) // 2

    if not point_is_visible(center_x, center_y):
        return {"success": False, "error": "目标元素不可见"}

    try:
        if actionType == "click":
            pg.click(x=center_x, y=center_y, clicks=1, interval=0.1, button='left')
        elif actionType == "double":
            pg.doubleClick(x=center_x, y=center_y, interval=0.1)
        elif actionType == "right":
            pg.rightClick(x=center_x, y=center_y, interval=0.1)
        elif actionType == "move":
            pg.moveTo(x=center_x, y=center_y, duration=0.2)
        elif actionType == "drag":
            pg.dragTo(x=center_x, y=center_y, duration=0.5, button='left')
        elif actionType == "input":
            pg.click(x=center_x, y=center_y, clicks=1, interval=0.1, button='left')
            time.sleep(0.5)
            keyboard = Controller()
            keyboard.type(inputText)
        elif actionType == "press":
            if inputText.find("+") != -1:
                keys = inputText.split('+')
                for key in keys:
                    pg.keyDown(key)
                for key in reversed(keys):
                    pg.keyUp(key)
            else:
                pg.press(inputText)
        return {"success": True, "error": None}
    except pg.FailSafeException:
        error_msg = "触发安全保护! 鼠标移动到角落."
        print(error_msg)
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"执行操作失败: {str(e)}"
        print(error_msg)
        print("Stack trace:")
        traceback.print_exc()
        return {
            "success": False,
            "error": error_msg,
            "stack_trace": traceback.format_exc()
        }

def process_elements(elements_list, indent=0):
    result = ""
    for i in range(len(elements_list)):
        try:
            # 尝试获取控件类型
            control_type = elements_list[i].ControlTypeName
            
            # 如果是GroupControl且没有子元素，则跳过
            if control_type == "GroupControl" and len(elements_list[i].children) == 0:
                continue
                
            # 添加控件信息
            result += " " * indent + f"{i}. {elements_list[i].Name} ({control_type})\n"
            
            # 递归处理子元素
            if len(elements_list[i].children) > 0:
                result += process_elements(elements_list[i].children, indent + 4)
        except Exception as e:
            # 如果发生错误，跳过该控件并记录错误
            result += " " * indent + f"{i}. [无法访问的控件] (Error: {str(e)})\n"
            continue
    return result

if __name__ == "__main__":
    # 调用 GetScreenInfo 并打印结果
    SetTab(0)
    print(GetScreenInfo())