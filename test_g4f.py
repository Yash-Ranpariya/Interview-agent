import g4f

try:
    response = g4f.ChatCompletion.create(
        model=g4f.models.gpt_4o_mini,
        messages=[{"role": "user", "content": "Hello! Reply with OK"}],
    )
    print("SUCCESS:", response)
except Exception as e:
    print("FAILED:", e)
