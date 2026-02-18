package com.aiagent.orchestrator.service;

import com.aiagent.orchestrator.model.Task;
import com.aiagent.orchestrator.model.TaskRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import java.time.LocalDateTime;
import java.util.UUID;

@Service
public class TaskService {

    @Autowired
    private RedisTemplate<String, String> redisTemplate;

    public Task createTask(TaskRequest request, String userId) {
        Task task = new Task();
        task.setTaskId(UUID.randomUUID().toString());
        task.setUserId(userId);
        task.setInput(request.getInput());
        task.setStatus("PENDING");
        task.setCreatedAt(LocalDateTime.now().toString());

        // Save task fields to Redis as a hash
        String key = "task:" + task.getTaskId();
        redisTemplate.opsForHash().put(key, "taskId", task.getTaskId());
        redisTemplate.opsForHash().put(key, "userId", task.getUserId());
        redisTemplate.opsForHash().put(key, "input", task.getInput());
        redisTemplate.opsForHash().put(key, "status", task.getStatus());
        redisTemplate.opsForHash().put(key, "createdAt", task.getCreatedAt());
        redisTemplate.opsForHash().put(key, "result", "");

        // Push task ID to queue for LLM engine to pick up
        redisTemplate.opsForList().leftPush("task:queue", task.getTaskId());

        return task;
    }

    public Task getTask(String taskId) {
        String key = "task:" + taskId;
        Task task = new Task();
        task.setTaskId((String) redisTemplate.opsForHash().get(key, "taskId"));
        task.setUserId((String) redisTemplate.opsForHash().get(key, "userId"));
        task.setInput((String) redisTemplate.opsForHash().get(key, "input"));
        task.setStatus((String) redisTemplate.opsForHash().get(key, "status"));
        task.setResult((String) redisTemplate.opsForHash().get(key, "result"));
        task.setCreatedAt((String) redisTemplate.opsForHash().get(key, "createdAt"));
        return task;
    }
}