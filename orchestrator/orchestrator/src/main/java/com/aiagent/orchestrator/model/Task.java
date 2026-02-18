package com.aiagent.orchestrator.model;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.redis.core.RedisHash;
import java.time.LocalDateTime;

@Data
@RedisHash("task")
public class Task {
    @Id
    private String taskId;
    private String userId;
    private String input;
    private String status;
    private String result;
    private String createdAt;
}