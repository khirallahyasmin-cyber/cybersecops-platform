import jenkins.model.Jenkins
import hudson.model.BooleanParameterValue
import hudson.model.ParametersAction
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition
import org.jenkinsci.plugins.workflow.job.WorkflowJob

def jenkins = Jenkins.get()
def jobName = 'devops-catalog'
def job = jenkins.getItem(jobName)
def jenkinsfile = new File('/workspace/Jenkinsfile')

if (!jenkinsfile.isFile()) {
    throw new IllegalStateException("Cannot configure ${jobName}: /workspace/Jenkinsfile is missing.")
}

if (job == null) {
    job = jenkins.createProject(WorkflowJob, jobName)
}

job.setDefinition(new CpsFlowDefinition(jenkinsfile.getText('UTF-8'), true))
job.setDescription('Pipeline local du catalogue DevOps : Maven, tests, images Docker Compose, deploiement et smoke tests.')
job.save()

if (job.getLastSuccessfulBuild() == null && !job.isBuilding()) {
    job.scheduleBuild2(0, new ParametersAction(new BooleanParameterValue('USE_LOCAL_SOURCE', true)))
}
