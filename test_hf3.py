import requests

hf_api_url = "https://router.huggingface.co/hf-inference/models/HuggingFaceH4/zephyr-7b-beta"
sys_prompt = "Role: AI interviewer. Language: strictly English. Ask candidate one technical interview question."
payload = {
    "inputs": f"<|system|>\n{sys_prompt}</s>\n<|user|>\nHello</s>\n<|assistant|>\n",
    "parameters": {"max_new_tokens": 100, "temperature": 0.7}
}

print("Sending request to HF...")
h_res = requests.post(hf_api_url, json=payload, timeout=10)
print("Status:", h_res.status_code)
print("Response:", h_res.text)
