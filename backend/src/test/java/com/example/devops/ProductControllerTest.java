package com.example.devops;

import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest(properties = "security.demo.enabled=true")
@AutoConfigureMockMvc
@ActiveProfiles("test")
class ProductControllerTest {
  @Autowired private MockMvc mockMvc;

  @Test
  void exposesTheOptInWeakHashDemoWithWildcardCors() throws Exception {
    mockMvc
        .perform(
            get("/api/security-demo/weak-hash")
                .param("value", "security-test")
                .header("Origin", "https://untrusted.example"))
        .andExpect(status().isOk())
        .andExpect(header().string("Access-Control-Allow-Origin", "*"))
        .andExpect(jsonPath("$.algorithm").value("MD5"))
        .andExpect(jsonPath("$.digest").value("ddbcdd7098732b1abf68b43cc76d089a"));
  }

  @Test
  void exposesTheOptInHtmlDemoWithMissingBrowserSecurityHeaders() throws Exception {
    mockMvc
          .perform(get("/api/security-demo/headers"))
          .andExpect(status().isOk())
          .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_HTML))
          .andExpect(content().string(containsString("Static security-header test page.")))
          .andExpect(content().string(containsString("/api/security-demo/weak-hash?value=")))
          .andExpect(header().string("Access-Control-Allow-Origin", "*"))
          .andExpect(header().string("X-Content-Type-Options", ""))
          .andExpect(header().doesNotExist("Content-Security-Policy"))
          .andExpect(header().doesNotExist("X-Frame-Options"));
  }

  @Test
  void createsReadsUpdatesAndDeletesAProduct() throws Exception {
    String request = """
        {"name":"Clavier","description":"USB keyboard","price":49.90,"stock":8}
        """;

    String location =
        mockMvc
            .perform(post("/api/products").contentType(MediaType.APPLICATION_JSON).content(request))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.id").isNumber())
            .andExpect(jsonPath("$.name").value("Clavier"))
            .andExpect(jsonPath("$.stock").value(8))
            .andReturn()
            .getResponse()
            .getHeader("Location");

    mockMvc
        .perform(
            put(location)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"name":"Clavier Pro","description":"Mechanical keyboard","price":89.90,"stock":4}
                    """))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.name").value("Clavier Pro"));

    mockMvc.perform(delete(location)).andExpect(status().isNoContent());
    mockMvc
        .perform(get(location))
        .andExpect(status().isNotFound())
        .andExpect(jsonPath("$.message", containsString("was not found")));
  }

  @Test
  void rejectsInvalidProductAndUnknownProduct() throws Exception {
    mockMvc
        .perform(
            post("/api/products")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"name":" ","description":"invalid","price":-3,"stock":-1}
                    """))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.error").value("Bad Request"));

    mockMvc
        .perform(get("/api/products/987654"))
        .andExpect(status().isNotFound())
        .andExpect(content().string(containsString("Product 987654 was not found")));
  }

  @Test
  void treatsSqlLikeProductNameAsData() throws Exception {
    String sqlLikeName = "' OR 1=1 --";

    String location =
        mockMvc
            .perform(
                post("/api/products")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("""
                        {"name":"' OR 1=1 --","description":"security test","price":1.00,"stock":0}
                        """))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.name").value(sqlLikeName))
            .andReturn()
            .getResponse()
            .getHeader("Location");

    mockMvc
        .perform(get(location))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.name").value(sqlLikeName));
  }

  @Test
  void includesContentTypeSniffingProtectionHeader() throws Exception {
    mockMvc
        .perform(get("/api/products"))
        .andExpect(status().isOk())
        .andExpect(header().string("X-Content-Type-Options", "nosniff"));
  }

  @Test
  void exposesPrometheusMetrics() throws Exception {
    mockMvc
        .perform(get("/actuator/prometheus"))
        .andExpect(status().isOk())
        .andExpect(content().string(containsString("jvm_memory_used_bytes")));
  }
}
