from fastapi import FastAPI
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

app = FastAPI()

# 模型路径
model_path = "qwen2.5-1.5b-lora"

# 加载 tokenizer （分词器）
tokenizer = AutoTokenizer.from_pretrained(model_path)

# 加载模型并移动到可用设备（GPU/CPU）
device = "cuda" if torch.cuda.is_available() else "cpu"
model = AutoModelForCausalLM.from_pretrained(model_path).to(device)

@app.get("/generate")
async def generate_text(prompt: str):
    # 用 chat template 格式化输入，让模型知道自己在做问答
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(device)

    # 生成文本，遇到 EOS token 自动停止
    outputs = model.generate(
        inputs["input_ids"],
        max_new_tokens=512,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        eos_token_id=tokenizer.eos_token_id,
    )

    # 只取新生成的部分（去掉输入的 prompt）
    new_tokens = outputs[0][inputs["input_ids"].shape[-1]:]
    generated_text = tokenizer.decode(new_tokens, skip_special_tokens=True)

    return {"generated_text": generated_text}