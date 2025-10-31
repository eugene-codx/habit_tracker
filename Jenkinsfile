pipeline {
    agent { label 'agent1' }
    environment {
        REPO_URL = credentials('REPO_URL')
        SERVER_IP = credentials('SERVER_IP')
        REMOTE_DIR_DEV = credentials('REMOTE_DIR_DEV')
        REMOTE_DIR_PROD = credentials('REMOTE_DIR_PROD')
        DOCKER_COM_IMAGE = "ghcr.io/eugene-codx"
        DOCKER_TAG = "latest"
        APP_NAME = 'habit_be'
    }
    triggers {
        githubPush()
    }
    parameters {
        string(name: 'BRANCH_NAME', defaultValue: 'main', description: 'Branch to build')
        booleanParam(name: 'RUN_QA_TESTS', defaultValue: true, description: 'Run QA Tests')
        booleanParam(name: 'DEPLOY_TO_PROD', defaultValue: false, description: 'Deploy to Production')
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm: ([
                    $class: 'GitSCM',
                    branches: [[name: '$BRANCH_NAME']],
                    extensions: [
                        [$class: 'CloneOption', depth: 1, shallow: true],
                        [$class: 'CleanBeforeCheckout']
                    ],
                    userRemoteConfigs: [[
                        url: env.REPO_URL,
                        credentialsId: 'GITHUB_SSH_KEY'
                    ]]
                ])
            }
        }
        stage('Build Docker Image') {
            steps {
                script {
                    appImage = docker.build("${DOCKER_COM_IMAGE}/${APP_NAME}:${DOCKER_TAG}")
                }
            }
        }
        stage('Push to GitHub Container Registry') {
            steps {
                script {
                    docker.withRegistry('https://ghcr.io', 'GITHUB_CONTAINER_REGISTRY_TOKEN') {
                        appImage.push()
                    }
                }
            }
        }
        stage('Deploy DEV to Ubuntu Server') {
            steps {
                script {
                    // Retrieve .env and SSH key from Jenkins Credentials
                    withCredentials([
                        file(credentialsId: 'ENV_DEV_habit', variable: 'SECRET_ENV_FILE_DEV'),
                        sshUserPrivateKey(
                            credentialsId: 'PSUSERDEPLOY_SSH',
                            keyFileVariable: 'SSH_KEY',
                            usernameVariable: 'SSH_USER'
                        ),
                        usernamePassword(
                            credentialsId: 'GITHUB_TOKEN_CREDENTIALS',
                            usernameVariable: 'GITHUB_USER',
                            passwordVariable: 'GITHUB_TOKEN'
                        )
                    ]) {
                        // DEVELOPMENT
                        // 1.1 First create directory and set DEV permissions
                        sh '''
                            ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" \
                                "${SSH_USER}@${SERVER_IP}" \
                                "sudo mkdir -p \\"${REMOTE_DIR_DEV}\\" && \
                                 sudo chown -R ${SSH_USER}:${SSH_USER} \\"${REMOTE_DIR_DEV}\\" && \
                                 sudo chmod 755 \\"${REMOTE_DIR_DEV}\\""
                        '''
                        // 2.1 Clean previous DEV version
                        sh '''
                            ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" \
                                "${SSH_USER}@${SERVER_IP}" \
                                "cd \\"${REMOTE_DIR_DEV}\\" && \
                                rm -f docker-compose.yml .env"
                        '''
                        // 3.1 Safely copy .env and docker-compose.yml files for DEV
                        sh '''
                            scp -o StrictHostKeyChecking=no -i "$SSH_KEY" \
                                "$SECRET_ENV_FILE_DEV" \
                                "${SSH_USER}@${SERVER_IP}:${REMOTE_DIR_DEV}/.env"

                            scp -o StrictHostKeyChecking=no -i "$SSH_KEY" \
                                docker-compose.yml \
                                "${SSH_USER}@${SERVER_IP}:${REMOTE_DIR_DEV}/"
                        '''
                        // 4.1 Stop previous DEV version
                        sh '''
                            ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" \
                                "${SSH_USER}@${SERVER_IP}" \
                                "cd \\"${REMOTE_DIR_DEV}\\" && \
                                docker-compose down --volumes --remove-orphans --timeout 30"
                        '''
                        // 5.1 Start DEV containers
                        sh '''
                            ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" \
                                "${SSH_USER}@${SERVER_IP}" "
                                # Log in to GitHub docker registry
                                echo '$GITHUB_TOKEN' | docker login ghcr.io -u '$GITHUB_USER' --password-stdin
                                cd '$REMOTE_DIR_DEV'
                                docker pull '$DOCKER_COM_IMAGE/$APP_NAME:$DOCKER_TAG'
                                docker-compose up -d
                            "
                        '''
                    }
                }
            }
        }
        stage('Run QA Tests') {
            when {
                expression { return params.RUN_QA_TESTS == true }
            }
            steps {
                echo "Triggering external QA Job..."
                // Run another Job and wait for it to finish
                script {
                    def qaBuild = build job: 'Habit_AT',
                                         wait: true,            // wait for completion
                                         propagate: true        // if it fails, the current pipeline fails too
                    echo "QA Job finished with status: ${qaBuild.getResult()}"
                }
            }
        }
        stage('Deploy PROD to Ubuntu Server') {
            when {
                expression { return params.DEPLOY_TO_PROD == true }
            }
            steps {
                script {
                    // Retrieve .env and SSH key from Jenkins Credentials
                    withCredentials([
                        file(credentialsId: 'ENV_PROD_Awakeia', variable: 'SECRET_ENV_FILE_PROD'),
                        sshUserPrivateKey(
                            credentialsId: 'PSUSERDEPLOY_SSH',
                            keyFileVariable: 'SSH_KEY',
                            usernameVariable: 'SSH_USER'
                        ),
                        usernamePassword(
                            credentialsId: 'GITHUB_TOKEN_CREDENTIALS',
                            usernameVariable: 'GITHUB_USER',
                            passwordVariable: 'GITHUB_TOKEN'
                        )
                    ]) {
                        // PRODUCTION
                        // 1.2 Create directory and set PROD permissions
                        sh '''
                            ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" \
                                "${SSH_USER}@${SERVER_IP}" \
                                "sudo mkdir -p \\"${REMOTE_DIR_PROD}\\" && \
                                 sudo chown -R ${SSH_USER}:${SSH_USER} \\"${REMOTE_DIR_PROD}\\" && \
                                 sudo chmod 755 \\"${REMOTE_DIR_PROD}\\""
                        '''
                        // 2.2 Clean previous PROD version
                        sh '''
                            ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" \
                                "${SSH_USER}@${SERVER_IP}" \
                                "cd \\"${REMOTE_DIR_PROD}\\" && \
                                rm -f docker-compose.yml .env"
                        '''
                        // 3.2 Safely copy .env and docker-compose.yml files for PROD
                        sh '''
                            scp -o StrictHostKeyChecking=no -i "$SSH_KEY" \
                                "$SECRET_ENV_FILE_PROD" \
                                "${SSH_USER}@${SERVER_IP}:${REMOTE_DIR_PROD}/.env"

                            scp -o StrictHostKeyChecking=no -i "$SSH_KEY" \
                                docker-compose.yml \
                                "${SSH_USER}@${SERVER_IP}:${REMOTE_DIR_PROD}/"
                        '''
                        // 4.2 Stop previous PROD version
                        sh '''
                            ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" \
                                "${SSH_USER}@${SERVER_IP}" \
                                "cd \\"${REMOTE_DIR_PROD}\\" && \
                                docker-compose down --volumes --remove-orphans --timeout 30"
                        '''
                        // 5.2 Start PROD containers
                        sh '''
                            ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" \
                                "${SSH_USER}@${SERVER_IP}" "
                                # Log in to GitHub docker registry
                                echo '$GITHUB_TOKEN' | docker login ghcr.io ghcr.io -u '$GITHUB_USER' --password-stdin
                                cd '$REMOTE_DIR_PROD'
                                docker pull '$DOCKER_COM_IMAGE/$APP_NAME:$DOCKER_TAG'
                                docker-compose up -d
                            "
                        '''
                    }
                }
            }
        }
    }
}
