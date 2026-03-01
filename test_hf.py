import requests

hf_api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
sys_prompt = "Role: AI interviewer. Language: strictly English. Ask candidate one technical interview question."
payload = {
    "inputs": f"[INST] {sys_prompt} [/INST]",
    "parameters": {"max_new_tokens": 100, "temperature": 0.7}
}

print("Sending request to HF...")
h_res = requests.post(hf_api_url, json=payload, timeout=10)
print("Status:", h_res.status_code)
print("Response:", h_res.text)
