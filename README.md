# DevSecOps Platform — Catalogue produits

Projet technique de démonstration orienté **DevSecOps** : une application simple de gestion de catalogue produits (CRUD) intégrée à une chaîne locale d’automatisation, de contrôles de sécurité et de supervision. Il ne s’agit ni d’un projet de fin d’études (PFE) ni d’un projet de stage, mais d’un projet technique pour mettre en pratique les bonnes pratiques DevSecOps sur un périmètre maîtrisé.

## Objectifs

- Illustrer l’intégration de contrôles de sécurité dans le cycle de développement (shift-left, CI/CD, runtime).
- Fournir une stack reproductible en local via Docker Compose (application, outils DevOps et monitoring).
- Produire des rapports exploitables à partir des résultats réels des outils (sans findings simulés).

## Contenu du dépôt

| Élément | Rôle |
|---|---|
| [`backend/`](./backend) | API Spring Boot (Java 17, Maven) : endpoints produits/santé, validation, tests, Actuator/Prometheus. |
| [`frontend/`](./frontend) | Interface web statique (Nginx) consommant l’API `/api`. |
| [`docker-compose.yml`](./docker-compose.yml) | Orchestration des services (app, profils `devops` et `monitoring`), volumes persistants. |
| [`Jenkinsfile`](./Jenkinsfile) | Pipeline déclaratif (préparation, contrôles, build, scans, déploiement, tests, rapport). |
| [`jenkins/`](./jenkins), [`monitoring/`](./monitoring) | Images/configurations Jenkins, Prometheus et Grafana provisionnés. |
| [`.pre-commit-config.yaml`](./.pre-commit-config.yaml) | Hooks de qualité/sécurité avant commit (dont Gitleaks et Commitizen). |
| [`devsecops_checks.py`](./devsecops_checks.py), [`devsecops_report.py`](./devsecops_report.py), [`sonarqube_report.py`](./sonarqube_report.py) | Génération et consolidation des rapports DevSecOps. |
| [`THREAT-MODEL.md`](./THREAT-MODEL.md) | Revue de menaces simplifiée (STRIDE) pour le périmètre local. |
| [`tests/`](./tests), [`reports/`](./reports) | Tests Python des scripts de reporting et exemples/artefacts de rapports. |

Documentation complémentaire présente dans le dépôt : [`COURS-DEVOPS-DEBUTANT.md`](./COURS-DEVOPS-DEBUTANT.md), [`RAPPORT-TECHNIQUE.md`](./RAPPORT-TECHNIQUE.md), [`OFFLINE-PACKAGE.md`](./OFFLINE-PACKAGE.md), [`RAPPORT-EXPLICATION-PROJET.*`](./RAPPORT-EXPLICATION-PROJET.md).

## Sécurité et pratiques DevSecOps

Cette section décrit les contrôles intégrés au projet, avec un focus sur la sécurité applicative, de la chaîne de build et de l’exécution.

### 1. Hygiène du code et prévention des fuites (shift-left)

- **Pre-commit** ([`.pre-commit-config.yaml`](./.pre-commit-config.yaml)) : espaces/fins de ligne, YAML, conflits de fusion, détection de clés privées, limite de taille de fichiers.
- **Gitleaks** : détection de secrets dans les changements indexés (hook local et étape dédiée en pipeline).
- **Commitizen** : validation des messages au format *Conventional Commits* (`commit-msg` local ; contrôle du message SCM/paramètre en pipeline selon le mode).
- **Gestion des secrets** : `.env` est ignoré par Git (mots de passe de démonstration locaux uniquement) ; les secrets réels doivent être fournis via des mécanismes dédiés (ex. Jenkins Credentials), jamais versionnés.

### 2. Analyse statique et tests (SAST / qualité / sécurité)

- **Maven + JUnit** (`backend/`) : compilation, tests (H2 en mémoire pour les tests web) et rapports de tests/couverture (JaCoCo).
- **SonarQube** (profil `devops`) : analyse de la qualité et des problèmes de sécurité du code Java lorsque le pipeline est configuré avec un jeton (`sonar-token`).
- **Mode démo sécurité** (`SECURITY_DEMO_ENABLED`, désactivé par défaut) : endpoint/page de test volontairement faibles pour valider la détection par les scanners ; le contrôleur reste inactif hors mode démo et aucune donnée sensible réelle n’est exposée. Ne pas activer pour une publication d’images.

