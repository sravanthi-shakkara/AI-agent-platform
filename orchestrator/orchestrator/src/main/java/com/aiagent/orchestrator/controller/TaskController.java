package com.aiagent.orchestrator.controller;

import com.aiagent.orchestrator.model.Task;
import com.aiagent.orchestrator.model.TaskRequest;
import com.aiagent.orchestrator.service.TaskService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/tasks")
public class TaskController {

    @Autowired
    private TaskService taskService;

    @PostMapping
    public ResponseEntity<Task> createTask(@RequestBody TaskRequest request,
                                            Authentication authentication) {
        String userId = authentication.getName();
        Task task = taskService.createTask(request, userId);
        return ResponseEntity.ok(task);
    }

    @GetMapping("/{taskId}")
    public ResponseEntity<Task> getTask(@PathVariable String taskId) {
        Task task = taskService.getTask(taskId);
        return ResponseEntity.ok(task);
    }
}
