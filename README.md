# Projet DevOps - catalogue de produits

Application pedagogique de catalogue (CRUD) pour relier le code, les tests, le controle de qualite, le stockage des artefacts, les images Docker, le deploiement et la supervision dans un pipeline Jenkins.

Pour une presentation detaillee de l'architecture, du code, des outils, du pipeline et de l'exploitation, consulte le [cours professionnel DevOps](./COURS-DEVOPS-DEBUTANT.md). Le [rapport de fin d'etudes](./RAPPORT-FIN-ETUDES.md) presente la realisation, les diagrammes, les resultats et les limites du projet.

## Correspondance avec le cours

| Notion du cours | Mise en pratique |
|---|---|
| Introduction DevOps | Pipeline de l'integration jusqu'au deploiement et a la supervision |
| Git | Deposer le projet dans un depot Git; Jenkins recupere le `Jenkinsfile` depuis ce depot |
| Jenkins | Pipeline declaratif `Jenkinsfile`, declenchement manuel ou webhook SCM |
| Maven | `backend/pom.xml`, `mvn clean verify`, tests et rapport JaCoCo |
| SonarQube | Etape d'analyse activable apres configuration d'un jeton Jenkins |
| Nexus | Publication optionnelle du JAR Maven dans un depot hosted |
| Docker | Images du backend Spring Boot et du frontend Nginx |
| Docker Compose et volumes | MySQL, application, outils DevOps et donnees persistantes par volumes nommes |
| Surveillance continue | Endpoint Prometheus, Prometheus et tableau de bord Grafana provisionne |
| PRE-COMMIT | Hooks `pre-commit`, dont Gitleaks contre les secrets dans les changements indexes |
| COMMIT | Conventional Commits valides par Commitizen avant le commit et en CI/SCM |
| Modelisation des menaces | Revue STRIDE simplifiee dans [THREAT-MODEL.md](./THREAT-MODEL.md) |
| SAST et tests securite | Analyse Java SonarQube et tests de securite JUnit |
| SCA / securite des conteneurs | Trivy rapporte les vulnerabilites LOW a CRITICAL corrigeables; HIGH/CRITICAL restent le seuil de politique |
| DAST / acceptance | ZAP Baseline effectue un scan passif et archive les rapports HTML et JSON |

Le backend utilise Spring Boot 4.0.8 / Spring Framework 7.0.9. Les versions Tomcat 11.0.25 et Jackson 3.1.7 sont fixees dans `backend/pom.xml` aux versions corrigees confirmees par les scans Trivy; cette mise a niveau supprime les findings critiques Spring/Tomcat et les findings HIGH Jackson observes sur les anciennes images.

Cette selection reprend quelques pratiques de la phase Develop du cours, sans ajouter tous les outils de la liste. L'analyse IaC, les plugins IDE et les revues par les pairs restent des pratiques d'equipe distinctes.

Le mode demo de securite (`SECURITY_DEMO_ENABLED=false` par defaut dans Compose) ajoute, lorsqu'il est active, un endpoint MD5 avec CORS permissif (`GET /api/security-demo/weak-hash`) et une page HTML statique de test avec CORS permissif, `X-Content-Type-Options` vide, et sans CSP ni `X-Frame-Options` (`GET /api/security-demo/headers`). ZAP Baseline effectue un scan passif de cette page; il n'effectue pas de scan actif XSS. Trivy conserve son controle de politique HIGH/CRITICAL et archive aussi ses constats MEDIUM/LOW; les niveaux MEDIUM/LOW sont informatifs et n'empechent pas la fin du pipeline. Aucune dependance connue comme CRITICAL n'est ajoutee au profil demo. Docker Hub n'est pas publie tant que `ENABLE_SECURITY_DEMO` est actif; desactivez ce parametre pour une publication normale. Les ports hote frontend/backend restent limites a `127.0.0.1`.

## Ouvrir le projet dans Ubuntu (WSL)

Ouvre l'application **Ubuntu** depuis le menu Demarrer, puis :

```bash
cd "/mnt/d/5NIDS/Labs Cybersecurity and Coding/DevOps_Project/devops-platform"
```

Le projet est conserve sur le lecteur Windows `D:` et travaille depuis Ubuntu/WSL2. Le noyau Ubuntu WSL2 etait demarrable lors de la preparation du projet. Pour recontroler cote Windows :

```powershell
Get-CimInstance Win32_ComputerSystem | Select-Object HypervisorPresent
wsl --list --verbose
```

## Prerequis Ubuntu

Installer Java 17, Maven, Git, Docker Engine et Compose v2 :

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git python3 openjdk-17-jdk-headless maven docker.io docker-compose-v2
sudo service docker start
docker version
docker compose version
docker run --rm hello-world
```

Si le service Docker indique qu'il n'est pas disponible, active systemd pour WSL dans `/etc/wsl.conf` :

```ini
[boot]
systemd=true
```

Puis, depuis PowerShell Windows, execute `wsl --shutdown`, rouvre Ubuntu et verifie `sudo systemctl start docker`. L'ajout de l'utilisateur au groupe `docker` facilite l'usage sans `sudo`, mais ce groupe accorde des privileges proches de root.

Le profil complet (Jenkins, SonarQube, Nexus, Prometheus, Grafana) consomme beaucoup de memoire. Prevoir 8 Go de RAM au minimum pour Ubuntu/WSL, davantage pour tout lancer simultanement. SonarQube a besoin de :

```bash
sudo sysctl -w vm.max_map_count=262144
```

## Construire et tester avec Maven

```bash
cd backend
mvn -B clean verify
```

Les tests web utilisent H2 en memoire; le lancement local complet et Compose utilisent MySQL. Pour construire et lancer uniquement application + base de donnees :

```bash
cd ..
bash ./setup.sh
```

L'interface est sur `http://localhost:8081`; l'API est sur `http://localhost:8080`. `./setup.sh` cree `.env` a partir de `.env.example` si necessaire. Les valeurs fournies sont uniquement des mots de passe de demonstration : change-les avant toute exposition ou utilisation hors de la machine locale.

Endpoints utiles :

```text
GET    /api/health
GET    /api/products
GET    /api/products/{id}
POST   /api/products
PUT    /api/products/{id}
DELETE /api/products/{id}
GET    /actuator/health
GET    /actuator/prometheus
```

Exemple de creation :

```bash
curl -X POST http://localhost:8080/api/products \
  -H 'Content-Type: application/json' \
  -d '{"name":"Clavier","description":"USB","price":49.90,"stock":8}'
```

## Lancer les outils DevOps

Depuis la racine `devops-platform` dans Ubuntu :

```bash
bash ./setup.sh --tools       # Jenkins, SonarQube et Nexus avec l'application
bash ./setup.sh --monitoring   # Prometheus et Grafana avec l'application
bash ./setup.sh --all          # toute la plateforme
```

| Service | URL | Connexion |
|---|---|---|
| Application web | http://localhost:8081 | aucune |
| API | http://localhost:8080 | aucune |
| Jenkins | http://localhost:8083 | `JENKINS_ADMIN_ID` et `JENKINS_ADMIN_PASSWORD` dans `.env` |
| SonarQube | http://localhost:9000 | premier acces : `admin` / `admin`, puis changer le mot de passe |
| Nexus | http://localhost:8082 | `admin`; mot de passe initial dans `/nexus-data/admin.password` du conteneur |
| Prometheus | http://localhost:9090 | aucune |
| Grafana | http://localhost:3000 | `GRAFANA_ADMIN_USER` et `GRAFANA_ADMIN_PASSWORD` dans `.env` |

Au premier acces a Nexus Repository Community Edition (versions 3.77 et ulterieures), lis et accepte l'EULA dans l'assistant d'accueil Nexus. Cette acceptation n'est pas automatisee par Jenkins; tant qu'elle n'est pas faite, Nexus refuse les publications Maven avec une erreur `403`.

Au demarrage, Jenkins charge la definition du job **devops-catalog** depuis le `Jenkinsfile` du dossier monte dans le conteneur. Jenkins s'execute avec son utilisateur non-root; `DOCKER_GID` dans `.env` doit correspondre au groupe du socket Docker WSL (`stat -c '%g' /var/run/docker.sock` depuis Ubuntu), afin que les builds d'images continuent de fonctionner sans lancer Jenkins en root. Apres une modification du Jenkinsfile, redemarrer Jenkins pour recharger sa definition (`docker compose --profile devops restart jenkins`), puis lancer **Build with Parameters**. En mode local, `COMMIT_MESSAGE` est passe au hook Commitizen; la valeur par defaut `test(security): exercise scanner findings` valide le parcours sans inventer d'historique Git. En mode SCM, Commitizen controle le vrai message du dernier commit. `ENABLE_SECURITY_DEMO` active l'endpoint de test pendant le deploiement du pipeline. Pour voir le graphe des etapes, ouvrir **devops-catalog > Full Stage View**; les etapes grisées sont celles dont les parametres ne sont pas actives. Pour un job connecte a un depot Git distant, choisir **Pipeline script from SCM** et decocher ce parametre afin que Jenkins fasse le checkout Git.

Commandes pratiques :

```bash
bash ./status.sh
docker compose logs -f backend
docker compose logs -f jenkins
bash ./down.sh                  # arrete les services, garde les volumes
docker compose down -v          # supprime aussi les donnees persistantes
```

Ne lance pas `docker compose down -v` si les donnees MySQL, Jenkins, Nexus, SonarQube ou Grafana doivent etre conservees.

## Git et configuration du pipeline Jenkins

Pour utiliser Jenkins avec un depot Git distant, initialise/publie `devops-platform` comme racine du depot, puis cree un element Jenkins de type **Pipeline**, definition **Pipeline script from SCM**, et chemin du script `Jenkinsfile`. Un webhook GitHub peut cibler `http://<hote>:8083/github-webhook/` si l'hote est joignable depuis GitHub.

Le pipeline verifie d'abord les outils et la source, puis lance les hooks pre-commit, Gitleaks, Maven, les tests, le rapport informatif des mises a jour de dependances, Trivy Config sur l'IaC et SonarQube. Commitizen valide le parametre `COMMIT_MESSAGE` en mode source locale ou le vrai message du dernier commit en mode SCM. Il construit les images backend/frontend; Trivy analyse les composants logiciels et le systeme des images (SCA conteneur). Il valide ensuite la configuration Compose resolue, les garde-fous locaux sur `.env` et les credentials, publie eventuellement le JAR dans Nexus et les images sur Docker Hub, puis deploie l'application.

Apres le deploiement, Jenkins verifie les healthchecks et les privileges runtime, execute des tests HTTP et de headers de securite, redemarre le backend pour tester sa reprise, active le profil Prometheus/Grafana et verifie la cible scrapee et l'API Grafana. OWASP ZAP Baseline effectue enfin un scan passif de l'API. Les rapports correspondants sont archives; l'email apres succes reste facultatif si `EMAIL_TO` et SMTP sont configures.

Le stage pre-commit execute maintenant tous les hooks `pre-commit` configures, Gitleaks inclus; Commitizen est execute separement au stage Git `commit-msg` seulement si un vrai message SCM existe. Gitleaks est aussi relance dans son stage dedie pour obtenir un statut independant dans la dashboard.

Les scans du pipeline portent sur les sources de l'application, ses dependances, les images construites, sa configuration d'infrastructure et l'API effectivement deployee. Le contrôleur `SecurityDemoController` contient des exemples de mauvaises pratiques et une valeur de credential explicitement factice, non utilisable et jamais renvoyée par l'API, afin de vérifier leur détection par SonarQube; le contrôleur reste désactivé hors mode démo. Aucun jeu de findings attendu ni résultat de scanner simulé n'est injecté dans les rapports : les résultats affichés proviennent des outils exécutés. Une ligne n'est marquée exécutée que si le stage correspondant enregistre son résultat; un contrôle non lancé reste « Non exécuté ». Un rapport sans finding signifie uniquement que le scanner n'a pas rapporté de finding dans son périmètre et son exécution; il ne garantit pas l'absence absolue de vulnérabilité.

Apres chaque execution Jenkins, le pipeline genere le tableau de suivi consolide `reports/devsecops-report.html` et sa feuille de style externe `reports/devsecops-report.css`, les publie avec le plugin **HTML Publisher** et archive tous les fichiers sous `reports/`. Depuis la page **Dashboard DevSecOps**, chaque lien ouvre l'artefact de ce build dans le meme onglet avec un chemin relatif au dossier publie (`../artifact/...`); les liens utilisent ainsi automatiquement le meme hote et le meme contexte Jenkins que le navigateur, au lieu de supposer `localhost` ou de dependre de l'ouverture d'un nouvel onglet. Les sorties restent natives (JSON/log/XML et HTML ZAP). Gitleaks fournit un compte-rendu texte sans contenu sensible; les smoke tests et le test de reprise archivent aussi leurs sorties. Les etapes sans fichier detaille n'affichent un lien que si un artefact reel existe. Sur petit ecran, le tableau masque les colonnes secondaires et conserve des boutons de rapport facilement activables. La feuille CSS externe de la dashboard respecte la politique CSP par defaut de Jenkins sans la desactiver. Dans Jenkins, ouvre le job `devops-catalog`, puis le lien **Dashboard DevSecOps** dans le menu du job ou du build. Chaque rapport est conserve avec son build; les artefacts bruts restent accessibles dans **Artifacts**. `JENKINS_PUBLIC_URL` renseigne toujours l'URL publique de build dans les resultats JSON; la navigation depuis la dashboard reste relative pour fonctionner quel que soit l'hote utilisé dans le navigateur.
Le menu permet de naviguer entre la synthese, les cinq phases du cours (Pre-commit, Commit/CI, Acceptation, Production, Operations), les findings, le plan d'action et le perimetre. Pour chaque outil, les lignes affichent son objectif, le résumé du résultat, la commande, les métriques/finding extraits du rapport et les liens vers les artefacts. Les stages sans résultat indiquent que leur diagnostic doit être recherché dans le premier stage en échec; ils ne sont pas présentés comme des réussites. Les rapports Trivy incluent aussi le journal de scan afin d'expliquer les échecs avant production de JSON. La dashboard respecte la politique CSP stricte de Jenkins : styles en fichier externe et aucun script integre. Seuls les contrôles automatisés configurés dans le laboratoire sont catalogués.
Les findings sont lus dans les rapports SonarQube, Trivy IaC/images et ZAP, tous produits à partir des sources, dépendances, configuration et services réels du projet. Le scan d'image Trivy est aussi la source SCA des composants embarqués. Le plan d'action est généré uniquement à partir des constats de cette exécution. Les alertes ZAP de niveau WARN restent visibles sans interrompre le pipeline grâce à l'option `-I`; Trivy image archive les niveaux LOW à CRITICAL, tandis que son seuil bloquant reste HIGH/CRITICAL corrigible. Pour la base de vulnérabilités, Trivy utilise ses registres officiels de secours par défaut (`mirror.gcr.io/aquasec`, puis GHCR) et dispose d'un délai de 30 minutes pour les scans d'images, afin qu'un téléchargement initial lent ne soit pas confondu avec un scan propre. Trivy Config archive les findings IaC sans bloquer le pipeline afin de rendre visibles les écarts de configuration effectivement analysés, notamment le contexte Jenkins local privilégié. Un rapport de scan terminé sans findings ne prouve pas l'absence de toute vulnérabilité.

Le statut « Réussi » confirme que le contrôle s'est terminé avec succès; pour les scanners, il ne signifie pas qu'aucune vulnérabilité n'a été trouvée. Les findings et leurs sévérités sont comptabilisés séparément. Avant de publier le HTML, le générateur vérifie qu'un résultat réussi dispose de preuves présentes, non vides et valides (notamment JSON/XML); sans preuve, son statut devient « Bloqué ». Chaque build Jenkins commence par initialiser un jeu de résultats vierge. Une génération locale sans nouveau numéro de build ne réutilise pas les statuts ni les liens d'un ancien build Jenkins : ils sont ramenés à « Non exécuté ».

Les contrôles locaux automatisables sont vérifiés dans Jenkins : SonarQube, Trivy SCA des images/IaC, configuration Compose, healthchecks/runtime, headers de sécurité, redémarrage contrôlé et disponibilité Prometheus/Grafana. Le contrôle de redémarrage est un test local limité, pas une campagne complète de chaos engineering.

Le compte admin Jenkins est synchronise au demarrage avec `JENKINS_ADMIN_ID` et `JENKINS_ADMIN_PASSWORD` du fichier `.env`. Si tu modifies ces valeurs, reconstruis/redemarre Jenkins pour appliquer le mot de passe configure. Le jeton `sonar-token` reste un credential Jenkins distinct et doit etre valide dans **Manage Jenkins > Credentials**.

Le rapport peut aussi etre regenere depuis la racine du projet dans Ubuntu/WSL :

```bash
mkdir -p reports
mvn -f backend/pom.xml -B clean verify
cp backend/target/surefire-reports/TEST-com.example.devops.ProductControllerTest.xml \
  reports/maven-tests.xml
python3 devsecops_report.py init --project-root . --results reports/devsecops-results.json
python3 devsecops_report.py record --id maven-tests --status passed \
  --summary "Tests Maven terminés" --command "mvn -f backend/pom.xml -B clean verify" \
  --artifact reports/maven-tests.xml --results reports/devsecops-results.json
python3 devsecops_report.py generate --results reports/devsecops-results.json \
  --output reports/devsecops-report.html
```

`record` accepte `passed`, `failed`, `blocked`, `skipped`, `manual` et `not_run`. Un résultat « Réussi » doit être associé à au moins un artefact réel déjà créé; les rapports manquants, vides ou illisibles empêchent la publication de ce statut. En usage normal, Jenkins initialise les résultats à chaque build, renseigne les statuts lui-même et produit le HTML à la fin du build, même si une étape de sécurité échoue.

Les tests du generateur HTML utilisent la bibliotheque standard Python :

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

Dans **Manage Jenkins > Credentials**, ajouter seulement les secrets dont tu as besoin :

- `sonar-token` (Secret text) : jeton utilisateur cree dans SonarQube ; cocher `RUN_SONAR` dans le pipeline ;
- `nexus-credentials` (Username with password) : compte administrateur Nexus utilise par ce pipeline pour configurer le depot hosted `maven-releases` et les droits de publication ; cocher `PUBLISH_NEXUS`. Cette configuration est reservee au laboratoire local ; pour un serveur partage, creer un compte de service dedie et adapter le compte cible dans le `Jenkinsfile` ;
- `dockerhub-credentials` (Username with password) : compte Docker Hub ; le depot prive `ykhirallah/devops-catalog` est cree. Pour une publication reelle, renseigner `DOCKERHUB_REPOSITORY` (valeur pre-remplie), cocher `PUBLISH_DOCKER`, configurer ce credential et desactiver `ENABLE_SECURITY_DEMO`. Les deux images sont publiees dans ce depot sous les tags `backend-<numero-build>` et `frontend-<numero-build>`.
- Email : dans **Manage Jenkins > System > Extended E-mail Notification**, configurer `smtp.gmail.com`, port `587`, TLS, l'adresse Gmail comme nom d'utilisateur et un mot de passe d'application Google (jamais le mot de passe normal du compte). Dans **Build with Parameters**, renseigner `EMAIL_TO` avec l'adresse destinataire; l'etape finale envoie la confirmation apres le deploiement et les tests HTTP. Ne mets jamais le mot de passe SMTP dans le Jenkinsfile ni dans le depot.

Le depot Nexus local `maven-releases` et l'identifiant Jenkins `nexus-credentials` sont provisionnes pour ce laboratoire. `PUBLISH_NEXUS` est active par defaut; l'etape configure le depot en mode `ALLOW` pour autoriser les republications des versions de developpement. SonarQube s'execute par defaut avec le secret Jenkins `sonar-token`; Docker Hub reste opt-in car il publie des images sur un compte externe. L'envoi d'email est saute si `EMAIL_TO` est vide. L'acces au socket Docker donne au pipeline des privileges proches de root : reserve cette configuration au laboratoire local, jamais a un Jenkins expose a des utilisateurs non fiables.

Trivy telecharge ses bases de vulnerabilites au premier scan; prevois un acces reseau, plusieurs Go de stockage et du temps supplementaire pour ce premier lancement. Son cache est conserve dans le volume Jenkins. Le pipeline ignore les vulnerabilites sans correctif connu. Les rapports Trivy incluent LOW, MEDIUM, HIGH et CRITICAL; seuls les constats HIGH/CRITICAL font passer le build a UNSTABLE, sans etre presentes comme une erreur d'execution du scanner.

OWASP ZAP Baseline (image Docker epinglee en `2.17.0`) execute un spider et l'analyse passive de l'endpoint de demonstration, sans lancer les tests actifs destructifs. `-I` laisse passer les alertes de niveau `WARN` tout en conservant les resultats dans les rapports; une erreur d'execution ou une regle `FAIL` fait echouer l'etape. `-z "-silent"` desactive la mise a jour et l'installation d'add-ons au lancement : le scan utilise les regles deja presentes dans l'image epinglee, ce qui evite une dependance reseau et rend les builds reproductibles. Pour mettre a jour les regles, actualiser volontairement la version de l'image ZAP. Le scan requiert un acces reseau a GitHub Container Registry (GHCR) au premier telechargement de l'image. Les rapports HTML et JSON sont consultables dans les artefacts du build Jenkins.

## Git local

Si ce dossier n'est pas encore un depot Git, initialise-le avant d'installer les hooks :

```bash
git init -b main
```

### PRE-COMMIT : controles automatiques

`pre-commit` verifie les espaces de fin de ligne, les fins de fichier, la syntaxe YAML, les conflits de fusion, les cles privees, les secrets detectables par Gitleaks et les fichiers de plus de 1 Mo avant chaque commit.

### COMMIT : messages Conventional Commits

Commitizen fournit `cz commit` pour creer interactivement un message normalise; son hook `commit-msg` refuse les messages non conformes, y compris ceux saisis avec `git commit`.

### Installer les outils

Dans Ubuntu/WSL, installe les outils isoles avec `pipx`, puis active les hooks dans le depot :

```bash
sudo apt-get install -y pipx
pipx ensurepath
pipx install pre-commit
pipx install commitizen
pre-commit install --install-hooks
```

Apres `pipx ensurepath`, ouvre un nouveau terminal si les commandes ne sont pas encore dans le `PATH`. La configuration [.pre-commit-config.yaml](./.pre-commit-config.yaml) lance les controles de fichiers avant chaque commit et valide le message au format Conventional Commits avec Commitizen. Les environnements de hooks sont installes automatiquement par pre-commit.

Les types de messages acceptes comprennent `feat`, `fix`, `docs`, `test`, `build`, `ci`, `refactor` et `chore`. Exemple :

```bash
git add .
cz commit
# ou, sans assistant interactif :
git commit -m "feat(backend): add product search"
```

Pour lancer les controles manuellement :

```bash
pre-commit run --all-files
```

Le pipeline Jenkins les execute egalement. Lorsque Jenkins recupere le depot Git (mode SCM), il verifie aussi le message du commit. En mode local, le dossier est copie sans l'historique Git : les controles de fichiers s'executent quand meme, mais la validation du message est faite par le hook local au moment du commit.

```bash
git add .
git commit -m "feat: create DevOps product catalog platform"
git remote add origin <url-du-depot>
git push -u origin main
```

Le fichier `.env`, les sorties Maven et les donnees d'execution ne sont pas versionnes.
