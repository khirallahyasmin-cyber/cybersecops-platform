# Copie téléchargeable du projet

L'archive de distribution contient les sources du projet et, si disponible au moment de sa création, le JAR exécutable Spring Boot du backend sous `offline-backend/`. Ce JAR embarque les bibliothèques Maven du backend.

Cette archive n'est pas une distribution totalement hors ligne : les images Docker (MySQL, Jenkins, SonarQube, Nexus, Prometheus, Grafana, ainsi que les images de base pour construire l'application) ne sont pas incluses. La configuration complète du laboratoire requiert Docker Desktop avec Compose et un accès réseau lors du premier démarrage pour obtenir ces images. Le backend utilise également MySQL; le JAR seul ne lance donc pas toute la plateforme.

Le fichier `.env` local n'est volontairement pas distribué, car il contient des paramètres et mots de passe propres à la machine. Utiliser `.env.example` comme point de départ et définir ses propres secrets.

Pour lancer la plateforme depuis un environnement avec Docker Compose et accès réseau, à la racine du projet :

```powershell
Copy-Item .env.example .env
docker compose --profile devops --profile monitoring up -d --build
```

Les sources du backend se trouvent dans `backend/`; les images backend et frontend sont construites à partir de leurs Dockerfiles. Pour obtenir une vraie copie autonome hors ligne, il faut préparer et exporter les images Docker nécessaires depuis un hôte Docker connecté, puis transporter également ces archives avec le projet. Le poste qui a produit cette copie ne disposait pas de Docker; les images ne pouvaient donc pas y être exportées.
