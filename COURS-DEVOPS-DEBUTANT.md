# Cours professionnel DevOps

## Du code source a l'exploitation d'une application

**Support de formation accompagne du projet DevOps Catalog**

Ce cours explique le fonctionnement du projet dans son ensemble et la maniere dont ses composants s'articulent. Il suit le cycle de vie d'un changement logiciel : developpement, integration, verification, analyse de qualite, stockage de l'artefact, construction d'images, deploiement et observation.

Le support est destine a une premiere formation DevOps. Il explique les notions au moment ou elles apparaissent dans le projet, donne les commandes utiles et decrit ce qu'il faut observer.

---

## 1. Perimetre et objectifs de la formation

Le laboratoire met en oeuvre une petite application de catalogue de produits et les services necessaires pour illustrer une chaine de livraison logicielle :

- **Java 17 et Spring Boot** pour l'API ;
- **Maven** pour les dependances, la compilation, les tests et le paquet JAR ;
- **MySQL** pour la persistance des produits en execution ;
- **HTML, CSS et JavaScript servis par Nginx** pour l'interface ;
- **Docker et Docker Compose** pour construire et orchestrer les conteneurs ;
- **Jenkins** pour decrire et executer le pipeline ;
- **SonarQube** pour analyser le code source ;
- **Nexus Repository** pour heberger l'artefact Maven ;
- **Prometheus et Grafana** pour collecter et consulter des metriques.

Au terme de la lecture, un etudiant doit pouvoir expliquer :

1. ce qui se passe entre la modification du code et son execution ;
2. la responsabilite de chaque outil, sans les confondre ;
3. l'ordre des controles et publications dans Jenkins ;
4. la difference entre source, artefact, image et conteneur ;
5. comment verifier l'etat du systeme et localiser un echec ;
6. pourquoi les secrets et les donnees persistantes doivent etre proteges.

Le systeme est un **laboratoire local**, pas une plateforme de production. Certains choix privilegient la pedagogie et la simplicite; les limites de securite et de disponibilite sont precisees dans les chapitres correspondants.

## 2. Les principes DevOps mobilises

**DevOps** designe une pratique d'organisation et d'ingenierie qui rapproche le developpement et l'exploitation. Les equipes cherchent a livrer plus rapidement tout en obtenant des retours frequents et en maitrisant les risques. Les outils automatisent une partie du travail, mais ne remplacent ni la collaboration, ni les revues, ni la responsabilite des equipes.

### 2.1 Integration continue

L'integration continue, ou **CI (Continuous Integration)**, consiste a integrer frequemment les changements et a executer automatiquement des verifications communes. Dans ce projet, Maven compile l'application, les tests valident certains comportements, et SonarQube analyse le code.

L'objectif est de decouvrir un probleme tot, lorsque le changement est encore facile a examiner, plutot que de le decouvrir apres un deploiement.

### 2.2 Livraison et deploiement

La **livraison continue (Continuous Delivery)** consiste a maintenir une version verifiee et deployable. Un artefact reproductible, des images identifiees et des etapes automatisees contribuent a cet objectif.

Le **deploiement continu (Continuous Deployment)** va plus loin : chaque changement qui satisfait les controles peut etre mis en production automatiquement. Le laboratoire deploie dans l'environnement Docker local; cela illustre l'automatisation, mais ne signifie pas qu'il constitue une procedure de mise en production securisee.

### 2.3 Pipeline et retour rapide

Un **pipeline** est une sequence de traitements qui transforme une revision de code en un resultat verifie. Un build a un statut global et chaque etape a son propre resultat. Une etape en echec doit empecher les etapes dependantes de publier ou de deployer un resultat invalide.

Dans Jenkins, le **Console Output** fournit les details techniques. La **vue des stages** montre l'ordre et l'etat des etapes. Une etape ignoree n'est pas necessairement en erreur : une condition ou un parametre peut l'avoir desactivee.

## 3. Vue d'ensemble de l'architecture

```text
Code du projet
     |
     | dossier local monte (configuration actuelle)
     | ou depot Git distant (configuration possible)
     v
Jenkins : pipeline declaratif
     |
     +--> Maven : compilation, tests, JAR
     +--> SonarQube : analyse statique du code
     +--> Nexus : publication du JAR Maven
     +--> Docker Compose : images puis deploiement local
                                      |
                                      +--> Frontend Nginx
                                      +--> API Spring Boot
                                      +--> MySQL
                                               |
                                               +--> endpoint de metriques
                                                        |
                                                        v
                                                  Prometheus
                                                        |
                                                        v
                                                     Grafana
```

### 3.1 Les services et leurs interfaces

| Service | Adresse depuis le navigateur | Fonction |
|---|---|---|
| Frontend catalogue | `http://localhost:8081` | Formulaire et affichage du catalogue |
| Backend / API | `http://localhost:8080` | API REST, acces aux donnees et metriques |
| Jenkins | `http://localhost:8083` | Execution et suivi du pipeline |
| SonarQube | `http://localhost:9000` | Resultats de l'analyse de code |
| Nexus Repository | `http://localhost:8082` | Navigation dans les artefacts publies |
| Prometheus | `http://localhost:9090` | Etat de collecte et requetes de metriques |
| Grafana | `http://localhost:3000` | Consultation des donnees Prometheus |

Ces adresses sont publiees sur l'ordinateur hote. Les conteneurs communiquent entre eux au moyen du reseau Compose, en utilisant les noms de service et les ports internes, par exemple `backend:8080`, `mysql:3306`, `sonarqube:9000` et `nexus:8081`. Dans un conteneur, `localhost` designe ce conteneur lui-meme, pas les autres conteneurs.

### 3.2 Parcours d'une requete applicative

Le navigateur charge la page statique depuis Nginx. Le code JavaScript appelle l'API sous le chemin relatif `/api`. Nginx transmet ces requetes a `backend:8080` sur le reseau Compose. Spring Boot valide et traite la demande; le depot JDBC execute les requetes sur MySQL. La reponse JSON revient par le backend puis le proxy Nginx au navigateur.

Ce proxy conserve une origine de navigateur unique pour l'interface et l'API. Le controle CORS de l'API autorise aussi explicitement les origines locales prevues par l'application.

## 4. Organisation du projet et responsabilites des fichiers

Les principaux elements sont :

| Chemin | Responsabilite |
|---|---|
| `Jenkinsfile` | Etapes, parametres, credentials et orchestration CI/CD |
| `docker-compose.yml` | Services, reseaux, ports, volumes, profils et dependances |
| `setup.sh` | Verification puis demarrage de Compose |
| `.env.example` | Modele de variables locales sans secrets personnels |
| `.env` | Configuration locale; ne doit pas etre versionnee |
| `backend/pom.xml` | Projet Maven, dependances, plugins et distribution Maven |
| `backend/Dockerfile` | Construction multi-etapes de l'image de l'API |
| `backend/src/main/java/...` | Code Java de l'API et de l'acces aux donnees |
| `backend/src/main/resources/application.properties` | Port, Actuator et configuration Spring |
| `backend/src/test/...` | Tests automatises du comportement HTTP |
| `frontend/index.html` | Interface HTML, styles et logique JavaScript du catalogue |
| `frontend/nginx.conf` | Service de la page et proxy `/api` vers le backend |
| `frontend/Dockerfile` | Image Nginx qui embarque les fichiers frontend |
| `jenkins/Dockerfile` | Image Jenkins personnalisee et plugins du pipeline |
| `jenkins/init.groovy.d/zz-pipeline.groovy` | Creation et mise a jour du job local Jenkins |
| `monitoring/prometheus/prometheus.yml` | Cible et intervalle de collecte Prometheus |
| `monitoring/grafana/provisioning/...` | Source Prometheus preconfiguree dans Grafana |
| `README.md` | Instructions d'installation et reference rapide du projet |

