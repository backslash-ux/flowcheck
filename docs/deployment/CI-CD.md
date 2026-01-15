# CI/CD Integration Guide

Integrate FlowCheck into your CI/CD pipelines.

## GitHub Actions

### Basic Workflow

```yaml
name: FlowCheck

on: [pull_request, push]

jobs:
  check:
    runs-on: ubuntu-latest
    container: backslash-ux/flowcheck:latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run FlowCheck
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: flowcheck check --strict
```

### With Docker Build & Push

```yaml
name: Build and Push

on:
  push:
    branches: [main, release/**]
    tags: [v*]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: docker/setup-buildx-action@v2
      
      - uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - uses: docker/build-push-action@v4
        with:
          push: true
          tags: backslash-ux/flowcheck:latest
```

## GitLab CI

```yaml
stages:
  - check
  - build
  - deploy

check:
  stage: check
  image: backslash-ux/flowcheck:latest
  script:
    - flowcheck check --strict

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t flowcheck:latest .
    - docker push $CI_REGISTRY_IMAGE:latest
```

## Jenkins

```groovy
pipeline {
  agent any
  
  stages {
    stage('Check') {
      steps {
        sh 'docker run --rm -v $(pwd):/workspace -w /workspace backslash-ux/flowcheck:latest flowcheck check --strict'
      }
    }
    
    stage('Build') {
      steps {
        sh 'docker build -t flowcheck:$BUILD_NUMBER .'
      }
    }
    
    stage('Deploy') {
      steps {
        sh 'docker push myregistry.azurecr.io/flowcheck:$BUILD_NUMBER'
      }
    }
  }
}
```

## See Also

- [Docker Deployment](Docker.md)
- [Kubernetes Deployment](Kubernetes.md)