### 3. Dépendances, images et infrastructure (SCA / IaC / supply chain)

- **Trivy (SCA conteneur/images)** : analyse des composants logiciels et du système des images backend/frontend construites ; rapports LOW→CRITICAL, avec seuil de politique bloquant/instable ciblé sur les vulnérabilités **corrigibles HIGH/CRITICAL** (selon configuration pipeline).
- **Trivy Config (IaC)** : analyse de la configuration d’infrastructure (ex. Compose) pour rendre visibles les écarts de configuration.
- **Dépendances applicatives** : versions de dépendances gérées dans [`backend/pom.xml`](./backend/pom.xml) (mises à niveau appliquées pour corriger des constats identifiés par les scans dans ce contexte de lab).
- **Nexus** (optionnel, profil `devops`) : publication contrôlée d’artefacts Maven dans un dépôt local de laboratoire.

### 4. Sécurité dynamique et vérifications runtime (DAST / posture à l’exécution)

- **OWASP ZAP Baseline** : scan passif (spider + règles passives) de l’API/endpoint de démonstration déployé, rapports HTML/JSON archivés (sans tests actifs destructifs).
- **Vérifications post-déploiement** (pipeline) : healthchecks, contrôles runtime/privilèges, tests HTTP et en-têtes de sécurité, test de reprise après redémarrage contrôlé du backend.
- **Exposition réseau locale** : les ports applicatifs sont publiés sur `127.0.0.1` dans la configuration Compose ; l’application de lab n’intègre pas d’authentification utilisateur et ne doit pas être exposée à un réseau non fiable sans durcissement.

### 5. Supervision et exploitation

- **Prometheus / Grafana** (profil `monitoring`) : collecte et visualisation des métriques applicatives (endpoint Actuator Prometheus) via configuration provisionnée.
- **Traçabilité** : exécutions Jenkins, artefacts et rapports consolidés (`reports/devsecops-report.*`, `reports/devsecops-results.json`) pour relier contrôles, preuves et résultats.

### 6. Modélisation des menaces et limites

- **Threat model** : voir [`THREAT-MODEL.md`](./THREAT-MODEL.md) (revue STRIDE simplifiée : actifs, frontières de confiance, menaces, contrôles existants et actions recommandées pour le périmètre Docker Compose local).
- **Limites importantes** :
  - Les résultats des scanners reflètent le périmètre, les règles et l’exécution au moment du scan ; **l’absence de finding ne garantit pas l’absence de vulnérabilité**.
  - Le socket Docker monté dans Jenkins et certains choix de configuration sont adaptés à un **laboratoire local de confiance**, pas à un environnement multi-utilisateur ou exposé.
  - Nexus, SonarQube, publication d’images, e-mail, etc. nécessitent une configuration/credentials explicites selon les besoins ; certaines étapes sont optionnelles ou conditionnées par des paramètres.

## Prérequis

- **Recommandé** : Ubuntu/WSL2 (ou Linux) avec Docker Engine et Docker Compose v2.
- Pour le build local du backend : Java 17, Maven, Git, Python 3.
- Profil complet (`--all`) : prévoir des ressources suffisantes (RAM, disque) ; SonarQube peut nécessiter `vm.max_map_count=262144`.

Vérifications utiles :
```bash
docker --version
docker compose version
java -version
mvn -version
```

## Démarrage rapide

Depuis la racine du projet (`devops-platform`) :

```bash
# Crée .env si absent (mots de passe de démonstration locaux)
bash ./setup.sh                 # application + base de données
bash ./setup.sh --tools         # + Jenkins, SonarQube, Nexus
bash ./setup.sh --monitoring    # + Prometheus, Grafana
bash ./setup.sh --all           # stack complète
```