Le dossier `backend/target/` contient des sorties de build et non du code source. Les fichiers `.env` et `target/` sont exclus par le `.gitignore` local.

## 5. Demarrage du laboratoire sous Ubuntu / WSL

Le projet est situe sur le lecteur Windows `D:` et accessible depuis Ubuntu WSL sous `/mnt/d`. Depuis l'application Ubuntu, place-toi a la racine :

```bash
cd "/mnt/d/5NIDS/Labs Cybersecurity and Coding/DevOps_Project/devops-platform"
```

Docker Engine et Compose v2 doivent etre utilisables dans la distribution. Verifie-les :

```bash
docker version
docker compose version
```

Si le service Docker de cette distribution WSL n'est pas demarre :

```bash
sudo service docker start
```

SonarQube requiert une valeur noyau `vm.max_map_count` suffisante. La commande appliquee au laboratoire est :

```bash
sudo sysctl -w vm.max_map_count=262144
```

La commande `sysctl` modifie le parametre de la session courante; apres un arret complet de WSL il peut falloir le reconfigurer ou le rendre persistant dans la distribution.

### 5.1 Configuration locale

Au premier lancement, `setup.sh` copie `.env.example` vers `.env` si `.env` n'existe pas et applique des permissions restrictives. Les variables alimentent le nom du projet Compose, MySQL, PostgreSQL de SonarQube, Jenkins et Grafana.

Les valeurs de demonstration ne sont pas adaptees a une machine partagee ou exposee. En particulier :

- remplace les mots de passe de demonstration avant tout usage hors du poste local ;
- ne communique pas le contenu de `.env` ;
- ne versionne jamais `.env` ;
- ne place pas de jeton SonarQube, mot de passe Nexus, SMTP ou Docker Hub dans un script versionne.

Les credentials utilises par un job Jenkins sont conserves dans le magasin **Manage Jenkins > Credentials**. La substitution d'une valeur par un masque dans les logs ne remplace pas la prevention de l'exposition du secret.

### 5.2 Demarrer tous les profils

Depuis la racine du projet :

```bash
bash ./setup.sh --all
```

Le script :

1. verifie que Docker et Compose existent ;
2. prepare `.env` uniquement s'il est absent ;
3. valide la configuration resolue avec `docker compose config --quiet` ;
4. execute `docker compose up -d --build --wait` pour les profils selectionnes ;
5. affiche les URLs locales a utiliser.

Trois modes sont disponibles : sans option pour l'application et MySQL, `--tools` pour ajouter Jenkins/SonarQube/Nexus, `--monitoring` pour ajouter Prometheus/Grafana, `--all` pour le laboratoire complet.

Le profil complet est gourmand en ressources. Il faut prevoir plusieurs gigaoctets de RAM pour les services et davantage si Jenkins construit des images pendant que SonarQube analyse le code.

## 6. L'application : interface, API et donnees

### 6.1 Interface Nginx

Le frontend est une page statique (`frontend/index.html`) avec HTML, CSS et JavaScript. Il ne s'agit pas d'un projet Node/React : il n'y a ni compilation JavaScript ni gestionnaire de paquets frontend dans ce laboratoire.

La page :

- charge la liste avec `GET /api/products` ;
- verifie l'API avec `GET /api/health` ;
- cree un produit avec `POST /api/products` ;
- modifie un produit avec `PUT /api/products/{id}` ;
- supprime un produit avec `DELETE /api/products/{id}` ;
- affiche les erreurs renvoyees par l'API.

Le fichier `frontend/nginx.conf` configure Nginx pour livrer la page et retransmettre les chemins `/api/` au service Compose `backend:8080`. Le Dockerfile frontend part de Nginx Alpine et copie la page ainsi que cette configuration.

### 6.2 Organisation du backend

Le backend est une application Spring Boot Java 17. Les responsabilites sont separees en couches :

1. **`ProductController`** expose les routes REST de `/api/products`, traduit les requetes HTTP et choisit les codes de reponse ;
2. **`ProductRequest`** definit la forme des donnees entrantes et les contraintes de validation ;
3. **`ProductService`** porte la logique applicative et transforme les absences en erreurs metier ;
4. **`ProductRepository`** execute les operations SQL via `JdbcTemplate` ;
5. **`Product`** represente les donnees retournees ;
6. **`ApiExceptionHandler`** transforme les erreurs metier et de validation en reponses HTTP structurees ;
7. **`ApiController`** fournit `/api/health`.

Cette separation rend plus lisible la distinction entre HTTP, regles applicatives et stockage. Le projet utilise le JDBC explicite et non un ORM comme JPA. Les parametres de requetes `?` evitent de concatener des valeurs utilisateurs dans le SQL. Lors de la creation, un `KeyHolder` recupere l'identifiant genere par la base.

### 6.3 Contrat REST et validation

L'API CRUD utilise les methodes HTTP usuelles :

| Methode | Route | Resultat nominal |
|---|---|---|
| `GET` | `/api/products` | Liste JSON, statut `200` |
| `GET` | `/api/products/{id}` | Produit JSON, ou `404` |
| `POST` | `/api/products` | Produit cree, statut `201` et en-tete `Location` |
| `PUT` | `/api/products/{id}` | Produit modifie, ou `404` |
| `DELETE` | `/api/products/{id}` | Suppression, statut `204`, ou `404` |

Les donnees d'entree sont validees : le nom ne peut pas etre vide et est limite a 120 caracteres; la description est limitee a 1000 caracteres; le prix doit etre strictement positif; le stock doit etre positif ou nul. Une requete invalide renvoie `400 Bad Request`. Un identifiant absent renvoie `404 Not Found`.

### 6.4 Base de donnees et configuration runtime

MySQL est un service distinct. Compose fournit au backend les variables de connexion avec `SPRING_DATASOURCE_URL`, le nom de service `mysql`, et les identifiants issus de l'environnement local. Le fichier `backend/src/main/resources/schema.sql` cree la table `products` : un identifiant auto-incremente, un nom et une description, un prix `DECIMAL(10,2)` et un stock entier. La configuration Spring execute l'initialisation SQL au demarrage. Les tests activent le profil `test` et utilisent H2 en memoire.

Pour interroger l'API exposee sur le poste :

```bash
curl --fail http://localhost:8080/api/health
curl --fail http://localhost:8080/api/products
```

Ces tests de base confirment que les routes repondent. Ils ne remplacent pas les tests fonctionnels complets, les controles de securite ou les essais de charge.

## 7. Conteneurs, images et orchestration

### 7.1 Vocabulaire Docker

- Une **image** est un modele construit a partir d'un Dockerfile.
- Un **conteneur** est un processus lance a partir d'une image.
- Un **volume nomme** conserve des donnees en dehors du conteneur.
- Un **port publie** relie un port de l'hote a un port du conteneur.
- Un **health check** execute periodiquement une verification de disponibilite.
- Un **reseau Compose** permet aux services de communiquer par noms de services.

Reconstruire une image et redemarrer un conteneur ne sont pas la meme operation. Un conteneur peut etre remplace tout en conservant les donnees dans un volume.

### 7.2 Construction multi-etapes du backend

`backend/Dockerfile` contient deux etapes. La premiere utilise l'image Maven avec Java 17 pour produire le JAR. La seconde utilise uniquement un runtime Java 17, installe `curl` pour les controles de sante, copie le JAR, puis execute l'application avec un utilisateur non-root `app` (UID 10001).

Cette construction dite **multi-stage** evite d'inclure le compilateur et Maven dans l'image finale. L'image d'execution est plus simple et la JVM n'est pas lancee en tant que root. Le port applicatif est 8080.

Le Dockerfile frontend utilise l'image Nginx et copie la page statique et la configuration du proxy. Jenkins demande a Compose de construire backend et frontend; Compose utilise les Dockerfiles associes aux contextes de build.

