from ollama import generate

prompt = "你是一个中英翻译专家，请为我翻译以下内容"

response = generate("deepseek-r1:8b", prompt, stream=True)
for part in response:
    print(part.response, end="", flush=True)