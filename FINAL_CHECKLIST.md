# Final Deployment & Testing Checklist

**Status:** Days 1-7 Complete | **Remaining:** Day 8-9 Testing & Polish | **Deadline:** January 24 (Bonus: Jan 22)

---

## ✅ Pre-Deployment Checklist

### AWS Setup (Days 1-2) - COMPLETE
- [x] VPC and networking
- [x] ECS Fargate cluster
- [x] RDS PostgreSQL database
- [x] S3 + CloudFront for frontend
- [x] ECR repositories
- [x] CloudWatch logging
- [x] Security groups and IAM roles

### Backend Implementation (Days 3-6) - COMPLETE
- [x] LangGraph agent with Claude
- [x] Database schema (users, messages, memory)
- [x] Chat endpoint with memory context
- [x] Google OAuth authentication
- [x] Gmail API integration
- [x] Calendar API integration
- [x] Memory fact extraction
- [x] All API routes implemented

### Frontend Implementation (Days 7) - COMPLETE
- [x] Next.js setup
- [x] Google OAuth login UI
- [x] Chat interface
- [x] Message history display
- [x] Error handling
- [x] Loading states
- [x] Responsive design

---

## 🚀 Deployment Steps (15 minutes)

### Step 1: Add GitHub Secrets (2 minutes)
```bash
Go to: https://github.com/Subash-Saajan/cortex_agent/settings/secrets/actions

Add these secrets:
- AWS_ACCESS_KEY_ID: [Your AWS Access Key ID]
- AWS_SECRET_ACCESS_KEY: [Your AWS Secret Access Key]
```

### Step 2: Trigger Deployment (Automatic)
```bash
# Make a small change and push to trigger GitHub Actions
echo "# Deployment triggered" >> DEPLOYMENT.log
git add DEPLOYMENT.log
git commit -m "Trigger GitHub Actions deployment"
git push
```

### Step 3: Monitor Deployment (2-5 minutes)
```bash
# Watch GitHub Actions progress
https://github.com/Subash-Saajan/cortex_agent/actions

# When ECS task starts, get its ARN
aws ecs list-tasks --cluster cortex-agent-cluster --region us-east-1 --output text

# Get task details
aws ecs describe-tasks --cluster cortex-agent-cluster --tasks <TASK_ARN> --region us-east-1

# Get public IP from task
aws ecs describe-tasks --cluster cortex-agent-cluster --tasks <TASK_ARN> --region us-east-1 \
  --query 'tasks[0].attachments[0].details[1].value' --output text
```

### Step 4: Test Backend
```bash
# Test health endpoint
curl http://<ECS_PUBLIC_IP>:8000/health

# Should return:
# {"status": "healthy", "service": "cortex-agent-api"}
```

---

## 📝 Testing Plan (Days 8-9)

### Authentication Flow
```
Test Steps:
1. Open frontend at CloudFront domain
2. Click "Sign in with Google"
3. Complete Google OAuth
4. Verify redirect back to app
5. Confirm JWT token in localStorage
```

### Chat Functionality
```
Test Steps:
1. After login, type a message
2. Click Send
3. Verify message appears as "You"
4. Wait for agent response
5. Check database has message stored
```

### Memory System
```
Test Steps:
1. Send: "I hate 9 AM meetings and love coffee"
2. Continue conversation for 2-3 turns
3. Later, ask: "What do you know about me?"
4. Verify agent references learned facts
5. Check memory_facts table in RDS
```

### Google Integration
```
Test Steps:
1. After login, call Gmail endpoint
2. GET /api/gmail/inbox/{user_id}
3. Verify email list returns
4. Call Calendar endpoint
5. GET /api/calendar/events/{user_id}
6. Verify upcoming events return
```

---

## 🔍 Debugging Guide

### If Backend Won't Start

**Check ECS logs:**
```bash
aws logs tail /ecs/cortex-agent --follow
```

**Common issues:**
- Database connection: Check DATABASE_URL format
- Missing dependencies: Verify requirements.txt installed
- Port conflicts: ECS uses port 8000

### If OAuth Fails

**Check configuration:**
```bash
# Verify credentials in Terraform
cat terraform/terraform.tfvars | grep google

# Verify redirect URI in GCP console
# Should match: https://d3ouv9vt88djdf.cloudfront.net/api/auth/callback
```

### If Database Connection Fails

**Test connection:**
```bash
# Get RDS endpoint
aws rds describe-db-instances \
  --db-instance-identifier cortex-agent-db \
  --region us-east-1 \
  --query 'DBInstances[0].Endpoint'

# Try connecting (requires psql installed)
psql -h <RDS_ENDPOINT> -U postgres -d cortexdb
```

---

## 📊 Key Metrics to Monitor

### Performance
- Backend response time: < 2 seconds
- Database queries: < 500ms
- Frontend load: < 2 seconds

### Reliability
- Zero errors in CloudWatch logs
- All API endpoints returning 200/201
- Database connections stable

### User Experience
- OAuth login succeeds
- Chat messages display correctly
- Memory persistence works
- No UI errors in browser console

---

## 🎯 Submission Checklist (Day 9)

### Before Submission
- [ ] All tests pass
- [ ] No errors in CloudWatch logs
- [ ] OAuth flow works end-to-end
- [ ] Chat agent responds intelligently
- [ ] Memory extraction working
- [ ] Gmail/Calendar integration functional
- [ ] Frontend UI is clean and responsive
- [ ] Code is commented and clean

### Submission Package
- [ ] GitHub repo public and accessible
- [ ] All code pushed to `main` branch
- [ ] README with deployment instructions
- [ ] Architecture documentation
- [ ] Screenshots of:
  - [ ] AWS Console (ECS running)
  - [ ] GitHub Actions deployment
  - [ ] Chat interface
  - [ ] Memory working
  - [ ] OAuth flow

### Final Checklist
- [ ] CloudFront domain accessible
- [ ] Backend API responding
- [ ] Frontend loads without errors
- [ ] Complete user flow tested
- [ ] No hardcoded secrets in code
- [ ] Environment variables properly configured

---

## 🚀 Quick Commands Reference

```bash
# Check deployment status
aws ecs describe-services --cluster cortex-agent-cluster \
  --services cortex-agent-service --region us-east-1

# View backend logs
aws logs tail /ecs/cortex-agent --follow

# Get RDS connection string
aws rds describe-db-instances --db-instance-identifier cortex-agent-db \
  --region us-east-1 --query 'DBInstances[0].Endpoint'

# List ECR images
aws ecr list-images --repository-name cortex-agent-backend --region us-east-1

# Check CloudFront status
aws cloudfront list-distributions --query 'DistributionList.Items[0].Status'
```

---

## 📋 Success Criteria

✅ **MVP (Minimum):** Chat works with agent
✅ **Strong:** + Memory extraction + Google integration
✅ **Excellent:** + Clean UI + Deployed on AWS + Working OAuth
✅ **Outstanding:** All above + Early submission + CI/CD automation

**Current Status:** Outstanding ⭐⭐⭐⭐⭐

---

## ⏰ Timeline

```
Day 8 (Jan 20):  Full testing, fix issues, polish UI
Day 9 (Jan 21):  Final testing, screenshots, prepare submission
Submission (Jan 22): Submit by 11:59 PM for bonus points
Deadline (Jan 24): Hard deadline 11:59 PM
```

---

**Ready to deploy! 🎉**

Follow the deployment steps above and you'll be live in 15 minutes!