### 7.3 Lecture de `docker-compose.yml`

Le fichier Compose declare les services et leurs relations :

- **mysql** : base applicative avec volume `mysql-data` et controle `mysqladmin ping` ;
- **backend** : API Spring Boot, construit depuis `./backend`, publie le port 8080 et attend MySQL sain ;
- **frontend** : Nginx, construit depuis `./frontend`, publie le port 8081 et attend le backend sain ;
- **sonarqube-db** : PostgreSQL persistant utilise par SonarQube ;
- **sonarqube** : plateforme d'analyse, depend de PostgreSQL et expose le port 9000 ;
- **nexus** : depot d'artefacts, expose le port 8082 et conserve ses donnees dans `nexus-data` ;
- **jenkins** : serveur et agent d'orchestration du labo, expose 8083 et le port d'agent 50000, monte le socket Docker et le dossier projet en lecture seule ;
- **prometheus** et **grafana** : services de supervision disponibles via le profil `monitoring`.

Les services `sonarqube`, `nexus`, `jenkins` et `sonarqube-db` appartiennent au profil Compose `devops`. Prometheus et Grafana appartiennent au profil `monitoring`. Les volumes sont nommes : `mysql-data`, `sonarqube-db`, `sonarqube-data`, `sonarqube-extensions`, `sonarqube-logs`, `nexus-data`, `jenkins-home`, `prometheus-data` et `grafana-data`.

### 7.4 Exploitation courante des services

Depuis la racine :

```bash
docker compose --profile devops --profile monitoring ps
docker compose logs --tail=100 backend
docker compose logs --follow jenkins
docker compose images
```

Pour demander a Compose de demarrer ou de reconcilier les services sans reconstruire :

```bash
docker compose --profile devops --profile monitoring up --detach --wait
```

Pour arreter le laboratoire avec le script du projet :

```bash
bash ./down.sh
```

Un arret normal ne doit pas supprimer les volumes. La commande `docker compose down -v` supprime les volumes et donc les donnees persistantes de la base, des outils et de leur configuration. Elle n'est pas une commande de redemarrage.

## 8. Maven : dependances, cycle de vie et artefact

### 8.1 Le role du POM

`backend/pom.xml` identifie l'artefact sous les coordonnees Maven :

```text
groupId    : com.example
artifactId : devops-backend
version    : 1.0.0
```

Ces trois valeurs forment les coordonnees `com.example:devops-backend:1.0.0`. Le POM herite du parent Spring Boot 3.4.1, cible Java 17, declare les dependances Web, Actuator, Validation, JDBC et MySQL, et les dependances de test. Il configure JaCoCo pour produire un rapport de couverture et indique dans `distributionManagement` le depot Nexus `nexus-releases`.

### 8.2 Phases Maven utilisees

Maven execute un cycle de vie ordonne. Une phase demande l'execution des phases precedentes necessaires.

- `clean` supprime les anciens resultats du dossier `target` ;
- `test` compile le code et execute les tests unitaires ;
- `package` produit le JAR ;
- `verify` va jusqu'aux controles du cycle de verification ;
- `deploy` execute les phases precedentes, puis transfere l'artefact au depot distant declare.

La commande de validation locale est :

```bash
cd backend
mvn -B clean verify
```

`-B` active le mode non interactif, utile dans les logs CI. Le JAR est produit dans `backend/target/`. Les rapports Surefire sont sous `backend/target/surefire-reports/`, et le rapport HTML JaCoCo se trouve sous `backend/target/site/jacoco/`.

### 8.3 Tests

Les tests `ProductControllerTest` demarrent le contexte Spring avec MockMvc et le profil `test`. Ils couvrent le cycle CRUD et quelques cas d'erreur de validation et d'identifiant inexistant. H2 en memoire evite de dependre d'un serveur MySQL pour les tests unitaires et d'integration du controleur.

Les tests automatises ne prouvent pas qu'il n'existe aucun defaut. Ils verifient les comportements explicitement couverts et fournissent une protection lors des changements.

## 9. Git et source de verite

Git suit l'historique des changements dans un depot. Dans une equipe, les changements sont generalement isoles sur une branche, examines puis integres. Un tag ou un commit identifie une version source precise.

**Configuration actuelle du laboratoire :** le conteneur Jenkins monte le repertoire du projet comme `/workspace` en lecture seule et `USE_LOCAL_SOURCE` est actif par defaut. Le job local copie ce repertoire dans son espace de travail. L'execution du pipeline peut donc fonctionner sans depot Git distant.

Le job peut etre configure pour un depot distant dans Jenkins avec une definition **Pipeline script from SCM** et le chemin `Jenkinsfile`. Dans ce cas, il faut desactiver `USE_LOCAL_SOURCE` pour que le pipeline fasse `checkout scm`. Un depot Git correctement configure est necessaire avant d'utiliser cette variante.

Les fichiers `.env` et `backend/target/` sont exclus par `.gitignore`. Avant publication du depot, les fichiers de configuration ne doivent pas contenir de credential ou secret reel. Une suppression d'un secret dans un commit recent ne l'efface pas automatiquement de l'historique Git; il faut alors le revoquer et traiter l'historique.

## 10. Jenkins : execution du pipeline

### 10.1 Serveur, job et agent

Jenkins est le serveur d'automatisation. Un **job** est une definition de travail, ici `devops-catalog`. Le **Jenkinsfile** est un pipeline declaratif versionnable. Un **agent** fournit l'environnement ou s'executent les commandes; dans ce laboratoire, le conteneur Jenkins inclut Java, Maven, Docker CLI, Compose et curl.

Le Dockerfile Jenkins installe egalement des plugins pour les pipelines, Git, Sonar, credentials, horodatages, rapports JUnit, vue par etapes et e-mail. Le repertoire `jenkins/init.groovy.d/` contient le script d'initialisation du job.

Le script d'initialisation lit `/workspace/Jenkinsfile`, cree ou met a jour le job local `devops-catalog`, puis programme un premier build s'il n'y a encore aucun build reussi. Le code source du Jenkinsfile est donc celui du dossier monte.

### 10.2 Parametres du pipeline

Le pipeline declare les parametres suivants :

| Parametre | Comportement |
|---|---|
| `USE_LOCAL_SOURCE` | Copie le projet monte; si desactive, execute `checkout scm` |
| `RUN_SONAR` | Active l'analyse SonarQube |
| `PUBLISH_NEXUS` | Active la publication Maven dans Nexus |
| `PUBLISH_DOCKER` | Demande la publication des images sur Docker Hub |
| `DOCKERHUB_REPOSITORY` | Nom du depot Docker cible, sous la forme `compte/projet` |
| `EMAIL_TO` | Destinataire de la notification finale si SMTP est configure |

Les parametres Sonar et Nexus sont actifs par defaut dans le Jenkinsfile actuel. La publication Docker externe est desactivee par defaut. Une etape conditionnelle grisee dans Jenkins signifie qu'elle n'a pas ete executee, typiquement parce que son parametre etait desactive ou son adresse e-mail vide.

### 10.3 Lecture detaillee des stages

