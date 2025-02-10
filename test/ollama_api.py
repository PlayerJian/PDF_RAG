from langchain_community.llms import Ollama

# 创建Ollama实例，指定模型名称
ollama = Ollama(model="deepseek-r1:7b")

# 准备输入提示
prompt = "你是谁？"


# 使用stream方法进行流式生成
def stream_generation():
    for chunk in ollama.stream(input=prompt):
        print(chunk+"*****", end="", flush=True)


# 调用函数执行流式生成
stream_generation()