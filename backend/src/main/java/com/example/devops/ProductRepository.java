package com.example.devops;

import java.sql.Statement;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

@Repository
public class ProductRepository {
  private static final RowMapper<Product> ROW_MAPPER =
      (row, rowNumber) ->
          new Product(
              row.getLong("id"),
              row.getString("name"),
              row.getString("description"),
              row.getBigDecimal("price"),
              row.getInt("stock"));

  private final JdbcTemplate jdbcTemplate;

  public ProductRepository(JdbcTemplate jdbcTemplate) {
    this.jdbcTemplate = jdbcTemplate;
  }

  public List<Product> findAll() {
    return jdbcTemplate.query("SELECT id, name, description, price, stock FROM products ORDER BY id", ROW_MAPPER);
  }

  public Optional<Product> findById(long id) {
    return jdbcTemplate
        .query("SELECT id, name, description, price, stock FROM products WHERE id = ?", ROW_MAPPER, id)
        .stream()
        .findFirst();
  }

  public Product create(ProductRequest request) {
    KeyHolder keyHolder = new GeneratedKeyHolder();
    jdbcTemplate.update(
        connection -> {
          var statement =
              connection.prepareStatement(
                  "INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)",
                  Statement.RETURN_GENERATED_KEYS);
          statement.setString(1, request.name().trim());
          statement.setString(2, request.description() == null ? "" : request.description().trim());
          statement.setBigDecimal(3, request.price());
          statement.setInt(4, request.stock());
          return statement;
        },
        keyHolder);

    Number id = keyHolder.getKey();
    if (id == null) {
      throw new IllegalStateException("The database did not return an id for the new product.");
    }
    return findById(id.longValue())
        .orElseThrow(() -> new IllegalStateException("The newly created product could not be read back."));
  }

  public Optional<Product> update(long id, ProductRequest request) {
    int updated =
        jdbcTemplate.update(
            "UPDATE products SET name = ?, description = ?, price = ?, stock = ? WHERE id = ?",
            request.name().trim(),
            request.description() == null ? "" : request.description().trim(),
            request.price(),
            request.stock(),
            id);
    return updated == 0 ? Optional.empty() : findById(id);
  }

  public boolean delete(long id) {
    return jdbcTemplate.update("DELETE FROM products WHERE id = ?", id) > 0;
  }
}
