import os
import json
import asyncio
import redis
from fastapi import FastAPI
from openai import OpenAI
import httpx

app = FastAPI()

# Connect to Redis
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# Connect to OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a task decomposition agent.
Given a user's natural language request, break it into a JSON array of subtasks.
Each subtask must have this format:
{"action": "search" or "navigate" or "extract" or "summarize", "target": "url or search query", "params": {}}

Example input: "Find top 5 Python web frameworks"
Example output:
[
  {"action": "search", "target": "top 5 Python web frameworks 2024", "params": {}},
  {"action": "summarize", "target": "search results", "params": {}}
]

Return ONLY the JSON array. No explanation. No markdown. Just the raw JSON array."""

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/summarize")
async def summarize(data: dict):
    text = data.get("text", "")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Summarize the following text in 3-5 bullet points."},
            {"role": "user", "content": text[:3000]}
        ]
    )
    return {"summary": response.choices[0].message.content}

async def process_queue():
    """This runs in the background, picking tasks from Redis queue"""
    print("LLM Engine: Starting queue processor...")
    while True:
        try:
            # Wait for a task (blocking pop with 2 second timeout)
            result = r.brpop("task:queue", timeout=2)
            
            if result:
                _, task_id = result
                print(f"LLM Engine: Processing task {task_id}")
                
                # Get task details from Redis
                task_key = f"task:{task_id}"
                user_input = r.hget(task_key, "input")
                
                if not user_input:
                    print(f"LLM Engine: No input found for task {task_id}")
                    continue
                
                # Update status
                r.hset(task_key, "status", "DECOMPOSING")
                
                # Ask OpenAI to break task into subtasks
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_input}
                    ]
                )
                
                subtasks_json = response.choices[0].message.content.strip()
                print(f"LLM Engine: Subtasks generated: {subtasks_json}")
                
                # Push to browser worker queue
                job = json.dumps({
                    "task_id": task_id,
                    "subtasks": json.loads(subtasks_json)
                })
                r.lpush("browser:queue", job)
                r.hset(task_key, "status", "PROCESSING")
                
        except json.JSONDecodeError as e:
            print(f"LLM Engine: JSON parse error: {e}")
        except Exception as e:
            print(f"LLM Engine: Error: {e}")
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(process_queue())