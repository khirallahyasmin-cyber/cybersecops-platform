import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import hudson.security.HudsonPrivateSecurityRealm
import hudson.model.User
import jenkins.model.Jenkins
import hudson.security.HudsonPrivateSecurityRealm.Details

def jenkins = Jenkins.get()
def username = System.getenv('JENKINS_ADMIN_ID')
def password = System.getenv('JENKINS_ADMIN_PASSWORD')

if (!username || !password) {
    throw new IllegalStateException('JENKINS_ADMIN_ID and JENKINS_ADMIN_PASSWORD must be configured.')
}

if (!(jenkins.getSecurityRealm() instanceof HudsonPrivateSecurityRealm)) {
    jenkins.setSecurityRealm(new HudsonPrivateSecurityRealm(false))
}

def adminUser = User.getById(username, true)
adminUser.addProperty(Details.fromPlainPassword(password))
adminUser.save()

def authorization = new FullControlOnceLoggedInAuthorizationStrategy()
authorization.setAllowAnonymousRead(false)
jenkins.setAuthorizationStrategy(authorization)
jenkins.save()
