import os
import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from PIL import Image


os.environ["HF_HOME"] = r"F:\SpiderModel\huggingface_cache"       # 自定义缓存目录
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"               # 禁用 symlink 警告
os.environ["HF_ENDPOINT"] = "https://huggingface.tuna.tsinghua.edu.cn"  # 清华镜像
os.environ["HF_TOKEN"] = "YOUR KEY WORD"       # HF 令牌


MODEL_NAME = "Qwen/Qwen2-VL-2B-Instruct"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# 待识别的图片列表（请确保图片文件存在于当前目录）
IMAGES = ["captcha_0.png", "captcha_1.png", "captcha_2.png",
          "captcha_3.png", "captcha_4.png", "captcha_5.png"]


quantization_config = BitsAndBytesConfig(load_in_8bit=True)



print("加载模型中，请稍等...")


model = Qwen2VLForConditionalGeneration.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    quantization_config=quantization_config,   # 根据上方配置启用量化
    cache_dir=r"F:\SpiderModel\huggingface_cache",
    trust_remote_code=True
)

processor = AutoProcessor.from_pretrained(
    MODEL_NAME,
    cache_dir=r"F:\SpiderModel\huggingface_cache",
    trust_remote_code=True
)

print("模型加载完成 ✅")


def recognize_image(image_path,quest):
    image = Image.open(image_path).convert("RGB")
    messages = [{
        "role": "user",
        "content": [
            {"type": "image"},   # 图片占位符
            {"type": "text", "text": f"如果该图片是{quest},则返回数字1，否则返回0不允许返回任何其他数据"}
        ]
    }]
    # 应用对话模板，得到纯文本 prompt
    prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    # 将文本和图片一起传给 processor，生成模型输入
    inputs = processor(text=prompt, images=image, return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=50,
            temperature=0.0,
            do_sample=False
        )

    # 只解码新生成的部分
    generated_ids = output_ids[0][inputs['input_ids'].shape[1]:]
    result = processor.decode(generated_ids, skip_special_tokens=True)
    return result
