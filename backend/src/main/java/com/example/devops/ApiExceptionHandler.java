package com.example.devops;

import java.time.Instant;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.bind.MethodArgumentNotValidException;

@RestControllerAdvice
public class ApiExceptionHandler {
  @ExceptionHandler(ProductNotFoundException.class)
  public ResponseEntity<Map<String, Object>> handleNotFound(ProductNotFoundException exception) {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .body(Map.of("status", 404, "error", "Not Found", "message", exception.getMessage(), "time", Instant.now().toString()));
  }

  @ExceptionHandler(MethodArgumentNotValidException.class)
  public ResponseEntity<Map<String, Object>> handleInvalidRequest(MethodArgumentNotValidException exception) {
    String message =
        exception.getBindingResult().getFieldErrors().stream()
            .findFirst()
            .map(error -> error.getField() + ": " + error.getDefaultMessage())
            .orElse("The request is invalid.");
    return ResponseEntity.badRequest()
        .body(Map.of("status", 400, "error", "Bad Request", "message", message, "time", Instant.now().toString()));
  }
}
