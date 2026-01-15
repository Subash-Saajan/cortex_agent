#!/bin/bash

# Cortex Agent - AWS Deployment Script

set -e

echo "=== Cortex Agent AWS Deployment ==="
echo ""

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"

echo "AWS Account ID: $ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"
echo ""

# ECR URLs
ECR_BACKEND="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/cortex-agent-backend"
ECR_FRONTEND="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/cortex-agent-frontend"

echo "=== Step 1: Login to ECR ==="
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
echo "✓ Logged in to ECR"
echo ""

echo "=== Step 2: Build Backend Image ==="
docker build -t cortex-agent-backend:latest ./backend
docker tag cortex-agent-backend:latest $ECR_BACKEND:latest
echo "✓ Backend image built"
echo ""

echo "=== Step 3: Push Backend Image ==="
docker push $ECR_BACKEND:latest
echo "✓ Backend image pushed to ECR"
echo ""

echo "=== Step 4: Build Frontend Image ==="
docker build -t cortex-agent-frontend:latest ./frontend
docker tag cortex-agent-frontend:latest $ECR_FRONTEND:latest
echo "✓ Frontend image built"
echo ""

echo "=== Step 5: Push Frontend Image ==="
docker push $ECR_FRONTEND:latest
echo "✓ Frontend image pushed to ECR"
echo ""

echo "=== Step 6: Update ECS Service ==="
aws ecs update-service \
  --cluster cortex-agent-cluster \
  --service cortex-agent-service \
  --force-new-deployment \
  --region $AWS_REGION
echo "✓ ECS service updated"
echo ""

echo "=== Deployment Complete! ==="
echo ""
echo "Next steps:"
echo "1. Wait for ECS task to be RUNNING (1-2 minutes)"
echo "2. Get CloudFront domain: aws cloudfront list-distributions --query 'DistributionList.Items[0].DomainName' --output text"
echo "3. Get ECS public IP: aws ecs describe-tasks --cluster cortex-agent-cluster --tasks <task-arn> --query 'tasks[0].attachments[0].details[1].value' --output text"
echo "4. Test backend health: curl http://<ecs-public-ip>:8000/health"
echo ""