1. **Declarative: Tool Install** : verifie Java, Maven, Docker Compose et curl afin d'echouer rapidement si l'agent n'a pas les outils attendus.
2. **Getting Project from Git** : si `USE_LOCAL_SOURCE` est actif, nettoie le workspace et copie le contenu de `/workspace` en excluant `.env`, `.git` et `backend/target`; sinon, Jenkins utilise `checkout scm`.
3. **Cleaning the project** : lance `mvn -B clean` dans `backend`.
4. **Artifact construction** : lance `mvn -B -DskipTests package`. Cette etape prepare le JAR; les tests sont executees dans le stage suivant, de sorte que les resultats de test restent visibles separement.
5. **Unit Tests** : execute `mvn -B test jacoco:report`; le bloc `post always` publie les fichiers JUnit et archive le JAR ainsi que le rapport de couverture.
6. **Code Quality Check via SonarQube** : si `RUN_SONAR` est actif, Jenkins injecte `sonar-token` comme secret temporaire, puis appelle le plugin Maven Sonar avec les coordonnees explicites de son plugin et la cle `devops-catalog`.
7. **Publish to Nexus** : si `PUBLISH_NEXUS` est actif, Jenkins injecte `nexus-credentials`, prepare temporairement les parametres Maven, configure le role/depot necessaire et execute `mvn deploy`. Les fichiers de configuration Maven locaux sont supprimes par un `trap` a la fin du script, meme si la commande echoue.
8. **Building our image** : Compose construit les images backend et frontend. Si `PUBLISH_DOCKER` est actif, le pipeline exige un nom de depot et la credential `dockerhub-credentials`, se connecte via `--password-stdin`, tague et publie les deux images, puis se deconnecte.
9. **Deploy our image** : Compose demarre ou met a jour MySQL, backend et frontend, attend leur disponibilite, puis lance les requetes HTTP de verification sur l'API.
10. **Email verification** : ne s'execute que si `EMAIL_TO` est renseigne. Le plugin envoie un message apres le deploiement reussi; il faut aussi une configuration SMTP valide dans Jenkins.

Le pipeline utilise `disableConcurrentBuilds()` pour eviter deux builds simultanes qui manipuleraient le meme environnement local. Les horodatages facilitent le rapprochement des commandes avec les journaux des services.

### 10.4 Examiner un build

Dans `http://localhost:8083`, ouvrir **devops-catalog**, puis **Full Stage View** pour l'ordre des stages. Depuis un build, **Console Output** donne les commandes et sorties; le lien de rapport JUnit presente les tests; les artefacts archives sont consultables depuis la page du build.

Pour diagnostiquer proprement :

1. identifier le premier stage rouge, pas seulement le dernier message du build ;
2. lire la premiere commande qui retourne un code non nul ;
3. distinguer une panne d'outil, un probleme de code, un probleme de secret, un refus de service ou un test d'acceptation en echec ;
4. examiner les journaux du conteneur concerne si l'erreur vient d'un service ;
5. corriger la cause, puis relancer et verifier les resultats de bout en bout.

Un resultat Jenkins `SUCCESS` indique que les etapes effectivement executees se sont terminees correctement. Il ne signifie pas qu'une etape optionnelle ignoree, telle que l'e-mail, a ete verifiee.

## 11. SonarQube : analyse statique

SonarQube analyse le code source et produit des indicateurs et des constats de qualite. Il peut signaler des defauts probables, des risques de maintenance et certains problemes de securite. Il ne lance pas l'application a la place des tests et ne prouve pas l'absence de vulnerabilites.

Le service SonarQube stocke son etat dans PostgreSQL. Pour executer l'analyse, Jenkins utilise l'adresse interne `http://sonarqube:9000`, le plugin Maven `org.sonarsource.scanner.maven:sonar-maven-plugin` et la cle de projet `devops-catalog`. L'adresse publique `localhost:9000` sert a consulter les resultats depuis le navigateur; elle n'est pas l'adresse utilisee entre conteneurs.

Le token est stocke dans Jenkins sous l'identifiant `sonar-token` de type **Secret text**. Il est injecte dans l'environnement de l'etape et ne doit pas etre ecrit en clair dans le POM, le Jenkinsfile, Git ou un rapport. Le resultat d'analyse s'affiche dans le tableau de bord du projet SonarQube.

Une analyse reussie signifie que le scanner a transmis les donnees et que le serveur les a acceptees. Le statut de quality gate et les constats du projet doivent etre consultes separement pour determiner si le niveau de qualite repond aux criteres de l'equipe.

## 12. Nexus : gestion des artefacts Maven

Un **artefact** est un resultat versionne et reutilisable de la construction, ici un fichier JAR et son POM Maven. Nexus Repository heberge ces artefacts afin que les autres builds puissent les retrouver sans reconstruire le code source.

### 12.1 Coordonnees et chemin du paquet

Le projet publie l'artefact :

```text
com.example:devops-backend:1.0.0
```

Dans le depot Maven hosted `maven-releases`, le chemin attendu est :

```text
com/example/devops-backend/1.0.0/devops-backend-1.0.0.jar
```

Le POM est egalement publie. La page **Browse** de Nexus permet d'explorer le depot; l'API de recherche Nexus peut confirmer l'existence de la version.

### 12.2 Authentification et publication

L'identifiant `nexus-credentials` de Jenkins est une credential **Username with password**. Le pipeline genere un fichier settings Maven temporaire qui associe le serveur Maven `nexus-releases` a cette credential. Le meme identifiant de serveur figure dans `distributionManagement` du POM : Maven s'en sert pour choisir les identifiants du transfert.

L'etape configure le role `jenkins-maven-releases-publisher`, les droits associes au depot et sa strategie `ALLOW`, puis execute `mvn deploy`. L'option `ALLOW` permet dans ce laboratoire de republier une version pendant les demonstrations; pour une politique de versions immuables, une configuration plus stricte est preferable.

### 12.3 Acceptation initiale et limites du laboratoire

Les versions recentes de Nexus Repository Community Edition peuvent imposer une acceptation de l'EULA avant d'autoriser les operations sur les depots. Cette acceptation est juridique et doit etre faite consciemment par la personne responsable, apres lecture des conditions; le pipeline ne doit pas accepter cette EULA automatiquement.

Pour simplifier le laboratoire, la credential utilisee pour configurer Nexus dispose de droits administratifs et le pipeline met a jour l'utilisateur admin. C'est un raccourci pedagogique local, pas un modele de moindre privilege. Un environnement d'equipe doit utiliser un compte de service dedie, des permissions strictement limitees au depot requis et une rotation geree des credentials.

Un `403 Forbidden` durant `mvn deploy` indique un refus du serveur; les causes possibles incluent l'EULA non acceptee, un mauvais compte, des privileges insuffisants ou une politique du depot. Il faut verifier la console Maven et les journaux Nexus au lieu de conclure uniquement a partir du code HTTP.

## 13. Livraison Docker et deploiement local

L'etape Docker est executee apres les tests et la publication Nexus. Compose construit les images de l'application a partir des Dockerfiles, puis l'etape de deploiement met a jour les conteneurs locaux. Le backend utilise MySQL par le reseau interne et le frontend communique avec l'API via son proxy Nginx.

Le pipeline attend le demarrage des services (`up --detach --wait`) et effectue ensuite deux controles :

- `/api/health` confirme que la route de sante applicative repond ;
- `/api/products` confirme que l'API du catalogue peut servir une requete de lecture.

Ces tests HTTP sont des **smoke tests** : ils couvrent une petite surface apres deploiement afin de detecter rapidement une panne majeure. Ils ne remplacent pas une suite complete de tests de bout en bout ou un suivi continu.

La publication sur Docker Hub est une etape distincte et optionnelle. Elle est desactivee par defaut, car elle transfere des images vers un service externe et necessite un nom de depot et des credentials valides. Ne l'active que si la destination et le compte ont ete autorises.

## 14. Prometheus et Grafana : observabilite

L'observabilite aide les equipes a comprendre l'etat d'un systeme en fonctionnement. Le laboratoire illustre principalement les **metriques**. Dans un systeme complet, les metriques sont accompagnees de journaux et de traces distribuees.

### 14.1 Exposition des metriques

Spring Boot Actuator expose les endpoints de sante et Prometheus. `application.properties` ouvre les endpoints `health`, `info` et `prometheus`, et active l'export Prometheus. L'adresse interne du backend est :

```text
http://backend:8080/actuator/prometheus
```

### 14.2 Collecte Prometheus

`monitoring/prometheus/prometheus.yml` configure une collecte toutes les 15 secondes sur le chemin `/actuator/prometheus` de la cible `backend:8080`, sous le nom de job `devops-backend`.

