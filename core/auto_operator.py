import pyautogui as pg
from pynput.keyboard import Controller
import time
import uiautomation as auto
import re
import traceback
from typing import Tuple, Optional, Union
from core.debug import debug_print

import time
import uiautomation as auto
from core.debug import debug_print

class ElementHelper:
    """控件辅助类，用于处理窗口激活和元素滚动等操作"""
    
    @staticmethod
    def is_element_in_window(element, window):
        """判断元素是否在窗口中"""
        try:

            element_rect = element.BoundingRectangle
            window_rect = window.BoundingRectangle
            
            # 检查元素矩形是否是窗口矩形的子集
            return (element_rect.left >= window_rect.left and
                    element_rect.right <= window_rect.right and
                    element_rect.top >= window_rect.top and
                    element_rect.bottom <= window_rect.bottom)
        except Exception:
            return False
    
    @staticmethod
    def activate_window(element):
        """激活元素所在的窗口"""
        debug_print("激活窗口")
        window = element.GetTopLevelControl()
        if not window: 
            return False
        window.SetFocus()
        time.sleep(0.5)
        return window
    
    @staticmethod
    def scroll_into_view(element, window):
        """使元素在视图中可见"""
        if not element.IsOffscreen:
            print(f"元素{element.Name}在视图中可见")
            return True
            
        # 滚动方式1：使用ScrollItemPattern
        try:
            element.GetScrollItemPattern().ScrollIntoView()
        except Exception as e:
            print(f"滚动1失败: {e}")
            pass 
        time.sleep(0.5)

        # 滚动方式2：使用鼠标滚轮1
        
        current_element = element
        while current_element != window:
            current_element = current_element.GetParentControl()
            if ElementHelper.is_element_in_window(current_element, window):
                break
        current_element = current_element.GetParentControl()
        print(current_element.Name)
        
        y_element = (element.BoundingRectangle.bottom + element.BoundingRectangle.top) / 2
        y_top_parent = (current_element.BoundingRectangle.bottom + current_element.BoundingRectangle.top) / 2
        
        diff_y1 = y_element - y_top_parent
        if diff_y1 > 0:
            up_or_down = element.WheelDown
        else:
            up_or_down = element.WheelUp
        up_or_down(ratioY=abs(diff_y1)/100)
        return True 

class AutoOperator:
    """自动化操作类，用于执行界面上的各种操作"""
    
    def __init__(self, screen_collector):
        self.keyboard = Controller()
        self.last_error = None
        self.screen_collector = screen_collector
        
    def execute_action(self, action_line: str) -> bool:
        if not action_line: return False

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
            for action, pattern in patterns.items():
                matches = re.findall(pattern, action_line)
                if not matches: continue
                    
                for match in matches:
                    return self._execute_single_action(action, match)
            
            return False
        except Exception as e:
            self._set_error(f"执行操作时发生错误: {e}")
            return False
            
    def _execute_single_action(self, action: str, match) -> bool:
        try:
            if action == "input":
                index = int(match[0])
                element = self._find_element_by_index(index)
                if not element: return False
                return self._handle_input(element, match[1])
            elif action == "press":
                return self._handle_press(match)
            else:
                index = int(match)
                element = self._find_element_by_index(index)
                if not element: return False
                return self._handle_mouse_action(element, action)
        except Exception as e:
            self._set_error(f"Error executing {action}: {str(e)}")
            return False

    def _find_element_by_index(self, target_index: int):
        for element_info in self.screen_collector.optable:
            if element_info.index == target_index:
                return element_info.item
        return None
        
    def _set_error(self, error_message: str):
        self.last_error = error_message
        debug_print(f"错误: {error_message}")
    
    def _handle_input(self, element, text: str) -> bool:
        # 预处理
        window = ElementHelper.activate_window(element)
        if not window: return False
        ElementHelper.scroll_into_view(element, window)

        # 输入文本
        self._handle_mouse_action(element, "click")
        pg.keyDown("ctrl")
        pg.keyDown("a")
        pg.keyUp("a")
        pg.keyUp("ctrl")
        pg.press("backspace")
        element.SendKeys(text)
        return True
        
    
    def _handle_press(self, key_combination):
        if isinstance(key_combination, tuple):
            key_combination = key_combination[0]
                
            if "+" in key_combination:
                keys = key_combination.split('+')
                for key in keys:
                    pg.keyDown(key)
                for key in reversed(keys):
                    pg.keyUp(key)
            else:
                pg.press(key_combination)
            return True
        return False
    
    def _handle_mouse_action(self, element, action: str) -> bool:
        # 预处理
        window = ElementHelper.activate_window(element)
        if not window: return False
        ElementHelper.scroll_into_view(element, window)

        # 点击元素
        if action == "click":
            element.Click()
        elif action == "double":
            element.DoubleClick()
        elif action == "right":
            element.RightClick()
        # todo: drag & move
        return True
    
    def get_last_error(self):
        return self.last_error
        
        
        
        
    
