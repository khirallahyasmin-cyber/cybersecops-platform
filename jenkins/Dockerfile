FROM jenkins/jenkins:lts-jdk17
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg git maven pre-commit python3 \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && curl -fsSL https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor -o /usr/share/keyrings/trivy.gpg \
    && . /etc/os-release \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list \
    && echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb ${VERSION_CODENAME} main" > /etc/apt/sources.list.d/trivy.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin trivy=0.71.2 \
    && rm -rf /var/lib/apt/lists/*
COPY init.groovy.d/ /usr/share/jenkins/ref/init.groovy.d/
RUN jenkins-plugin-cli --plugins workflow-aggregator git sonar credentials-binding timestamper junit pipeline-stage-view email-ext htmlpublisher
USER jenkins
