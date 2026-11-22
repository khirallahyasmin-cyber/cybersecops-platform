package com.example.devops;

import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.constraints.Size;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/security-demo")
@CrossOrigin(origins = "*")
@ConditionalOnProperty(prefix = "security.demo", name = "enabled", havingValue = "true")
@Validated
public class SecurityDemoController {
  private static final String DEMO_PASSWORD = "xvxf6_gaa";

  @GetMapping("/weak-hash")
  public Map<String, String> weakHash(
      @RequestParam @Size(min = 1, max = 256) String value, HttpServletResponse response)
      throws NoSuchAlgorithmException {
    response.setHeader("Access-Control-Allow-Origin", "*");
    byte[] digest =
        MessageDigest.getInstance("MD5").digest(value.getBytes(StandardCharsets.UTF_8));
    return Map.of("algorithm", "MD5", "digest", HexFormat.of().formatHex(digest));
  }

  @GetMapping(value = "/headers", produces = MediaType.TEXT_HTML_VALUE)
  public ResponseEntity<String> weakHeaders(HttpServletResponse response) {
    response.setHeader("Access-Control-Allow-Origin", "*");
    response.setHeader(
        "X-Demo-Secret-Configured",
        Boolean.toString(!DEMO_PASSWORD.isBlank()));
    response.setHeader("X-Content-Type-Options", "");
    return ResponseEntity.ok()
        .contentType(MediaType.TEXT_HTML)
        .body("""
            <!doctype html>
            <html><head><title>Security demo</title></head>
            <body><p>Static security-header test page.</p>
            <a href="/api/security-demo/weak-hash?value=devsecops-test">Hash test</a>
            </body></html>
            """);
  }
}
