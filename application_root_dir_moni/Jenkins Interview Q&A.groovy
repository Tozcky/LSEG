Jenkins Interview Q&A

######what is Jenkins ?#############

an open source tool to automate all sorts of task related to building testing and devivering or deploying software
primarally used for ci/cd pipelines.

#######what are the plugins in jenkings##########
 maven
 sonar scanner >> performing code quality checks
 nexus
 kubernetes
 ssh credentials
 git 

############How jenkins works  ? ##############

changes are pushed in to the git repo
once jenkins is informed,  it automatically triggers the pipeline job to execute the task in pipeline.
it fetch the  source code from repo and create a local copy of it 
then as per the commad which we have given  compile the source code >> perform unit testing > build the application to generate the artifact like .jar or .war file
then it can go to the docker steps . build the image 
then it deploy the application to deployment server (qa/ stg or prod)

#############Default env variables in jenkins ################
$JOB_NAME
$NODE_NAME
$WORKSPACE
$BUILD_URL
$JENKINS_URL
$BUILD_ID 

1. Explain the master slave architecture of Jenkins

jenkins master pull the code from the remote GIthub repo every time there is a code commit
it distribute the workload to the all jenkins slaves
on request from the jenkins master , the slaves carry out builds and test and produce the test reports

2. what is a jenkinsfile and what it does ?

it is a text file that contains the definition of a jenkins pipeline and is checked into source control repo
    *.Allows code reveie and iteration on the pipeline
    *.Permits audit trail for the pipeline
    *.there is a single source of truth for the pipeline which can be viewed and edited.

3. Which of the following commands runs jenkins from the command line ?
    *. java -jar jenkins.war

4. what concepts are key aspects of jenkins pipeline ?

*.Pipeline : user defined model of a ( CD continues delivery pipeline, pipelines code defines entrie build process, that includes building testing and delivering an application
*.Node: A machine which is part of jenkins env capable of exeuting a pipeline
*.Step: A single task that tells jenkins what to do at a particular point in time
*.Stage: Defines a conceptually distinct subset of tasks performed through the entire pipeline(build,test,deploy stages)

5. which file is used to define dependency in maven ? 
    pome.xml

6. Explain the two types of pipeline in jenkins along with their syntax
    jenkins provide 2 ways of developing a pipeline code :  SCRIPTED and DECLARATIVE

######################3###SCRIPTED:########################
Scripted pipeline : it is based on groovy script as their domain specific language. One or more node blocks does the core work throughout the entire pipeline

    node{                           >> execute this pipeline or any of its stages on any available agent
         stage('Build'){            >> Define the Builed stage
                                    >> Performs steps related to Build stage
         }
         stage('Test'){             >> Define the test stage
                                    >> Performs steps related to test stage
         }
         stage('Deploy'){           >> Define the Deploy Stage
                                    >> Performs steps related to deploy stage
         }
    }

#########################################################


##################DECLARATIVE############################
Declarative pipeline : it provide a simple and friendly snytax to define a pipeline, here pipeline block defines the work done throughout the pipeline

    pipeline{
        agent any                              >> Execute this pipeline or any of its stages on any available agent
        stages{
            stage('Build'){                    >> Define the Builed stage
                steps{
                                               >> Performs steps related to Build stage
                }
            }
            stage('Test'){                  >> Define the test stage  
                steps{
                                            >> Performs steps related to test stage
                }
            }
            stage('Deploy'){                >> Define the Deploy Stage
                steps{
                                            >> Performs steps related to deploy stage
                }
            }
        }
    }
##########################################################


7. how do you create a backup and copy files in jenkins
   periodically backup you JENKINS_HOME directory  (its container : build jobs configurations/slave node configurations/ build history)

8. Name three security mechanisms jenkins uses to authenticate users
   *. it use internal DB to store user data
   *.LDAP server can be used by jenkings to authenticate users
   *.jenkins can be configured to employ the authentication mechanism used by the application server upon which it is deployed.

9. how to deploy a custome build of a core plugin ?

    Copy the .hpi file to $JENKINS_HOME/plugins
    Remove the plugins development directory
    create an empty file called <plugin>.hpi.pinned
    Restart the jenkins and use you custome buil of a core plugin

10.