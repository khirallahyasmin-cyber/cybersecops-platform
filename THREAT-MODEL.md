# Threat model - DevOps product catalog

This lightweight STRIDE review follows the threat-modeling steps in the
DevSecOps development-phase course. It covers the local Docker Compose
application, not a production deployment or the Jenkins host.

## Scope and assets

- Product records and the MySQL database volume.
- Database credentials in `.env` and Jenkins credentials in its persistent
  volume.
- The backend API, frontend, built images, and source repository.
- The Docker engine socket exposed to the Jenkins container.

## Trust boundaries

1. Browser to the Nginx frontend and its `/api/` proxy to Spring Boot.
2. Spring Boot to MySQL over the private Compose network.
3. Jenkins pipeline to the Docker engine through `/var/run/docker.sock`.
4. Developer workstation and Git repository to the CI checkout.

## STRIDE review

| Threat | Example in this project | Existing control or action |
|---|---|---|
| Spoofing | An unauthorized caller changes catalog data. | The application is a local lab and has no user authentication; do not expose it to an untrusted network. Add authentication before any shared deployment. |
| Tampering | A caller submits malformed or SQL-like product input. | Bean Validation constrains requests, JDBC uses prepared statements, and JUnit verifies invalid input and SQL-like product names. |
| Repudiation | A change or deployment cannot be tied to its source. | Use Git history and Jenkins build records; require reviewed pull requests for shared repositories. |
| Information disclosure | A password or database value leaks through Git, logs, or an exposed endpoint. | `.env` is ignored by Git; Gitleaks checks staged changes; pre-commit scans for private keys; keep real credentials in Jenkins Credentials, never in source. |
| Denial of service | Large input or excessive requests consume application resources. | Request fields have size and range constraints. Add rate limits and resource limits before exposing the service. |
| Elevation of privilege | A compromised Jenkins job controls the Docker host. | Jenkins has the Docker socket and runs as root for this local lab. Treat Jenkins jobs and users as fully trusted; never expose this configuration to untrusted users. |

## CI checks selected for this lab

- **Pre-commit:** Gitleaks blocks detected secrets before they enter a commit.
- **SAST:** the existing SonarQube pipeline step analyzes the Java source.
- **Security tests:** JUnit covers request validation and SQL-like input handling.
- **SCA and container vulnerabilities:** Trivy scans the built backend and
  frontend images for fixable HIGH and CRITICAL vulnerabilities.
- **Application findings:** SonarQube, Trivy, and OWASP ZAP findings in the
  dashboard come only from scans of the actual application source, resolved
  dependencies, built images, deployed API, and project configuration. The
  pipeline does not add expected findings or vulnerable example fixtures.

Threats and mitigations should be revisited when authentication, deployment
outside the local machine, or additional infrastructure is introduced.