Dans l'interface Prometheus (`http://localhost:9090`), la requete `up` permet de verifier si les cibles sont joignables; la valeur `1` indique une collecte reussie pour la cible correspondante. L'indicateur `up` ne garantit pas a lui seul que toutes les fonctions metier sont correctes.

### 14.3 Consultation Grafana

Le fichier de provisioning sous `monitoring/grafana/provisioning/datasources/prometheus.yml` configure automatiquement la source de donnees Grafana en visant `http://prometheus:9090`. L'adresse `prometheus` est resolue depuis le conteneur Grafana.

Grafana presente les metriques et peut servir a construire des panneaux et des alertes. Une source de donnees correctement provisionnee ne signifie pas qu'un tableau de bord metier complet est fourni : les panneaux doivent etre configures selon les besoins de supervision.

### 14.4 Sante, tests et supervision

- Un **test unitaire** verifie un comportement de code isole ou controle.
- Un **smoke test** verifie quelques fonctions apres deploiement.
- Un **health check** indique qu'un processus ou service satisfait un controle de disponibilite.
- Une **metrique** observe une mesure au cours du temps.

Ces mecanismes se completent. Un processus peut etre actif sans que l'application soit saine; une metrique peut montrer un service joignable sans confirmer l'exactitude d'une operation fonctionnelle.

## 15. Notifications par e-mail

Le stage `Email verification` est conditionne a un parametre `EMAIL_TO` non vide. Il utilise le plugin Email Extension. Pour qu'un message soit effectivement transmis, Jenkins doit aussi posseder une configuration SMTP fonctionnelle dans **Manage Jenkins > System > Extended E-mail Notification**.

Le cas Gmail demande generalement un serveur SMTP autorise, TLS sur le port 587 et un mot de passe d'application compatible avec les parametres du compte. Un mot de passe personnel normal ne doit pas etre utilise ni copie dans le Jenkinsfile. Il faut stocker les secrets selon les mecanismes Jenkins et verifier le resultat de livraison avec un destinataire autorise.

Si `EMAIL_TO` est vide, Jenkins ignore le stage. Un build reussi dans cette configuration ne constitue donc pas un test d'envoi de courriel.

## 16. Demarrage, arret et conservation des donnees

Les commandes principales s'executent depuis la racine du projet :

```bash
bash ./setup.sh --all
docker compose --profile devops --profile monitoring ps
bash ./down.sh
```

`setup.sh --all` valide les fichiers Compose et demarre les profils application, DevOps et monitoring. `docker compose ps` affiche les etats, ports et controles de sante. `down.sh` arrete les services selon le script du projet; les volumes nommes persistent normalement.

Ne pas utiliser `docker compose down -v` pour un arret ordinaire : `-v` supprime les volumes et les donnees qui y sont stockees. Avant toute operation de maintenance destructive, identifier precisement les volumes et etablir une sauvegarde si les donnees ont de la valeur.

## 17. Securite et ecarts par rapport a la production

Le laboratoire permet d'apprendre les integrations; plusieurs points doivent etre renforces pour un environnement partage ou public :

1. **Secrets** : les secrets locaux d'exemple doivent etre remplaces; les credentials doivent vivre dans un coffre ou le gestionnaire de credentials Jenkins et etre renouveles en cas d'exposition.
2. **Compte Nexus** : ne pas utiliser l'administrateur global pour les publications; creer un utilisateur technique aux droits minimaux.
3. **Docker socket** : le socket monte dans Jenkins permet des operations privilegiees sur le moteur Docker. Un utilisateur capable de modifier le pipeline peut potentiellement obtenir un controle tres eleve sur l'hote. Isoler les agents de build et ne pas exposer Jenkins a du code non fiable.
4. **Reseau et exposition** : les ports sont publies pour le developpement local. Ne pas exposer directement les interfaces sans TLS, authentification, pare-feu et durcissement adequats.
5. **Images** : certaines images sont referencees par des tags qui peuvent evoluer. Une pratique de production epingle les versions et, selon le contexte, leurs digests, et applique un processus de mise a jour controle.
6. **Artefacts** : une version fixe `1.0.0` et une politique `ALLOW` facilitent les demonstrations mais rendent les republications ambigues. En production, preferer des versions uniques/immutables et une politique de retention definie.
7. **Sauvegarde** : les volumes Docker ne sont pas une sauvegarde. Les donnees et configurations necessaires a la reprise doivent etre sauvegardees, testees et restaurees selon un plan.
8. **EULA** : l'acceptation doit etre prise par une personne habilitee apres lecture, jamais automatisee par un build CI.
9. **E-mail et journaux** : ne pas envoyer de secret dans les notifications; filtrer les donnees personnelles et appliquer des durees de conservation aux logs.
10. **Tests** : une pipeline verte n'est pas une certification de securite ou de disponibilite. Il faut definir des controles adaptes au risque et au niveau de service attendu.

## 18. Methode de diagnostic

Le diagnostic suit une progression du plus proche au plus large :

1. **Verifier le processus** : `docker compose --profile devops --profile monitoring ps`.
2. **Verifier le point d'entree utilisateur** : tester l'URL locale et relever le code HTTP.
3. **Lire les journaux du service concerne** : `docker compose logs --tail=100 <service>`.
4. **Verifier les dependances** : base saine, variables requises, service accessible par son nom Compose.
5. **Lire le premier echec du pipeline** : consulter Console Output et non seulement le message final.
6. **Classifier le probleme** : code, dependance, configuration, authentication, autorisation, reseau, capacite ou disponibilite.
7. **Corriger la cause puis revalider** : tests, pipeline complet et verification du resultat reel dans Nexus, SonarQube ou l'application.

Exemples de signaux :

| Signal | Interpretation initiale |
|---|---|
| `docker` ou Compose indisponible | Probleme d'environnement Docker/WSL |
| Backend en attente ou unhealthy | Examiner les logs backend et l'etat MySQL |
| Tests Maven rouges | Examiner le rapport Surefire et l'assertion qui echoue |
| Credential Jenkins absente | Verifier l'identifiant exact et le type du credential |
| Sonar `401`/`403` | Verifier token, permissions et configuration du serveur |
| Nexus `403` | Verifier EULA, identite, droits et politique du depot |
| `localhost` incorrect dans un conteneur | Utiliser le nom du service Compose pour la communication interne |
| Stage e-mail ignore | `EMAIL_TO` vide ou condition du stage non satisfaite |

Les commandes de base sont :

```bash
docker compose --profile devops --profile monitoring ps
docker compose logs --tail=100 <nom-du-service>
curl --fail http://localhost:8080/api/health
curl --fail http://localhost:8080/actuator/prometheus
```

## 19. Glossaire

| Terme | Sens dans ce projet |
|---|---|
| Agent Jenkins | Environnement qui execute les commandes du pipeline |
| Artefact | Paquet Maven publie, ici le JAR et son POM |
| Build | Execution du job Jenkins avec ses resultats |
| CI/CD | Integration continue et pratiques de livraison/deploiement |
| Conteneur | Processus isole lance depuis une image |
| Credential | Secret ou identifiant conserve par Jenkins |
| Image Docker | Modele construit pour executer un service |
| JAR | Archive Java executable ou reutilisable |
| Pipeline | Sequence automatisee de verification et de livraison |
| Profil Compose | Groupe de services optionnels active par une commande |
| Smoke test | Verification simple des fonctions essentielles apres deploiement |
| Volume | Stockage persistant associe aux services Docker |

## 20. Synthese du flux complet