Sous Windows sans Docker dans le PATH, exécuter ces commandes depuis Ubuntu WSL dans le dossier monté du projet, par exemple :
```bash
wsl -d Ubuntu
cd "/mnt/c/Users/<user>/.../devops-platform"
bash ./setup.sh --all
```

Arrêt :
```bash
bash ./down.sh                                    # conserve les volumes
docker compose --profile devops --profile monitoring down -v   # supprime aussi les données (destructif)
```

## Accès aux services

| Service | URL | Accès |
|---|---|---|
| Application web | http://localhost:8081 | — |
| API | http://localhost:8080 | — |
| Santé API (Actuator) | http://localhost:8080/actuator/health | — |
| Métriques Prometheus (app) | http://localhost:8080/actuator/prometheus | — |
| Jenkins | http://localhost:8083 | `JENKINS_ADMIN_ID` / `JENKINS_ADMIN_PASSWORD` (`.env`) |
| SonarQube | http://localhost:9000 | premier accès `admin` / `admin` puis changement requis |
| Nexus | http://localhost:8082 | `admin` ; mot de passe initial selon initialisation/volume (voir README Nexus/`admin.password` si présent) |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` (`.env`) |

> Modifier les identifiants/mots de passe par défaut avant toute utilisation hors machine locale. Ne pas exposer ces services sans durcissement approprié.

## API (exemples)

```text
GET    /api/health
GET    /api/products
GET    /api/products/{id}
POST   /api/products
PUT    /api/products/{id}
DELETE /api/products/{id}
```

Exemple :
```bash
curl -X POST http://localhost:8080/api/products \
  -H 'Content-Type: application/json' \
  -d '{"name":"Clavier","description":"USB","price":49.90,"stock":8}'
```

## Pipeline CI/CD et rapports

- Le pipeline Jenkins est défini dans [`Jenkinsfile`](./Jenkinsfile) (job chargé depuis le workspace monté en environnement local ; pour SCM distant, configurer un job *Pipeline script from SCM*).
- Les contrôles couvrent notamment : hooks/pre-commit, Gitleaks, build/tests Maven, analyse SonarQube (si configurée), scans Trivy (IaC/images), validations de configuration/runtime, DAST ZAP, et consolidation des résultats.
- Les rapports sont produits dans [`reports/`](./reports) (artefacts natifs et tableau de bord HTML/CSS générés par `devsecops_report.py`).
- Les exécutions et options (publication Nexus/Docker Hub, e-mail, mode démo sécurité, etc.) dépendent des paramètres Jenkins, credentials et configuration de l’environnement.

Régénération locale du rapport (exemple) :
```bash
mkdir -p reports
mvn -f backend/pom.xml -B clean verify
cp backend/target/surefire-reports/TEST-com.example.devops.ProductControllerTest.xml reports/maven-tests.xml
python3 devsecops_report.py init --project-root . --results reports/devsecops-results.json
python3 devsecops_report.py record --id maven-tests --status passed \
  --summary "Tests Maven terminés" --command "mvn -f backend/pom.xml -B clean verify" \
  --artifact reports/maven-tests.xml --results reports/devsecops-results.json
python3 devsecops_report.py generate --results reports/devsecops-results.json --output reports/devsecops-report.html
```

Tests des scripts de reporting :
```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Git et conventions

- Initialiser le dépôt dans `devops-platform` si nécessaire : `git init -b main`
- Installer les hooks recommandés : `pre-commit install` et `pre-commit install --hook-type commit-msg` (voir `.pre-commit-config.yaml`)
- Utiliser des messages **Conventional Commits** (ex. `feat(...)`, `fix(...)`, `docs(...)`)
- Ne pas versionner `.env`, les sorties Maven (`target/`) ni les données d’exécution sensibles ; vérifier `git status` avant commit/push.

## Notes

- Projet destiné à un usage **local/de démonstration technique**. Pour un déploiement partagé ou productif : ajouter authentification/autorisation, gestion des secrets robuste, durcissement réseau et des conteneurs, politique de vulnérabilités et revue de configuration adaptées.
- Les performances et l’empreinte mémoire dépendent des profils activés (SonarQube/Jenkins/Nexus en particulier).

