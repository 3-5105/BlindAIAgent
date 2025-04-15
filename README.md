# BlindAIAgent
在Windows环境下，通过无障碍辅助功能，为仅文本的单模态大模型提供GUI操作能力

# 原理
基于Windows系统中，通过[UI自动化](https://learn.microsoft.com/zh-cn/dotnet/framework/ui-automation/ui-automation-overview)功能，将屏幕上的所有控件转换为文本并编号。大模型根据任务，给出对某控件的某操作，由此工程执行。

# 待办
 - 支持更多操作（目前只支持左右单击、左双击、快捷键、输入文本）
 - 扩大AI的识别范围（目前仅能操作前台窗口内的控件）
 - 去除不必要的控件，节省token
 - 优化代码结构
 - 对于Chromium系浏览器，优先使用Chrome DevTools 协议操作，获得更高精度
 - 对于Win32标准控件，使用合适的Win32Api获得更准确的数据
 - i18n

# 开发环境
作者使用Python 3.12，或许附近的版本也可使用
运行`pip install -r requirements.txt`安装依赖

# 注意事项
AI提交的内容在不经过审查的情况下就会执行。请确保AI有0%的可能伤害到您的数据

此工程仍在开发阶段，请勿用于生产环境
