pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  environment {
    COMPOSE_PROJECT_NAME = 'devops-lab'
    SONARQUBE_URL = 'http://sonarqube:9000'
    NEXUS_URL = 'http://nexus:8081'
  }

  parameters {
    booleanParam(name: 'USE_LOCAL_SOURCE', defaultValue: true, description: 'Use the project folder mounted into the local Jenkins container. Disable this when the job is configured from a Git repository.')
    string(name: 'COMMIT_MESSAGE', defaultValue: 'test(security): exercise scanner findings', description: 'Conventional Commit message validated by Commitizen when USE_LOCAL_SOURCE is enabled.')
    booleanParam(name: 'ENABLE_SECURITY_DEMO', defaultValue: true, description: 'Enable local-only MEDIUM/LOW security demo endpoints for ZAP. Docker publishing is skipped while this is enabled.')
    booleanParam(name: 'RUN_SONAR', defaultValue: true, description: 'Run SonarQube analysis. Requires Jenkins secret credential sonar-token.')
    booleanParam(name: 'PUBLISH_NEXUS', defaultValue: true, description: 'Deploy the Maven artifact to Nexus. Requires hosted maven-releases and credential nexus-credentials.')
    booleanParam(name: 'PUBLISH_DOCKER', defaultValue: false, description: 'Push backend and frontend images to DOCKERHUB_REPOSITORY. Requires credential dockerhub-credentials and ENABLE_SECURITY_DEMO=false.')
    string(name: 'DOCKERHUB_REPOSITORY', defaultValue: 'ykhirallah/devops-catalog', description: 'Private Docker Hub repository created for this project; images are pushed with backend-BUILD_NUMBER and frontend-BUILD_NUMBER tags.')
    string(name: 'JENKINS_PUBLIC_URL', defaultValue: 'http://localhost:8083', description: 'Browser-accessible base URL for links from the HTML report.')
    string(name: 'EMAIL_TO', defaultValue: 'jasminekhirallah2@gmail.com', description: 'Email address to notify after a successful deployment. Requires Jenkins SMTP configuration.')
  }

  stages {
    stage('Declarative: Tool Install') {
      steps {
        sh '''
          set -eu
          command -v java
          java -version
          command -v mvn
          mvn -version
          command -v git
          git --version
          command -v pre-commit
          pre-commit --version
          command -v trivy
          trivy --version
          command -v docker
          docker compose version
          command -v curl
          command -v python3
          python3 --version
        '''
      }
    }

    stage('Getting Project from Git') {
      steps {
        script {
          if (params.USE_LOCAL_SOURCE) {
            deleteDir()
            sh '''
              set -eu
              archive="$(mktemp)"
              trap 'rm -f "$archive"' EXIT
              tar --exclude=.env --exclude=.git --exclude=backend/target --exclude=reports -cf "$archive" -C /workspace .
              tar -xf "$archive" -C "$WORKSPACE"
            '''
          } else {
            checkout scm
          }
        }
      }
    }

    stage('Initialize DevSecOps report') {
      steps {
        sh '''
          mkdir -p reports
          rm -f reports/devsecops-results.json reports/devsecops-report.html
          rm -f reports/THREAT-MODEL.md
          rm -f reports/pre-commit.log reports/gitleaks.log reports/gitleaks-summary.txt reports/commitizen.log reports/commit-message.txt
          rm -f reports/smoke-tests.log reports/fault-injection.log
          rm -f reports/sonarqube-issues.json reports/sonarqube-hotspots.json
          rm -f reports/security-fixture-findings.json reports/trivy-fixture-iac.json reports/trivy-fixture-sca.json
          rm -f reports/report-views/security-fixture-findings.html
          rm -f reports/maven-tests.xml reports/trivy-backend.json reports/trivy-frontend.json
          rm -f reports/trivy-scan.log reports/trivy-scan-completed
          rm -f reports/trivy-iac.json reports/dependency-updates.log
          rm -f reports/configuration-checks.json reports/runtime-checks.json
          rm -f reports/monitoring-checks.json reports/security-smoke-checks.json
          rm -f reports/zap-report.html reports/zap-report.json
        '''
        sh 'python3 devsecops_report.py init --project-root . --results reports/devsecops-results.json'
      }
    }

    stage('Pre-commit checks') {
      steps {
        sh '''
          set -eu
          mkdir -p reports
          if [ "$USE_LOCAL_SOURCE" = "true" ]; then
            git config --global --add safe.directory "$WORKSPACE"
            git init --quiet
            git add -A
          fi
          set +e
          pre-commit run --all-files > reports/pre-commit.log 2>&1
          result=$?
          set -e
          cat reports/pre-commit.log
          exit "$result"
        '''
      }
      post {
        success {
          sh '''
            python3 devsecops_report.py record --id precommit --status passed --summary "Tous les hooks pre-commit configures, y compris Gitleaks, ont passe." --command "pre-commit run --all-files" --artifact reports/pre-commit.log --results reports/devsecops-results.json
          '''
        }
        failure {
          sh '''
            python3 devsecops_report.py record --id precommit --status failed --summary "Au moins un hook pre-commit a echoue; consulter les details." --command "pre-commit run --all-files" --artifact reports/pre-commit.log --results reports/devsecops-results.json
          '''
        }
      }
    }

    stage('Gitleaks secrets scan') {
      steps {
        sh '''
          set -eu
          mkdir -p reports
          set +e
          pre-commit run gitleaks --all-files > reports/gitleaks.log 2>&1
          result=$?
          set -e
          rm -f reports/gitleaks.log
          if [ "$result" -eq 0 ]; then
            printf '%s\n' 'Gitleaks terminé : aucun secret détecté.' > reports/gitleaks-summary.txt
          else
            printf '%s\n' 'Gitleaks a échoué ou a détecté un secret. Consulter les logs Jenkins avec les permissions requises.' > reports/gitleaks-summary.txt
          fi
          exit "$result"
        '''
      }
      post {
        success {
          sh 'python3 devsecops_report.py record --id gitleaks --status passed --summary "Gitleaks na detecte aucun secret dans les fichiers suivis." --command "pre-commit run gitleaks --all-files" --artifact reports/gitleaks-summary.txt --results reports/devsecops-results.json'
        }
        failure {
          sh 'python3 devsecops_report.py record --id gitleaks --status failed --summary "Gitleaks a detecte un secret ou na pas pu terminer; ne pas partager sa sortie brute." --command "pre-commit run gitleaks --all-files" --artifact reports/gitleaks-summary.txt --results reports/devsecops-results.json'
        }
      }
    }

    stage('Commit message validation') {
      steps {
        withEnv(["COMMIT_MESSAGE=${params.COMMIT_MESSAGE ?: ''}"]) {
          sh '''
            set -eu
            mkdir -p reports
            : > reports/commit-message.txt
            if [ "$USE_LOCAL_SOURCE" = "true" ]; then
              if [ -z "$(printf '%s' "$COMMIT_MESSAGE" | tr -d '[:space:]')" ]; then
                printf '%s\n' 'Échec : renseigner COMMIT_MESSAGE pour valider le message en mode source locale.' > reports/commitizen.log
                cat reports/commitizen.log
                exit 1
              fi
              printf '%s\n' "$COMMIT_MESSAGE" > reports/commit-message.txt
              message_file=reports/commit-message.txt
            else
              git log -1 --format=%B > reports/commit-message.txt
              message_file=reports/commit-message.txt
            fi
            set +e
            pre-commit run --hook-stage commit-msg --commit-msg-filename "$message_file" > reports/commitizen.log 2>&1
            result=$?
            set -e
            cat reports/commitizen.log
            exit "$result"
          '''
        }
      }
      post {
        success {
          sh 'python3 devsecops_report.py record --id commitizen --status passed --summary "Le message soumis respecte Conventional Commits selon Commitizen." --command "pre-commit run --hook-stage commit-msg --commit-msg-filename" --artifact reports/commitizen.log --artifact reports/commit-message.txt --results reports/devsecops-results.json'
        }
        failure {
          sh 'python3 devsecops_report.py record --id commitizen --status failed --summary "La validation Commitizen a echoue; consulter les details." --command "pre-commit run --hook-stage commit-msg --commit-msg-filename" --artifact reports/commitizen.log --artifact reports/commit-message.txt --results reports/devsecops-results.json'
        }
      }
    }

    stage('Cleaning the project') {
      steps {
        dir('backend') {
          sh 'mvn -B clean'
        }
      }
    }

    stage('Artifact construction') {
      steps {
        dir('backend') {
          sh 'mvn -B -DskipTests package'
        }
      }
    }

    stage('Unit Tests') {
      steps {
        dir('backend') {
          sh 'mvn -B test jacoco:report'
        }
      }
      post {
        always {
          junit testResults: 'backend/target/surefire-reports/*.xml', allowEmptyResults: false
          archiveArtifacts artifacts: 'backend/target/*.jar,backend/target/site/jacoco/**', fingerprint: true
          sh '''
            mkdir -p reports
            if [ -f backend/target/surefire-reports/TEST-com.example.devops.ProductControllerTest.xml ]; then
              cp backend/target/surefire-reports/TEST-com.example.devops.ProductControllerTest.xml reports/maven-tests.xml
            fi
          '''
        }
        success {
          sh 'python3 devsecops_report.py record --id maven-tests --status passed --summary "Les tests unitaires et de securite Maven sont passes." --command "mvn -B test jacoco:report" --artifact reports/maven-tests.xml --results reports/devsecops-results.json'
        }
        failure {
          sh 'python3 devsecops_report.py record --id maven-tests --status failed --summary "Les tests Maven ont echoue; consulter le rapport Surefire." --command "mvn -B test jacoco:report" --artifact reports/maven-tests.xml --results reports/devsecops-results.json'
        }
      }
    }

    stage('Dependency update report') {
      steps {
        dir('backend') {
          sh '''
            set +e
            mvn -B org.codehaus.mojo:versions-maven-plugin:2.18.0:display-dependency-updates > "$WORKSPACE/reports/dependency-updates.log" 2>&1
            result=$?
            set -e
            cat "$WORKSPACE/reports/dependency-updates.log"
            if [ "$result" -eq 0 ]; then
              python3 "$WORKSPACE/devsecops_report.py" record --id dependency-management --status passed --summary "Le rapport Maven Versions liste les dépendances ayant une mise à jour disponible; aucune mise à jour automatique n'est appliquée." --command "mvn org.codehaus.mojo:versions-maven-plugin:2.18.0:display-dependency-updates" --artifact reports/dependency-updates.log --results "$WORKSPACE/reports/devsecops-results.json"
            else
              python3 "$WORKSPACE/devsecops_report.py" record --id dependency-management --status failed --summary "La vérification des mises à jour n'a pas abouti; le rapport est informatif et le pipeline continue." --command "mvn org.codehaus.mojo:versions-maven-plugin:2.18.0:display-dependency-updates" --artifact reports/dependency-updates.log --results "$WORKSPACE/reports/devsecops-results.json"
            fi
          '''
        }
      }
    }

    stage('Infrastructure as Code scan') {
      steps {
        sh '''
          set -eu
          mkdir -p reports
          trivy --cache-dir "$JENKINS_HOME/.cache/trivy" config \
            --severity HIGH,CRITICAL \
            --format json \
            --output reports/trivy-iac.json \
            .
        '''
      }
      post {
        success {
          sh 'python3 devsecops_report.py record --id iac-analysis --status passed --summary "Trivy Config a terminé l’analyse de la configuration réellement utilisée par le projet; les éventuels findings restent visibles dans le rapport et la dashboard." --command "trivy config --severity HIGH,CRITICAL ." --artifact reports/trivy-iac.json --results reports/devsecops-results.json'
        }
        failure {
          sh 'python3 devsecops_report.py record --id iac-analysis --status failed --summary "L’analyse de la configuration du projet a échoué; consulter le rapport Trivy." --command "trivy config --severity HIGH,CRITICAL ." --artifact reports/trivy-iac.json --results reports/devsecops-results.json'
        }
      }
    }

    stage('Code Quality Check via SonarQube') {
      when {
        expression { params.RUN_SONAR }
      }
      steps {
        withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
          dir('backend') {
            retry(3) {
              sh 'mvn -B -U org.sonarsource.scanner.maven:sonar-maven-plugin:5.1.0.4751:sonar -Dsonar.projectKey=devops-catalog -Dsonar.sources=src/main/java -Dsonar.host.url="$SONARQUBE_URL" -Dsonar.token="$SONAR_TOKEN"'
            }
          }
          sh 'python3 sonarqube_report.py --base-url "$SONARQUBE_URL" --project-key devops-catalog --output-dir reports'
        }
      }
      post {
        success {
          sh 'python3 devsecops_report.py record --id sonarqube --status passed --summary "Analyse SonarQube terminee; vulnerabilites et hotspots recuperes via lAPI." --command "Maven SonarQube scanner + API issues/hotspots" --artifact reports/sonarqube-issues.json --artifact reports/sonarqube-hotspots.json --results reports/devsecops-results.json'
          sh 'python3 devsecops_report.py record --id secure-coding --status passed --summary "Les règles de sécurité du profil SonarQube ont été exécutées sur le code Java; consulter issues et hotspots." --command "SonarQube security analysis" --artifact reports/sonarqube-issues.json --artifact reports/sonarqube-hotspots.json --results reports/devsecops-results.json'
        }
        failure {
          sh 'python3 devsecops_report.py record --id sonarqube --status failed --summary "Analyse ou recuperation des resultats non terminee; verifier le jeton, les permissions et le journal Jenkins." --command "Maven SonarQube scanner + API issues/hotspots" --artifact reports/sonarqube-issues.json --artifact reports/sonarqube-hotspots.json --results reports/devsecops-results.json'
          sh 'python3 devsecops_report.py record --id secure-coding --status failed --summary "Les règles de sécurité SonarQube n\'ont pas pu être évaluées; consulter le stage SonarQube." --command "SonarQube security analysis" --artifact reports/sonarqube-issues.json --artifact reports/sonarqube-hotspots.json --results reports/devsecops-results.json'
        }
      }
    }

    stage('Building our images') {
      steps {
        sh 'docker compose --project-name "$COMPOSE_PROJECT_NAME" build --pull backend frontend'
      }
    }

    stage('Resolved Compose and local safeguards') {
      steps {
        sh '''
          set +e
          docker compose --project-name "$COMPOSE_PROJECT_NAME" config --format json | \
            python3 devsecops_checks.py compose-config --project-root . --output reports/configuration-checks.json
          result=$?
          set -e
          python3 devsecops_report.py record-check-report \
            --report reports/configuration-checks.json \
            --id acceptance-iac \
            --id infrastructure-compliance \
            --id configuration-safety \
            --id secrets-management \
            --command "docker compose config --format json + local safety checks" \
            --results reports/devsecops-results.json
          exit "$result"
        '''
      }
    }

    stage('Trivy vulnerability scan') {
      steps {
        catchError(
          buildResult: 'UNSTABLE',
          stageResult: 'UNSTABLE',
          message: 'Trivy found HIGH/CRITICAL vulnerabilities; continuing so the remaining security scans can complete.'
        ) {
          sh '''
          set +e
          mkdir -p reports
          rm -f reports/trivy-scan-completed
          : > reports/trivy-scan.log
          if trivy --timeout 30m --cache-dir "$JENKINS_HOME/.cache/trivy" image --scanners vuln --severity LOW,MEDIUM,HIGH,CRITICAL --ignore-unfixed --format json --output reports/trivy-backend.json --exit-code 0 devops-catalog-backend:local >> reports/trivy-scan.log 2>&1; then
            backend_status=0
          else
            backend_status=$?
          fi
          cat reports/trivy-scan.log
          if trivy --timeout 30m --cache-dir "$JENKINS_HOME/.cache/trivy" image --scanners vuln --severity LOW,MEDIUM,HIGH,CRITICAL --ignore-unfixed --format json --output reports/trivy-frontend.json --exit-code 0 devops-catalog-frontend:local >> reports/trivy-scan.log 2>&1; then
            frontend_status=0
          else
            frontend_status=$?
          fi
          cat reports/trivy-scan.log
          if [ "$backend_status" -ne 0 ] || [ "$frontend_status" -ne 0 ]; then
            exit 1
          fi
          python3 - <<'PY'
import json
from pathlib import Path
import sys

findings = []
counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
for report in (Path("reports/trivy-backend.json"), Path("reports/trivy-frontend.json")):
    data = json.loads(report.read_text(encoding="utf-8"))
    if not isinstance(data.get("Results"), list):
        raise ValueError(f"{report} is missing the Trivy Results array")
    for result in data["Results"]:
        for vulnerability in result.get("Vulnerabilities") or []:
            severity = vulnerability.get("Severity")
            if severity in counts:
                counts[severity] += 1
            if severity in {"HIGH", "CRITICAL"}:
                findings.append(vulnerability)

Path("reports/trivy-scan-completed").touch()
print(
    "Trivy scans completed: "
    + ", ".join(f"{severity}={count}" for severity, count in counts.items())
)
if findings:
    for vulnerability in findings:
        print(
            f"{vulnerability.get('Severity')} "
            f"{vulnerability.get('VulnerabilityID')} "
            f"{vulnerability.get('PkgName')} "
            f"{vulnerability.get('InstalledVersion')}"
        )
    sys.exit(1)
PY
          '''
        }
      }
      post {
        success {
          sh 'python3 devsecops_report.py record --id sca --status passed --summary "Trivy a analysé les composants Java embarqués dans les images backend/frontend; consulter les compteurs de sévérité et les rapports liés." --command "trivy image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed" --artifact reports/trivy-backend.json --artifact reports/trivy-frontend.json --artifact reports/trivy-scan.log --results reports/devsecops-results.json'
          sh 'python3 devsecops_report.py record --id trivy --status passed --summary "Le scan Trivy des images backend et frontend s’est terminé; consulter les compteurs de sévérité et les rapports liés." --command "trivy image --severity HIGH,CRITICAL --ignore-unfixed" --artifact reports/trivy-backend.json --artifact reports/trivy-frontend.json --artifact reports/trivy-scan.log --results reports/devsecops-results.json'
          sh 'python3 devsecops_report.py record --id continuous-scanning --status passed --summary "Les scans Trivy IaC et images se sont exécutés; consulter les métriques et rapports associés." --command "Trivy config + image" --artifact reports/trivy-iac.json --artifact reports/trivy-backend.json --artifact reports/trivy-frontend.json --artifact reports/trivy-scan.log --results reports/devsecops-results.json'
        }
        unstable {
          script {
            if (fileExists('reports/trivy-scan-completed')) {
              sh 'python3 devsecops_report.py record --id sca --status failed --summary "Trivy a détecté des vulnérabilités HIGH/CRITICAL dans les images; les constats MEDIUM/LOW restent informatifs. Consulter les détails CVE." --command "trivy image --scanners vuln --severity LOW,MEDIUM,HIGH,CRITICAL --ignore-unfixed" --artifact reports/trivy-backend.json --artifact reports/trivy-frontend.json --artifact reports/trivy-scan.log --results reports/devsecops-results.json'
              sh 'python3 devsecops_report.py record --id trivy --status failed --summary "La règle de sécurité Trivy a trouvé des CVE HIGH/CRITICAL; le build est UNSTABLE et les autres scans continuent." --command "trivy image --severity LOW,MEDIUM,HIGH,CRITICAL --ignore-unfixed" --artifact reports/trivy-backend.json --artifact reports/trivy-frontend.json --artifact reports/trivy-scan.log --results reports/devsecops-results.json'
              sh 'python3 devsecops_report.py record --id continuous-scanning --status passed --summary "Les scans Trivy IaC et images se sont terminés; consulter les rapports associés pour les vulnérabilités détectées." --command "Trivy config + image" --artifact reports/trivy-iac.json --artifact reports/trivy-backend.json --artifact reports/trivy-frontend.json --artifact reports/trivy-scan.log --results reports/devsecops-results.json'
            }
          }
        }
        failure {
          script {
            if (fileExists('reports/trivy-scan-completed')) {
              sh 'python3 devsecops_report.py record --id sca --status passed --summary "Le scan SCA s’est terminé avec des rapports valides; la règle HIGH/CRITICAL a bloqué la suite du pipeline." --command "trivy image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed" --artifact reports/trivy-backend.json --artifact reports/trivy-frontend.json --artifact reports/trivy-scan.log --results reports/devsecops-results.json'
              sh 'python3 devsecops_report.py record --id trivy --status passed --summary "Les scans Trivy des images sont terminés; la règle HIGH/CRITICAL a bloqué la suite du pipeline." --command "trivy image --severity HIGH,CRITICAL --ignore-unfixed" --artifact reports/trivy-backend.json --artifact reports/trivy-frontend.json --artifact reports/trivy-scan.log --results reports/devsecops-results.json'
              sh 'python3 devsecops_report.py record --id continuous-scanning --status passed --summary "Les scans Trivy IaC et images sont terminés; des findings de sévérité HIGH/CRITICAL bloquent la suite du pipeline." --command "Trivy config + image" --artifact reports/trivy-iac.json --artifact reports/trivy-backend.json --artifact reports/trivy-frontend.json --artifact reports/trivy-scan.log --results reports/devsecops-results.json'
            } else {
              sh 'python3 devsecops_report.py record --id sca --status failed --summary "Le scan SCA Trivy n’a pas produit deux rapports JSON valides; consulter le journal d’exécution." --command "trivy image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed" --artifact reports/trivy-backend.json --artifact reports/trivy-frontend.json --artifact reports/trivy-scan.log --results reports/devsecops-results.json'
              sh 'python3 devsecops_report.py record --id trivy --status failed --summary "Le scan Trivy des images n’a pas abouti; consulter le journal et les rapports partiels." --command "trivy image --severity HIGH,CRITICAL --ignore-unfixed" --artifact reports/trivy-backend.json --artifact reports/trivy-frontend.json --artifact reports/trivy-scan.log --results reports/devsecops-results.json'
              sh 'python3 devsecops_report.py record --id continuous-scanning --status failed --summary "Au moins un scan Trivy n’a pas abouti; consulter le journal et les rapports IaC/images liés." --command "Trivy config + image" --artifact reports/trivy-iac.json --artifact reports/trivy-backend.json --artifact reports/trivy-frontend.json --artifact reports/trivy-scan.log --results reports/devsecops-results.json'
            }
          }
        }
      }
    }

    stage('Publish to Nexus') {
      when {
        expression { params.PUBLISH_NEXUS }
      }
      steps {
        withCredentials([usernamePassword(credentialsId: 'nexus-credentials', usernameVariable: 'NEXUS_USER', passwordVariable: 'NEXUS_PASSWORD')]) {
          script {
            def xmlEscape = { value ->
              value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')
            }
            writeFile file: 'backend/.maven-settings.xml', text: """<settings><servers><server><id>nexus-releases</id><username>${xmlEscape(env.NEXUS_USER)}</username><password>${xmlEscape(env.NEXUS_PASSWORD)}</password></server></servers></settings>"""
          }
          dir('backend') {
            sh '''
              set -eu
              trap 'rm -f .maven-settings.xml .nexus-user.json' EXIT
              role_url="$NEXUS_URL/service/rest/v1/security/roles/jenkins-maven-releases-publisher"
              role_body='{"id":"jenkins-maven-releases-publisher","name":"Jenkins Maven Releases Publisher","description":"Publish artifacts to the local maven-releases repository","privileges":["nx-repository-view-maven2-maven-releases-add","nx-repository-view-maven2-maven-releases-edit","nx-repository-view-maven2-maven-releases-read","nx-repository-view-maven2-maven-releases-browse"],"roles":[]}'
              role_status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --user "$NEXUS_USER:$NEXUS_PASSWORD" "$role_url")"
              if [ "$role_status" = 404 ]; then
                curl --fail --silent --show-error --user "$NEXUS_USER:$NEXUS_PASSWORD" --header 'Content-Type: application/json' --request POST --data "$role_body" "$NEXUS_URL/service/rest/v1/security/roles"
              else
                curl --fail --silent --show-error --user "$NEXUS_USER:$NEXUS_PASSWORD" --header 'Content-Type: application/json' --request PUT --data "$role_body" "$NEXUS_URL/service/rest/v1/security/roles/jenkins-maven-releases-publisher"
              fi
              printf '%s\n' '{"userId":"admin","firstName":"Admin","lastName":"Nexus","emailAddress":"admin@example.org","source":"default","status":"active","readOnly":false,"roles":["nx-admin","jenkins-maven-releases-publisher"]}' > .nexus-user.json
              curl --fail --silent --show-error --user "$NEXUS_USER:$NEXUS_PASSWORD" \
                --header 'Content-Type: application/json' \
                --request PUT \
                --data-binary @.nexus-user.json \
                "$NEXUS_URL/service/rest/v1/security/users/admin"
              curl --fail --silent --show-error --user "$NEXUS_USER:$NEXUS_PASSWORD" "$NEXUS_URL/service/rest/v1/security/users?userId=admin" | grep -F 'jenkins-maven-releases-publisher'
              curl --fail --silent --show-error --user "$NEXUS_USER:$NEXUS_PASSWORD" \
                --header 'Content-Type: application/json' \
                --request PUT \
                --data '{"name":"maven-releases","online":true,"storage":{"blobStoreName":"default","strictContentTypeValidation":false,"writePolicy":"ALLOW"},"maven":{"versionPolicy":"RELEASE","layoutPolicy":"STRICT","contentDisposition":"ATTACHMENT"},"component":{"proprietaryComponents":false}}' \
                "$NEXUS_URL/service/rest/v1/repositories/maven/hosted/maven-releases"
              mvn -B -s .maven-settings.xml deploy
            '''
          }
        }
      }
    }

    stage('Publish Docker images') {
      when {
        expression { params.PUBLISH_DOCKER && !params.ENABLE_SECURITY_DEMO }
      }
      steps {
        script {
          if (!params.DOCKERHUB_REPOSITORY?.trim()) {
            error('Set DOCKERHUB_REPOSITORY before enabling PUBLISH_DOCKER.')
          }
          withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASSWORD')]) {
            sh '''
              set +x
              printf '%s' "$DOCKER_PASSWORD" | docker login --username "$DOCKER_USER" --password-stdin
              trap 'docker logout' EXIT
              docker tag devops-catalog-backend:local "$DOCKERHUB_REPOSITORY:backend-$BUILD_NUMBER"
              docker tag devops-catalog-frontend:local "$DOCKERHUB_REPOSITORY:frontend-$BUILD_NUMBER"
              docker push "$DOCKERHUB_REPOSITORY:backend-$BUILD_NUMBER"
              docker push "$DOCKERHUB_REPOSITORY:frontend-$BUILD_NUMBER"
            '''
          }
        }
      }
    }

    stage('Deploy our image') {
      steps {
        withEnv(["SECURITY_DEMO_ENABLED=${params.ENABLE_SECURITY_DEMO}"]) {
          sh '''
            set -eu
            mkdir -p reports
            : > reports/smoke-tests.log
            docker compose --project-name "$COMPOSE_PROJECT_NAME" up --detach --wait mysql backend frontend >> reports/smoke-tests.log 2>&1
            curl --fail --silent --show-error --retry 12 --retry-delay 5 --retry-connrefused \
              --output /dev/null --write-out 'GET /api/health: HTTP %{http_code}\n' \
              http://backend:8080/api/health >> reports/smoke-tests.log 2>&1
            curl --fail --silent --show-error --retry 12 --retry-delay 5 --retry-connrefused \
              --output /dev/null --write-out 'GET /api/products: HTTP %{http_code}\n' \
              http://backend:8080/api/products >> reports/smoke-tests.log 2>&1
            if [ "$SECURITY_DEMO_ENABLED" = "true" ]; then
              curl --fail --silent --show-error \
                --output /dev/null --write-out 'GET /api/security-demo/weak-hash: HTTP %{http_code}\n' \
                'http://backend:8080/api/security-demo/weak-hash?value=devsecops-test' >> reports/smoke-tests.log 2>&1
              curl --fail --silent --show-error \
                --output /dev/null --write-out 'GET /api/security-demo/headers: HTTP %{http_code}\n' \
                http://backend:8080/api/security-demo/headers >> reports/smoke-tests.log 2>&1
            fi
            cat reports/smoke-tests.log
          '''
        }
      }
      post {
        success {
          sh 'python3 devsecops_report.py record --id smoke-tests --status passed --summary "Le healthcheck et la route des produits repondent apres deploiement." --command "curl /api/health et /api/products" --artifact reports/smoke-tests.log --results reports/devsecops-results.json'
        }
        failure {
          sh 'python3 devsecops_report.py record --id smoke-tests --status failed --summary "Un test HTTP dacceptation a echoue." --command "curl /api/health et /api/products" --artifact reports/smoke-tests.log --results reports/devsecops-results.json'
        }
      }
    }

    stage('Infrastructure runtime checks') {
      steps {
        sh '''
          set +e
          python3 devsecops_checks.py runtime --project-name "$COMPOSE_PROJECT_NAME" --output reports/runtime-checks.json
          result=$?
          set -e
          python3 devsecops_report.py record-check-report \
            --report reports/runtime-checks.json \
            --id infrastructure-tests \
            --id server-hardening \
            --command "docker compose ps + docker inspect" \
            --results reports/devsecops-results.json
          exit "$result"
        '''
      }
    }

    stage('Post-deployment security smoke tests') {
      steps {
        sh '''
          set +e
          python3 devsecops_checks.py security-smoke --api-url http://backend:8080 --output reports/security-smoke-checks.json
          result=$?
          set -e
          python3 devsecops_report.py record-check-report \
            --report reports/security-smoke-checks.json \
            --id security-smoke-tests \
            --command "GET /api/health + GET /api/products + security headers" \
            --results reports/devsecops-results.json
          exit "$result"
        '''
      }
    }

    stage('Controlled backend recovery test') {
      steps {
        sh '''
          set +e
          mkdir -p reports
          : > reports/fault-injection.log
          docker compose --project-name "$COMPOSE_PROJECT_NAME" restart backend >> reports/fault-injection.log 2>&1
          result=$?
          if [ "$result" -eq 0 ]; then
            curl --fail --silent --show-error --retry 12 --retry-delay 5 --retry-all-errors \
              --output /dev/null --write-out 'GET /actuator/health/readiness: HTTP %{http_code}\n' \
              http://backend:8080/actuator/health/readiness >> reports/fault-injection.log 2>&1
            result=$?
          fi
          set -e
          cat reports/fault-injection.log
          exit "$result"
        '''
      }
      post {
        success {
          sh 'python3 devsecops_report.py record --id fault-injection --status passed --summary "Le redémarrage contrôlé du backend a été suivi d\'un retour à l\'état readiness." --command "docker compose restart backend + readiness probe" --artifact reports/fault-injection.log --results reports/devsecops-results.json'
        }
        failure {
          sh 'python3 devsecops_report.py record --id fault-injection --status failed --summary "Le backend ne s\'est pas rétabli après le redémarrage contrôlé." --command "docker compose restart backend + readiness probe" --artifact reports/fault-injection.log --results reports/devsecops-results.json'
        }
      }
    }

    stage('Continuous monitoring verification') {
      steps {
        withEnv(["SECURITY_DEMO_ENABLED=${params.ENABLE_SECURITY_DEMO}"]) {
          sh '''
            set -eu
            docker compose --project-name "$COMPOSE_PROJECT_NAME" --profile monitoring up --detach --wait prometheus grafana
            set +e
            python3 devsecops_checks.py monitoring \
              --prometheus-url http://prometheus:9090 \
              --grafana-url http://grafana:3000 \
              --output reports/monitoring-checks.json
            result=$?
            set -e
            python3 devsecops_report.py record-check-report \
              --report reports/monitoring-checks.json \
              --id continuous-monitoring \
              --command "Prometheus targets API + Grafana health API" \
              --results reports/devsecops-results.json
            exit "$result"
          '''
        }
      }
    }

    stage('ZAP DAST acceptance scan') {
      steps {
        withEnv([
          "SECURITY_DEMO_ENABLED=${params.ENABLE_SECURITY_DEMO}",
          "ZAP_TARGET=${params.ENABLE_SECURITY_DEMO ? 'http://backend:8080/api/security-demo/headers' : 'http://backend:8080/api/products'}"
        ]) {
          sh '''
            set -eu
            mkdir -p "$WORKSPACE/reports"
            scan_container="${COMPOSE_PROJECT_NAME}-zap-${BUILD_NUMBER}"
            scan_volume="${COMPOSE_PROJECT_NAME}-zap-work-${BUILD_NUMBER}"
            trap 'docker rm --force "$scan_container" >/dev/null 2>&1 || true; docker volume rm "$scan_volume" >/dev/null 2>&1 || true' EXIT
            docker volume create "$scan_volume" >/dev/null
            docker run --rm \
              --user 0:0 \
              --entrypoint sh \
              --mount "type=volume,source=$scan_volume,target=/zap/wrk" \
              ghcr.io/zaproxy/zaproxy:2.17.0 \
              -c 'chown 1000:1000 /zap/wrk'
            docker create \
              --name "$scan_container" \
              --network "${COMPOSE_PROJECT_NAME}_default" \
              --mount "type=volume,source=$scan_volume,target=/zap/wrk" \
              ghcr.io/zaproxy/zaproxy:2.17.0 \
              zap-baseline.py -z "-silent" -t "$ZAP_TARGET" -m 1 -I -r zap-report.html -J zap-report.json
            docker start "$scan_container" >/dev/null
            scan_status="$(docker wait "$scan_container")"
            docker logs "$scan_container"
            docker cp "$scan_container:/zap/wrk/zap-report.html" "$WORKSPACE/reports/zap-report.html"
            docker cp "$scan_container:/zap/wrk/zap-report.json" "$WORKSPACE/reports/zap-report.json"
            if [ "$scan_status" -ne 0 ]; then
              exit "$scan_status"
            fi
          '''
        }
      }
      post {
        success {
          sh 'python3 devsecops_report.py record --id zap --status passed --summary "OWASP ZAP Baseline a terminé le scan passif; consulter les alertes MEDIUM/LOW dans le rapport archivé." --command "zap-baseline.py -t ZAP_TARGET -I" --artifact reports/zap-report.html --artifact reports/zap-report.json --results reports/devsecops-results.json'
        }
        failure {
          sh 'python3 devsecops_report.py record --id zap --status failed --summary "Le scan ZAP a échoué; consulter le rapport et la console." --command "zap-baseline.py -t ZAP_TARGET -I" --artifact reports/zap-report.html --artifact reports/zap-report.json --results reports/devsecops-results.json'
        }
      }
    }

    stage('Email verification') {
      when {
        expression { params.EMAIL_TO?.trim() }
      }
      steps {
        emailext(
          to: params.EMAIL_TO.trim(),
          subject: "Deployment verified: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
          body: """The DevOps pipeline completed successfully.

Build: ${env.BUILD_URL}
Application: http://localhost:8081
API health: http://localhost:8080/api/health

This message confirms that the deployment and HTTP smoke tests passed."""
        )
      }
    }
  }

  post {
    always {
      script {
        env.DEVSECOPS_BUILD_RESULT = currentBuild.currentResult
        env.DEVSECOPS_PUBLIC_BASE_URL = params.JENKINS_PUBLIC_URL?.trim() ?: ''
        def publicBaseUrl = env.DEVSECOPS_PUBLIC_BASE_URL.replaceAll('/+$', '')
        env.DEVSECOPS_BUILD_URL = env.BUILD_URL ?: (
          publicBaseUrl
            ? "${publicBaseUrl}/job/${env.JOB_NAME}/${env.BUILD_NUMBER}/"
            : ''
        )
      }
      sh 'python3 devsecops_report.py generate --results reports/devsecops-results.json --output reports/devsecops-report.html --build-number "$BUILD_NUMBER" --build-url "$DEVSECOPS_BUILD_URL" --public-base-url "$DEVSECOPS_PUBLIC_BASE_URL" --build-result "$DEVSECOPS_BUILD_RESULT"'
      publishHTML(target: [
        allowMissing: false,
        alwaysLinkToLastBuild: true,
        keepAll: true,
        reportDir: 'reports',
        reportFiles: 'devsecops-report.html',
        includes: '**/*',
        reportName: 'Dashboard DevSecOps'
      ])
      archiveArtifacts artifacts: 'reports/**,backend/target/site/jacoco/**', allowEmptyArchive: true, fingerprint: true
    }
  }
}
