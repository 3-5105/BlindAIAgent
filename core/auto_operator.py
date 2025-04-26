import pyautogui as pg
from pynput.keyboard import Controller
import pygetwindow as gw
import time
import uiautomation as auto
import re
import traceback
from core.debug import debug_print

class AutoOperator:
    def __init__(self, screen_collector):
        self.keyboard = Controller()
        self.last_error = None
        self.screen_collector = screen_collector
        
    def execute_action(self, action_line):
        """Execute a single action command"""
        if not action_line:
            return False

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
                for match in matches:
                    try:
                        if action == "input":
                            debug_print(f"执行输入操作: {match[0]} {match[1]}")
                            return self._handle_input(int(match[0]), match[1])
                        elif action == "press":
                            debug_print(f"执行按键操作: {match}")
                            return self._handle_press(match)
                        else:
                            debug_print(f"执行鼠标操作: {match} {action}")
                            return self._handle_mouse_action(int(match), action)
                    except Exception as e:
                        self.last_error = f"Error executing {action}: {str(e)}\n{traceback.format_exc()}"
                        return False
            return False
        except Exception as e:
            self.last_error = f"执行操作时发生错误: {e}\n{traceback.format_exc()}"
            return False

    def _find_element_by_index(self, target_index):
        """Find element in the elements tree by its index
        def find_element(elements_list, index):
            for element in elements_list:
                debug_print(f"查找元素: {element.index} {element.name}")
                if element.index == index:
                    return element
                if element.children:
                    found = find_element(element.children, index)
                    if found:
                        return found
            return None
        
        return find_element(self.screen_collector.elements, target_index)
        """
        for element in self.screen_collector.optable:
            if element.index == target_index:
                debug_print(f"查找元素: {element.index} {element.name}")
                return element
        return None

    def _get_element_center(self, element):
        """Get the center coordinates of an element"""
        try:
            rect = element.item.BoundingRectangle
            center_x = (rect.left + rect.right) // 2
            center_y = (rect.top + rect.bottom) // 2
            return center_x, center_y
        except Exception as e:
            self.last_error = f"Failed to get element coordinates: {str(e)}"
            return None
        
    def _try_to_scroll(self, element: auto.Control, top_parent: auto.Control):
        """Try to scroll the element into view"""
        def scroll(element: auto.Control, top_parent: auto.Control):
            """Try to scroll the element into view using iterative approach"""
            current_element = element
            while current_element != top_parent:
                try:
                    current_element.GetScrollItemPattern().ScrollIntoView()
                    return True
                except Exception:
                    current_element = current_element.GetParentControl()
            return False

        def scroll_byhand(element: auto.Control, top_parent: auto.Control):
            """Try to scroll the element into view by hand"""
            current_element = element
            while current_element != top_parent and current_element.IsOffscreen == False:
                current_element = current_element.GetParentControl()
            if current_element == top_parent:
                return False

            # x_element = (element.BoundingRectangle.right + element.BoundingRectangle.left) / 2
            y_element = (element.BoundingRectangle.bottom + element.BoundingRectangle.top) / 2

            # x_top_parent = (top_parent.BoundingRectangle.right + top_parent.BoundingRectangle.left) / 2
            y_top_parent = (top_parent.BoundingRectangle.bottom + top_parent.BoundingRectangle.top) / 2

            diff_y1 = y_element - y_top_parent
            if diff_y1 > 0:
                up_or_down = element.WheelDown
            else:
                up_or_down = element.WheelUp
            up_or_down(y = diff_y1)

            try:
                return scroll(element, top_parent)
            except Exception:
                return scroll_byhand(element, top_parent)

            return True
        
        try:
            return scroll(element, top_parent)
        except Exception:
            return scroll_byhand(element, top_parent)
        
    def _make_window_visible(self, element):
        """Make the window containing the element visible"""
        
        # Get the target window
        target_window = element.item.GetTopLevelControl()
        
        # Only activate window if current focus is different
        try:
            self._activate_window(element)
        except Exception as e:
            debug_print(f"尝试检查窗口焦点失败: {e}")
            self._activate_window(element)

        if not element.item.IsOffscreen:
            return True

        try:
            element.item.GetScrollItemPattern().ScrollIntoView()
            return True
        except Exception as e:
            debug_print(f"尝试直接滚动失败: {e}")
            
            # Try to find nearest visible ancestor and scroll
        try:
            self._try_to_scroll(element.item, target_window)
            return True
        except Exception as e:
            debug_print(f"尝试手动滚动失败: {e}")
                
        return False

    def _activate_window(self, element):
        """Activate the window containing the element"""

        window = element.item.GetTopLevelControl()
        if window:
            window.SetFocus()
            time.sleep(0.5)
            return True
        return False

    def _handle_input(self, element_index, text):
        """Handle input operation"""
        try:
            """
            # First click the target element
            if not self._handle_mouse_action(element_index, "click"):
                return False
            
            # Then type the text
            time.sleep(0.5)
            self.keyboard.type(text)
            """
            element = self._find_element_by_index(element_index)
            self._make_window_visible(element)
            element.item.Click()
            element.item.SendKeys(text)

            return True
        except Exception as e:
            self.last_error = f"输入操作失败: {str(e)}"
            debug_print(f"执行输入操作失败: {self.last_error}")
            return False

    def _handle_press(self, key_combination):
        """Handle keyboard press operation"""
        try:
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
        except Exception as e:
            self.last_error = f"按键操作失败: {str(e)}"
            debug_print(f"执行按键操作失败: {self.last_error}")
            return False

    def _handle_mouse_action(self, element_index, action_type):
        """Handle mouse operations"""
        try:
            # Find the target element
            element = self._find_element_by_index(element_index)
            if not element:
                self.last_error = f"Element with index {element_index} not found"
                debug_print(f"执行鼠标操作失败: {self.last_error}")
                return False

            # Get element coordinates
            coords = self._get_element_center(element)
            if not coords:
                self.last_error = "Failed to get element coordinates"
                debug_print(f"执行鼠标操作失败: {self.last_error}")
                return False

            # Activate the window if needed
            if not self._make_window_visible(element):
                self.last_error = "Failed to make window visible"
                debug_print(f"执行鼠标操作失败: {self.last_error}")
                return False

            x, y = coords
            debug_print(f"执行鼠标操作: {x} {y} {action_type}")
            # Perform the mouse action
            if action_type == "click":
                element.item.Click()
                # pg.click(x=x, y=y, clicks=1, interval=0.1, button='left')
            elif action_type == "double":
                element.item.DoubleClick()
                # pg.doubleClick(x=x, y=y, interval=0.1)
            elif action_type == "right":
                element.item.RightClick()
                # pg.rightClick(x=x, y=y, interval=0.1)
            """
            elif action_type == "move":
                pg.moveTo(x=x, y=y, duration=0.2)
            elif action_type == "drag":
                pg.dragTo(x=x, y=y, duration=0.5, button='left')
            """
            return True
            
        except pg.FailSafeException:
            self.last_error = "触发安全保护! 鼠标移动到角落."
            debug_print(f"执行鼠标操作失败: {self.last_error}")
            return False
        except Exception as e:
            self.last_error = f"鼠标操作失败: {str(e)}"
            debug_print(f"执行鼠标操作失败: {self.last_error}")
            return False

    def get_last_error(self):
        """Get the last error message"""
        return self.last_error 