Le code du projet est rendu disponible a Jenkins par le montage local actuel ou par un depot Git lorsqu'il est configure. Jenkins verifie ses outils et prepare son workspace. Maven nettoie, construit et teste le backend; Jenkins publie les rapports de tests. SonarQube analyse ensuite le code source a l'aide d'un token stocke dans Jenkins. Nexus recoit le JAR et le POM par Maven `deploy`. Compose construit les images, met a jour les services locaux et Jenkins execute des controles HTTP. Prometheus continue de collecter les metriques exposees par Spring Boot et Grafana les rend consultables. L'e-mail est une notification finale optionnelle, qui necessite une configuration SMTP distincte.

Cette chaine relie des responsabilites complementaires :

- Git conserve l'historique source ;
- Maven construit le logiciel ;
- les tests valident des comportements ;
- SonarQube analyse le code ;
- Nexus stocke les artefacts ;
- Docker empaquette l'execution ;
- Compose orchestre les services ;
- Jenkins automatise le flux ;
- Prometheus et Grafana apportent de la visibilite operationnelle.

La valeur DevOps vient de la repetabilite et de la qualite de ce flux, de la securite de ses secrets et de la capacite de l'equipe a comprendre et ameliorer chaque retour.

---

Pour les commandes d'installation resumees et les informations generales du projet, consulter le [README](./README.md).

# Annexes techniques — installation et configuration

Les annexes qui suivent completent le cours sans remplacer ses explications. Elles decrivent l'installation et la configuration correspondant au laboratoire present. Executer les commandes Ubuntu depuis la racine indiquee; les commandes PowerShell sont marquees explicitement.

## Annexe A — Preparer Windows, WSL et Ubuntu

### A.1 Verifier WSL depuis PowerShell

Dans PowerShell Windows, verifier que la distribution Ubuntu utilise WSL 2 :

```powershell
wsl --status
wsl --list --verbose
```

La colonne `VERSION` d'Ubuntu doit indiquer `2`. Si la distribution existe mais utilise WSL 1, la conversion peut etre demandee ainsi :

```powershell
wsl --set-version Ubuntu 2
```

Cette operation ne remplace pas l'activation des prerequis de virtualisation Windows; ceux-ci doivent etre operationnels sur le poste avant de pouvoir demarrer WSL 2. Ne pas lancer de commandes de conversion ou de reinstallation sur une machine de cours sans sauvegarder les distributions a conserver.

### A.2 Ouvrir le projet depuis Ubuntu

Le projet sur `D:` est expose dans Ubuntu sous `/mnt/d` :

```bash
cd "/mnt/d/5NIDS/Labs Cybersecurity and Coding/DevOps_Project/devops-platform"
pwd
```

Garder les guillemets autour du chemin : il contient des espaces. Les commandes `docker compose` doivent etre lancees depuis ce repertoire, car le fichier Compose et `.env` s'y trouvent.

### A.3 Reglage requis par SonarQube

Dans Ubuntu, appliquer le parametre necessaire a SonarQube avant de demarrer les services :

```bash
sudo sysctl -w vm.max_map_count=262144
```

Verifier sa valeur :

```bash
sysctl vm.max_map_count
```

Ce reglage peut devoir etre reapplique apres un redemarrage complet de WSL. Le probleme qui en resulte se voit dans les journaux SonarQube; ne pas conclure qu'un echec du pipeline vient du code avant d'avoir verifie que le serveur SonarQube est disponible.

## Annexe B — Installer les outils Ubuntu

Depuis Ubuntu :

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git openjdk-17-jdk-headless maven docker.io docker-compose-v2
```

Le laboratoire utilise Java 17. Verifier chaque installation :

```bash
java -version
mvn -version
git --version
docker version
docker compose version
```

Demarrer Docker si le service de la distribution n'est pas actif :

```bash
sudo service docker start
docker run --rm hello-world
```

Le groupe Unix `docker` permet d'utiliser Docker sans `sudo`, mais son acces revient pratiquement a disposer de privileges root sur l'environnement Docker. Ne l'accorde qu'a des utilisateurs de confiance.

#### Option systemd pour WSL

Si la distribution Ubuntu est configuree pour systemd et que `sudo service docker start` ne convient pas, systemd peut etre active dans `/etc/wsl.conf` :

```ini
[boot]
systemd=true
```

Apres modification, fermer les processus WSL depuis PowerShell Windows avec :

```powershell
wsl --shutdown
```

Rouvrir Ubuntu, puis demarrer et verifier Docker :

```bash
sudo systemctl start docker
sudo systemctl status docker --no-pager
```

N'activer que le mode de gestion adapte a la distribution; eviter de melanger des services Docker concurrents entre l'integration Docker Desktop et un moteur installe dans Ubuntu.

## Annexe C — Configurer l'environnement du projet

Le fichier `.env.example` liste les variables attendues. `setup.sh` cree `.env` depuis ce modele seulement si `.env` est absent. Il n'ecrase pas une configuration existante.

Depuis la racine `devops-platform` :

```bash
cp .env.example .env
chmod 600 .env
```

Edite `.env` avec un editeur local. Remplace les mots de passe de demonstration avant toute utilisation partagee. Les variables sont utilisees ainsi :

| Variable | Services consommateurs |
|---|---|
| `COMPOSE_PROJECT_NAME` | Noms des ressources Docker Compose |
| `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD` | Base applicative MySQL |
| `SONAR_DB_USER`, `SONAR_DB_PASSWORD` | Base PostgreSQL interne de SonarQube |
| `JENKINS_ADMIN_ID`, `JENKINS_ADMIN_PASSWORD` | Provisionnement initial de l'administrateur Jenkins |
| `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD` | Compte administrateur Grafana |

Les variables MySQL sont prises en compte lors de l'initialisation du volume vide. Changer ensuite `.env` ne reconfigure pas necessairement les comptes deja crees dans la base; il faut alors mettre a jour la base existante avec une procedure controlee.

Ne jamais afficher ou coller le contenu de `.env` dans une console publique, une capture d'ecran, un ticket ou Git. Ne pas remplacer le fichier de secrets par `.env.example` si des donnees locales importantes doivent etre conservees.

## Annexe D — Installer, configurer et demarrer les services Compose

### D.1 Valider la configuration

Depuis la racine du projet :

```bash
docker compose --profile devops --profile monitoring config --quiet
```

Cette commande valide et resout la configuration Compose sans demarrer les services. Compose lit les variables disponibles dans `.env`.

### D.2 Demarrer tout le laboratoire

La methode recommandee est le script fourni :

```bash
bash ./setup.sh --all
```

Il active les profils `devops` et `monitoring`, valide la configuration, construit les images locales et attend les controles de disponibilite. Les autres modes sont :

```bash
bash ./setup.sh             # application et MySQL
bash ./setup.sh --tools     # application, Jenkins, SonarQube et Nexus
bash ./setup.sh --monitoring
bash ./setup.sh --all
```

### D.3 Comprendre la publication des ports

Dans `docker-compose.yml`, une declaration telle que `"8081:80"` signifie `port_hote:port_conteneur`. Le navigateur utilise donc `localhost:8081`, tandis que le service frontend ecoute sur le port 80 de son conteneur. Les services se parlent sur les ports internes et les noms Compose; le backend utilise ainsi `mysql:3306`, non `localhost:3306`.

### D.4 Controle apres demarrage

```bash
docker compose --profile devops --profile monitoring ps
curl --fail http://localhost:8080/api/health
curl --fail http://localhost:8081/
```

Le backend depend de MySQL sain et le frontend depend du backend sain. SonarQube depend de PostgreSQL. Un premier demarrage peut prendre plusieurs minutes, en particulier pour SonarQube et Nexus. Consulte les journaux sans afficher de variables secretes :

```bash
docker compose logs --tail=100 mysql
docker compose logs --tail=100 backend
docker compose logs --tail=100 sonarqube
docker compose logs --tail=100 nexus
```

## Annexe E — Installer et configurer l'application

### E.1 Configuration et schema

Le schema de la base se trouve dans `backend/src/main/resources/schema.sql`. Spring initialise la table `products` au demarrage selon les proprietes de l'application. Les parametres de connexion runtime sont fournis au conteneur backend par Compose via `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME` et `SPRING_DATASOURCE_PASSWORD`.

Le backend ecoute sur le port 8080. `application.properties` active les endpoints Actuator `health`, `info` et `prometheus`, ainsi que les sondes Spring de readiness.

### E.2 Construire et tester localement

Si Java et Maven sont installes sur l'hote Ubuntu :

```bash
cd backend
mvn -B clean verify
cd ..
```

La commande `verify` utilise H2 avec le profil de test, execute les tests et produit les rapports. Le JAR et les rapports apparaissent sous `backend/target/`.

La construction Compose de l'image utilise aussi Maven dans une etape Docker; elle peut donc etre executee meme si Maven n'est pas installe sur l'hote, du moment que Docker fonctionne :

```bash
docker compose build backend frontend
```

Ce sont deux chemins de construction distincts : Maven local pour le cycle de developpement, et Dockerfile multi-etapes pour construire l'image deployable.

### E.3 Configuration de l'interface

Le frontend est une page statique sans outil de compilation JavaScript. `frontend/Dockerfile` la copie dans Nginx. `frontend/nginx.conf` sert le contenu et transmet le chemin `/api/` au backend `backend:8080`. Pour une modification du HTML ou de la configuration Nginx, reconstruire l'image frontend puis redeployer :

```bash
docker compose build frontend
docker compose up -d --wait frontend
```

## Annexe F — Installer et configurer Jenkins

### F.1 Provisionnement du serveur

Compose construit Jenkins depuis `jenkins/Dockerfile`. Cette image ajoute Java 17 via l'image de base, Maven, curl, Docker CLI, Compose v2 et les plugins necessaires au pipeline. Le conteneur utilise un volume `jenkins-home` pour conserver jobs, plugins et credentials.

Le fichier `jenkins/init.groovy.d/zz-pipeline.groovy` configure automatiquement le job `devops-catalog` a partir de `/workspace/Jenkinsfile`. Compose monte le dossier du projet dans `/workspace` en lecture seule. Ce mode permet de suivre le cours sans depot Git distant.

Jenkins ecoute dans le conteneur sur 8080 et l'hote publie `8083:8080`. Le conteneur recoit des variables d'environnement provenant de `.env` pour le compte administrateur initial. Si le volume Jenkins contient deja une configuration, un changement de variables ne remplace pas automatiquement les comptes ou mots de passe deja stockes dans Jenkins.

Acces : `http://localhost:8083`. Connecte-toi avec les valeurs administrateur locales configurees. Ne mets pas de mot de passe dans ce document ou dans les scripts du projet.

