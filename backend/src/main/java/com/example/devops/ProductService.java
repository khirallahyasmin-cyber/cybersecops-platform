package com.example.devops;

import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class ProductService {
  private final ProductRepository repository;

  public ProductService(ProductRepository repository) {
    this.repository = repository;
  }

  public List<Product> findAll() {
    return repository.findAll();
  }

  public Product findById(long id) {
    return repository.findById(id).orElseThrow(() -> new ProductNotFoundException(id));
  }

  public Product create(ProductRequest request) {
    return repository.create(request);
  }

  public Product update(long id, ProductRequest request) {
    return repository
        .update(id, request)
        .orElseThrow(() -> new ProductNotFoundException(id));
  }

  public void delete(long id) {
    if (!repository.delete(id)) {
      throw new ProductNotFoundException(id);
    }
  }
}
