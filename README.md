# AI Agent Platform

A microservices-based autonomous AI agent system built using:

- Spring Boot (Orchestrator)
- Redis (Task Queue)
- Python FastAPI (LLM Engine)
- Playwright (Browser Worker)
- Docker (Containerization)

## Architecture

1. User sends task to Orchestrator (JWT secured)
2. Task stored in Redis queue
3. LLM Engine decomposes task using OpenAI
4. Browser Worker executes subtasks
5. Results stored back in Redis
6. User retrieves final output

## Tech Stack

Java 17+
Spring Boot 3
Redis
Python 3.11
FastAPI
Playwright
Docker Compose
JWT Authentication

---

till now Completed:
- Backend microservices setup
- JWT authentication
- Redis queue
- Docker multi-container architecture
