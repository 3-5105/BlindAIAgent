from .controller import Controller
from .utils import load_config
import traceback
import sys

def main():
    try:
        # 创建控制器实例
        controller = Controller()
        
        # 获取用户输入并运行任务
        while True:
            try:
                user_input = input("\n请输入要执行的任务 (输入 'exit' 退出): ")
                if user_input.lower() == 'exit':
                    print("程序退出...")
                    break
                    
                if not user_input.strip():
                    print("请输入有效的任务描述")
                    continue
                    
                # 运行任务
                controller.run_task(user_input)
                
            except KeyboardInterrupt:
                print("\n任务被用户中断")
                choice = input("是否要退出程序？(y/n): ")
                if choice.lower() == 'y':
                    break
            except Exception as e:
                print(f"执行任务时发生错误: {e}")
                print("错误详情:")
                print(traceback.format_exc())
                choice = input("是否要继续？(y/n): ")
                if choice.lower() != 'y':
                    break
                    
    except Exception as e:
        print(f"程序初始化失败: {e}")
        print("错误详情:")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 