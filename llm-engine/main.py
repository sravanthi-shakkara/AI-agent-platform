# LLM Engine - FastAPI service that processes tasks from Redis queue
# Uses OpenAI GPT-4o-mini to decompose natural language tasks into subtasks
# Runs a background thread to continuously watch for new tasks


import os
import json
import asyncio
import threading
import redis
from fastapi import FastAPI
from openai import OpenAI

app = FastAPI()
# Connect to Redis using environment variables from docker-compose.yml
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a task decomposition agent.
Given a user's natural language request, break it into a JSON array of subtasks.
Each subtask must have this format:
{"action": "search" or "navigate" or "extract" or "summarize", "target": "url or search query", "params": {}}
Return ONLY the JSON array. No explanation. No markdown. Just the raw JSON array."""

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/summarize")
def summarize(data: dict):
    text = data.get("text", "")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Summarize the following text in 3-5 bullet points."},
            {"role": "user", "content": text[:3000]}
        ]
    )
    return {"summary": response.choices[0].message.content}
# Background thread that watches Redis queue for new tasks
def process_queue():
    """Runs in a background thread, picking tasks from Redis queue"""
    print("LLM Engine: Queue processor thread started!")
    while True:
        try:
            result = r.brpop("task:queue", timeout=5)
            if result:
                _, task_id = result
                print(f"LLM Engine: Got task {task_id}")

                task_key = f"task:{task_id}"
                user_input = r.hget(task_key, "input")

                if not user_input:
                    print(f"LLM Engine: No input for task {task_id}")
                    continue

                r.hset(task_key, "status", "DECOMPOSING")

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_input}
                    ]
                )

                subtasks_json = response.choices[0].message.content.strip()
                print(f"LLM Engine: Subtasks: {subtasks_json}")

                job = json.dumps({
                    "task_id": task_id,
                    "subtasks": json.loads(subtasks_json)
                })
                r.lpush("browser:queue", job)
                r.hset(task_key, "status", "PROCESSING")
                print(f"LLM Engine: Task {task_id} pushed to browser worker")

        except json.JSONDecodeError as e:
            print(f"LLM Engine: JSON error: {e}")
        except Exception as e:
            print(f"LLM Engine: Error: {e}")
            import time
            time.sleep(1)

@app.on_event("startup")
def startup_event():
    print("LLM Engine: Starting background thread...")
    t = threading.Thread(target=process_queue, daemon=True)
    t.start()
    print("LLM Engine: Background thread started!")

if __name__ == "__main__":
    import uvicorn
    # Start background thread
    t = threading.Thread(target=process_queue, daemon=True)
    t.start()
    print("LLM Engine: Started directly!")
    uvicorn.run(app, host="0.0.0.0", port=8001)
