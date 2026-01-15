# Deployment Setup Guide

## GitHub Secrets Configuration

To enable the GitHub Actions CI/CD pipeline, you need to add AWS credentials as repository secrets.

### Steps:

1. **Generate AWS Access Key:**
   - Go to AWS Console → IAM → Users → Select your user
   - Security credentials tab → Create access key
   - Copy the Access Key ID and Secret Access Key

2. **Add to GitHub:**
   - Go to https://github.com/Subash-Saajan/cortex_agent/settings/secrets/actions
   - Click "New repository secret"
   - Add two secrets:
     - **AWS_ACCESS_KEY_ID**: Your AWS Access Key ID
     - **AWS_SECRET_ACCESS_KEY**: Your AWS Secret Access Key

3. **Trigger Deployment:**
   - Any push to `main` branch will automatically:
     - Build Docker images
     - Push to ECR
     - Update ECS service
     - Monitor deployment

## Infrastructure Summary

| Component | Details |
|-----------|---------|
| CloudFront Domain | https://d3ouv9vt88djdf.cloudfront.net |
| RDS Endpoint | cortex-agent-db.cafuw86ac9wv.us-east-1.rds.amazonaws.com:5432 |
| Database | cortexdb (username: postgres) |
| ECS Cluster | cortex-agent-cluster |
| ECS Service | cortex-agent-service |
| ECR Backend | 045230654519.dkr.ecr.us-east-1.amazonaws.com/cortex-agent-backend |
| ECR Frontend | 045230654519.dkr.ecr.us-east-1.amazonaws.com/cortex-agent-frontend |

## Monitoring Deployment

1. **Check GitHub Actions:**
   - Go to https://github.com/Subash-Saajan/cortex_agent/actions
   - Watch the workflow run in real-time

2. **Check ECS Service:**
   ```bash
   aws ecs describe-services \
     --cluster cortex-agent-cluster \
     --services cortex-agent-service \
     --region us-east-1
   ```

3. **View ECS Logs:**
   ```bash
   aws logs tail /ecs/cortex-agent --follow
   ```

4. **Get Public IP (once running):**
   ```bash
   TASK_ARN=$(aws ecs list-tasks --cluster cortex-agent-cluster --region us-east-1 --query 'taskArns[0]' --output text)
   aws ecs describe-tasks --cluster cortex-agent-cluster --tasks $TASK_ARN --region us-east-1 --query 'tasks[0].attachments[0].details[1].value' --output text
   ```

5. **Test Backend:**
   ```bash
   curl http://<ecs-public-ip>:8000/health
   ```

## Next Steps

1. Add GitHub Secrets (AWS credentials)
2. Push any change to `main` branch to trigger deployment
3. Monitor logs in CloudWatch
4. Test backend at public IP
5. Proceed to Days 3-4 (Core Agent & Memory)
