package com.example.devops;

import java.time.Instant;
import java.util.Map;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@CrossOrigin(origins = {"http://localhost:8081", "http://127.0.0.1:8081"})
public class ApiController {
  @GetMapping("/api/health")
  public Map<String, Object> health() {
    return Map.of("status", "UP", "service", "devops-backend", "time", Instant.now().toString());
  }
}