### F.2 Parametrer le job

1. Ouvrir **devops-catalog** et verifier que le Jenkinsfile est charge.
2. Utiliser **Build with Parameters** pour executer le job.
3. Garder `USE_LOCAL_SOURCE` active avec la configuration locale actuelle.
4. Garder `RUN_SONAR` et `PUBLISH_NEXUS` actives si les credentials et les services sont configures.
5. Garder `PUBLISH_DOCKER` desactive sauf si une publication externe est deliberement configuree.
6. Laisser `EMAIL_TO` vide tant que le SMTP n'est pas teste.
7. Apres le build, examiner **Full Stage View**, **Console Output**, les tests JUnit et les artefacts archives.

Pour relier un depot Git distant, configurer le job comme **Pipeline script from SCM**, choisir les informations SCM, indiquer `Jenkinsfile` comme chemin et fournir une credential SCM si le depot est prive. Desactiver ensuite `USE_LOCAL_SOURCE` pour utiliser `checkout scm`.

### F.3 Enregistrer les credentials de maniere sure

Dans **Manage Jenkins > Credentials**, ajouter les credentials au scope approprie :

| ID attendu | Type Jenkins | Utilisation |
|---|---|---|
| `sonar-token` | Secret text | Authentification du scanner Sonar |
| `nexus-credentials` | Username with password | Publication Maven et configuration Nexus dans le pipeline actuel |
| `dockerhub-credentials` | Username with password | Publication Docker optionnelle |

L'identifiant doit correspondre exactement a celui du Jenkinsfile. Les champs secret s'entrent dans l'interface Jenkins; ils ne sont ni fournis dans les arguments visibles d'une commande ni inscrits dans le depot.

**Avertissement Docker :** le socket `/var/run/docker.sock` est monte dans Jenkins et le conteneur Jenkins tourne avec des privileges eleves pour ce laboratoire. Cette configuration peut donner a un pipeline modifiable un controle tres large sur Docker et l'hote. N'expose pas ce Jenkins a des utilisateurs ou depots non fiables.

## Annexe G — Installer et configurer SonarQube

### G.1 Service et base interne

Avec le profil `devops`, Compose demarre PostgreSQL puis SonarQube. PostgreSQL conserve les donnees de SonarQube dans le volume `sonarqube-db`; SonarQube conserve ses donnees, extensions et journaux dans des volumes distincts. Le navigateur accede a `http://localhost:9000`, mais Jenkins utilise `http://sonarqube:9000` sur le reseau interne.

Appliquer `vm.max_map_count` avant le demarrage initial, comme decrit en Annexe A. Attendre que l'interface soit disponible avant de generer le token.

### G.2 Creer le projet et le token

1. Ouvrir l'interface SonarQube et se connecter avec le compte administrateur qui a ete configure lors du premier acces.
2. Creer le projet manuel avec la cle `devops-catalog` si le projet n'est pas deja apparu apres une analyse.
3. Dans les parametres de compte, generer un token adapte a l'analyse.
4. Copier le token directement dans Jenkins Credentials sous l'ID exact `sonar-token`, type **Secret text**.
5. Ne pas ecrire le token dans `pom.xml`, `.env`, le Jenkinsfile, un commit ou une capture.
6. Lancer un build Jenkins avec `RUN_SONAR` active et verifier le message de succes dans la console.
7. Ouvrir le projet `devops-catalog` dans SonarQube et examiner les mesures et la quality gate.

Le scanner utilise le plugin Maven avec sa coordonnee complete dans le Jenkinsfile. Cela evite de dependre d'une resolution implicite du prefixe Maven `sonar`. La cle de projet transmise au scanner doit correspondre a celle creee dans SonarQube.

Si la connexion echoue, examiner les journaux SonarQube, l'etat de PostgreSQL, la validite et les permissions du token Jenkins, et la difference entre l'adresse interne `sonarqube:9000` et l'adresse navigateur `localhost:9000`.

## Annexe H — Installer et configurer Nexus Repository

### H.1 Initialisation et EULA

Nexus demarre dans le profil `devops`, expose l'interface sur `http://localhost:8082` et stocke son etat dans le volume `nexus-data`. Le port interne du conteneur est 8081; depuis Jenkins, l'adresse est `http://nexus:8081`.

Lors de la premiere installation, le mot de passe initial genere par Nexus peut etre lu dans le conteneur :

```bash
docker exec devops-lab-nexus-1 cat /nexus-data/admin.password
```

Cette commande affiche un secret dans le terminal local : ne copie pas sa sortie dans un journal partage ou une capture. Connecte-toi avec l'identifiant `admin`, puis suis l'assistant de premiere configuration pour remplacer le mot de passe initial et configurer le compte. Apres le changement, l'ancien fichier peut ne plus etre present ou valide; conserve le nouveau secret dans un gestionnaire approuve et ajoute la credential correspondante dans Jenkins.

Les versions Community Edition recentes demandent la lecture et l'acceptation de l'EULA avant la publication. La personne responsable doit lire les conditions et confirmer elle-meme l'acceptation dans l'interface ou selon la procedure officielle applicable. Jenkins ne doit pas accepter une EULA automatiquement.

### H.2 Depot Maven et permissions

