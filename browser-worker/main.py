import os
import json
import asyncio
import redis
import httpx
from playwright.async_api import async_playwright

# Connect to Redis
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

LLM_ENGINE_URL = os.getenv("LLM_ENGINE_URL", "http://localhost:8001")

async def execute_subtask(page, subtask):
    """Execute a single subtask using the browser"""
    action = subtask.get("action", "")
    target = subtask.get("target", "")
    params = subtask.get("params", {})
    
    print(f"Browser Worker: Executing action={action}, target={target}")
    
    if action == "navigate":
        await page.goto(target, timeout=15000)
        title = await page.title()
        return {"action": "navigate", "url": target, "title": title}
    
    elif action == "search":
        search_url = f"https://www.google.com/search?q={target.replace(' ', '+')}"
        await page.goto(search_url, timeout=15000)
        
        # Extract search result titles and snippets
        await page.wait_for_selector("h3", timeout=5000)
        results = []
        
        titles = await page.query_selector_all("h3")
        for i, title_elem in enumerate(titles[:5]):
            try:
                text = await title_elem.inner_text()
                if text.strip():
                    results.append(text.strip())
            except:
                pass
        
        return {"action": "search", "query": target, "results": results}
    
    elif action == "extract":
        selector = params.get("selector", "body")
        try:
            element = await page.query_selector(selector)
            if element:
                text = await element.inner_text()
                return {"action": "extract", "content": text[:2000]}
        except:
            pass
        return {"action": "extract", "content": "Could not extract content"}
    
    elif action == "summarize":
        # Ask LLM engine to summarize
        context = params.get("text", target)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{LLM_ENGINE_URL}/summarize",
                    json={"text": context}
                )
                return resp.json()
        except Exception as e:
            return {"action": "summarize", "error": str(e)}
    
    else:
        return {"action": action, "status": "unknown action"}

async def worker():
    """Main worker loop"""
    print("Browser Worker: Starting...")
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        print("Browser Worker: Browser launched.")
        
        while True:
            try:
                # Wait for a job from the queue
                result = r.brpop("browser:queue", timeout=2)
                
                if result:
                    _, job_json = result
                    job = json.loads(job_json)
                    task_id = job["task_id"]
                    subtasks = job["subtasks"]
                    
                    print(f"Browser Worker: Executing {len(subtasks)} subtasks for task {task_id}")
                    
                    task_key = f"task:{task_id}"
                    page = await browser.new_page()
                    
                    all_results = []
                    for subtask in subtasks:
                        try:
                            result_data = await execute_subtask(page, subtask)
                            all_results.append(result_data)
                        except Exception as e:
                            all_results.append({"error": str(e), "subtask": subtask})
                    
                    await page.close()
                    
                    # Save results back to Redis
                    r.hset(task_key, mapping={
                        "status": "DONE",
                        "result": json.dumps(all_results, indent=2)
                    })
                    print(f"Browser Worker: Task {task_id} completed.")
                    
            except Exception as e:
                print(f"Browser Worker: Error: {e}")
                await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(worker())