import json

def load_config(config_path='config/config.json'):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("错误：未找到 config.json 文件")
        exit(1)
    except json.JSONDecodeError:
        print("错误：config.json 文件格式不正确")
        exit(1)
    except Exception as e:
        print(f"读取配置文件时发生错误: {e}")
        exit(1) 