Le pipeline local met a jour ou utilise un depot Maven2 hosted nomme `maven-releases`. Verifie dans Nexus :

1. que le depot est de type **maven2 (hosted)** ;
2. que la version est configuree pour les **releases** ;
3. que le depot est en ligne ;
4. que la strategie `ALLOW` correspond au comportement de republication du laboratoire ;
5. que l'identifiant `nexus-credentials` de Jenkins correspond au compte utilise pour configurer et publier.

Le Jenkinsfile provisionne actuellement le role `jenkins-maven-releases-publisher`, mais utilise egalement une credential administrateur pour modifier l'utilisateur et le depot. Cela est specifique au laboratoire. Dans un environnement partage, cree un compte de service distinct, limite aux privileges necessaires, puis adapte le Jenkinsfile pour ne pas modifier le compte administrateur.

### H.3 Verifier une publication

Lancer un build avec `PUBLISH_NEXUS` actif. Une publication reussie affiche des lignes Maven `Uploaded to nexus-releases`. Dans Nexus, parcourir :

```text
maven-releases
  / com
    / example
      / devops-backend
        / 1.0.0
```

Les fichiers attendus comprennent le JAR et le POM. Si Maven retourne `403`, verifier l'EULA, le compte, les permissions et la politique du depot; si Maven retourne une erreur de connexion, verifier l'adresse interne `nexus:8081` et l'etat du conteneur.

## Annexe I — Installer et configurer Prometheus et Grafana

### I.1 Configuration Prometheus

Le profil `monitoring` active Prometheus. Le Dockerfile prometheus embarque `monitoring/prometheus/prometheus.yml`. Ce fichier interroge `backend:8080` sur `/actuator/prometheus` a intervalle de 15 secondes et nomme la cible `devops-backend`.

Apres demarrage, ouvrir `http://localhost:9090`, consulter **Status > Targets** et confirmer que la cible est `UP`. Dans **Graph**, la requete suivante affiche l'etat des cibles :

```promql
up
```

Une cible `DOWN` demande de verifier que le backend est sain, que l'endpoint Actuator est expose et que Prometheus peut resoudre `backend` sur le reseau Compose.

### I.2 Configuration Grafana

Grafana est expose sur `http://localhost:3000`. Le compte administrateur et son secret proviennent de `.env`. Le fichier de provisioning dans `monitoring/grafana/provisioning/datasources/prometheus.yml` configure automatiquement une source Prometheus par defaut a l'adresse interne `http://prometheus:9090`.

Une fois connecte :

1. ouvrir **Connections > Data sources** et verifier la source Prometheus ;
2. utiliser l'action de verification disponible pour confirmer la connexion ;
3. consulter ou creer les visualisations necessaires avec les requetes PromQL appropriees.

Le depot configure la source de donnees, mais ne garantit pas la presence d'un tableau de bord metier complet. Les tableaux de bord doivent etre crees ou importes selon les metriques effectivement exposees par l'application.

## Annexe J — Configurer Git pour le pipeline (option depot distant)

Le pipeline courant utilise `/workspace` et ne requiert pas Git distant. Pour un scenario de cours connecte a un depot :

1. verifier `.gitignore` et l'absence de `.env` dans les fichiers a publier ;
2. initialiser ou utiliser un depot Git existant a la racine du projet ;
3. committer le code et publier une branche ;
4. dans Jenkins, creer ou modifier le job Pipeline pour choisir **Pipeline script from SCM** ;
5. choisir Git, fournir l'URL du depot et ajouter une credential Jenkins si necessaire ;
6. definir le chemin du script a `Jenkinsfile` ;
7. desactiver `USE_LOCAL_SOURCE` a l'execution du build ;
8. verifier dans Console Output que le checkout du commit attendu a eu lieu.

Un webhook Git n'est possible que si le service Jenkins est joignable depuis le serveur Git. `localhost` sur une machine de developpement n'est pas joignable depuis Internet; ne pas exposer un Jenkins non durci juste pour activer un webhook.

## Annexe K — Configurer l'e-mail optionnel

L'e-mail requiert a la fois le plugin `email-ext` (installe par l'image Jenkins du projet), une configuration SMTP valide dans Jenkins et une valeur `EMAIL_TO` non vide au lancement du pipeline.

1. Demander les parametres SMTP a l'administrateur du fournisseur de messagerie.
2. Dans **Manage Jenkins > System**, configurer **Extended E-mail Notification** avec l'hote, le port, TLS/SSL selon le fournisseur, l'expediteur et les identifiants requis.
3. Si le fournisseur offre une authentification par application, utiliser un mot de passe d'application dedie plutot que le mot de passe personnel.
4. Configurer egalement le serveur de courrier standard si la page Jenkins le demande pour les fonctions de notification.
5. Tester la configuration depuis Jenkins avec la fonction de test proposee.
6. Dans **Build with Parameters**, renseigner `EMAIL_TO` avec une adresse autorisee.
7. Lancer le pipeline et verifier que le stage final **Email verification** s'execute et que le message est effectivement recu.

Ne jamais ajouter le mot de passe SMTP dans le Jenkinsfile ou un fichier versionne. Tant que la configuration SMTP n'a pas ete testee, laisser `EMAIL_TO` vide; une etape ignoree n'est pas une confirmation d'envoi.

## Annexe L — Sauvegarde, redemarrage et reinitialisation

### L.1 Redemarrer sans supprimer les donnees

```bash
docker compose --profile devops --profile monitoring restart
```

Attendre ensuite que les services soient revenus et tester leurs URLs. Un redemarrage peut invalider les sessions navigateur; il ne doit pas reinitialiser les volumes.

### L.2 Arreter ou reconstruire

Pour arreter proprement selon le projet :

```bash
bash ./down.sh
```

Pour reconstruire les services declares et demarrer tous les profils :

```bash
bash ./setup.sh --all
```

Les commandes `up --build` peuvent reconstruire les images locales; elles ne suppriment pas les volumes nommes.

### L.3 Reinitialisation destructive

`docker compose down -v` supprime les volumes de ce projet. Cela peut effacer MySQL, l'historique et la configuration Jenkins, les analyses SonarQube, le contenu Nexus et l'etat Grafana/Prometheus. Cette commande ne doit etre utilisee que pour un laboratoire que l'on souhaite volontairement remettre a zero, apres verification de la configuration Compose et sauvegarde des donnees necessaires.

## Annexe M — Matrice de verification apres installation

| Controle | Commande ou interface | Resultat attendu |
|---|---|---|
| Compose valide | `docker compose --profile devops --profile monitoring config --quiet` | Sortie silencieuse et code retour 0 |
| Services actifs | `docker compose --profile devops --profile monitoring ps` | Conteneurs `Up`; controles `healthy` quand declares |
| Maven | `cd backend && mvn -B clean verify` | Build Maven reussi et tests valides |
| Interface web | `http://localhost:8081` | Page du catalogue |
| API | `curl --fail http://localhost:8080/api/health` | Reponse HTTP reussie et statut `UP` |
| Jenkins | `http://localhost:8083` | Connexion et job `devops-catalog` |
| SonarQube | `http://localhost:9000` | Projet et resultat d'analyse |
| Nexus | `http://localhost:8082` | Depot `maven-releases` et artefact publie |
| Prometheus | `http://localhost:9090` | Cible `devops-backend` `UP` |
| Grafana | `http://localhost:3000` | Source Prometheus connectee |
| E-mail | Console du build et boite destinataire | Stage execute et message recu apres SMTP configure |

La verification doit porter sur la fonction reelle et pas seulement sur l'ouverture d'une page : une page de connexion Jenkins en HTTP 200 ne prouve pas qu'un build fonctionne; la presence d'une cible Prometheus ne prouve pas qu'un artefact est publie; seul un build avec les stages concernes et les resultats verifies valide la chaine correspondante.
