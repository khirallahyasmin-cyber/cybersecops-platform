package com.example.devops;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;

public record ProductRequest(
    @NotBlank @Size(max = 120) String name,
    @Size(max = 1000) String description,
    @DecimalMin(value = "0.0", inclusive = false) BigDecimal price,
    @PositiveOrZero int stock) {}
