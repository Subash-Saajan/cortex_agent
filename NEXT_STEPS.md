# Next Steps - Adding ALB & Deploying to Vercel

**Goal:** Production-ready HTTPS deployment for Google OAuth compatibility

---

## Step 1: Add ALB to Terraform (~30-45 min)

### Files to Modify:

1. **terraform/alb.tf** (new file)
2. **terraform/main.tf** (update security groups)
3. **terraform/variables.tf** (add domain variable)
4. **terraform/outputs.tf** (output ALB DNS)

### What ALB Provides:

- HTTPS endpoint with ACM certificate
- Health checks for ECS tasks
- Stable DNS (doesn't change when task restarts)
- Standard port 443 (instead of 8000)
- Allows horizontal scaling

### Terraform Resources Needed:

```hcl
# 1. ACM Certificate (for api.cortex.subashsaajan.site)
resource "aws_acm_certificate" "backend"

# 2. ALB
resource "aws_lb" "backend"

# 3. Target Group (points to ECS tasks)
resource "aws_lb_target_group" "backend"

# 4. HTTPS Listener
resource "aws_lb_listener" "https"

# 5. Security Group for ALB
resource "aws_security_group" "alb"

# 6. Update ECS Security Group (allow traffic from ALB only)
```

---

## Step 2: Deploy Frontend to Vercel (~10-15 min)

### Process:

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click "New Project"
3. Import `Subash-Saajan/cortex_agent` repository
4. Select `frontend/` as root directory
5. Vercel auto-detects Next.js settings
6. Add environment variables:
   - `NEXT_PUBLIC_BACKEND_URL=https://api.cortex.subashsaajan.site`
   - `NEXT_PUBLIC_GOOGLE_CLIENT_ID=<your-client-id>`
7. Deploy

### Custom Domain Setup in Vercel:

1. Go to Project Settings → Domains
2. Add domain: `cortex.subashsaajan.site`
3. Vercel provides CNAME target (e.g., `cname.vercel-dns.com`)
4. Add this to Cloudflare DNS

---

## Step 3: Configure Cloudflare DNS (~10 min)

### DNS Records to Add:

```
Type: CNAME
Name: cortex
Target: <vercel-cname-target>
Proxy: OFF (gray cloud)
```

```
Type: CNAME
Name: api
Target: <alb-dns-name>.us-east-1.elb.amazonaws.com
Proxy: OFF (gray cloud)
```

**Important:** Turn OFF Cloudflare proxy (gray cloud) for both records during initial setup

---

## Step 4: Update Backend CORS (~5 min)

### File: backend/app/main.py

Update CORS origins to include new domains:

```python
origins = [
    "https://cortex.subashsaajan.site",      # Vercel production
    "http://localhost:3000",                  # Local dev
    "http://localhost:8000",                  # Local backend
]
```

Commit and push to trigger GitHub Actions deployment.

---

## Step 5: Update Google OAuth Redirect URIs (~5 min)

### In Google Cloud Console:

1. Go to APIs & Services → Credentials
2. Edit OAuth 2.0 Client
3. Update Authorized redirect URIs:
   ```
   https://cortex.subashsaajan.site/api/auth/callback
   http://localhost:3000/api/auth/callback
   ```
4. Save

---

## Step 6: Testing Checklist

### Manual Tests:

- [ ] Visit `https://cortex.subashsaajan.site` (should load)
- [ ] Visit `https://api.cortex.subashsaajan.site/health` (should return healthy)
- [ ] Click "Login with Google" (should redirect to Google)
- [ ] Complete OAuth flow (should redirect back and get JWT)
- [ ] Send a chat message (should get agent response)
- [ ] Check Gmail integration (fetch inbox)
- [ ] Check Calendar integration (view events)
- [ ] Tell agent a preference, refresh, verify it remembers

### Expected Results:

- ✅ All HTTPS (no mixed content warnings)
- ✅ OAuth redirects work smoothly
- ✅ Agent responds with context from memory
- ✅ Gmail and Calendar APIs accessible

---

## Cost Breakdown (Final)

| Resource | Daily Cost | 3-Day Demo Cost |
|----------|------------|-----------------|
| ECS Fargate | $0.33/day | $1.00 |
| ALB | $0.54/day | $1.62 |
| RDS (free tier) | $0.00 | $0.00 |
| ECR + misc | $0.07/day | $0.21 |
| **Total** | **~$0.94/day** | **~$2.83** |

**Vercel:** $0 (free tier)

---

## Timeline Estimate

| Task | Time | Status |
|------|------|--------|
| Write ALB Terraform | 20 min | ⏳ Pending |
| Apply Terraform | 5-10 min | ⏳ Pending |
| Deploy to Vercel | 10 min | ⏳ Pending |
| Configure DNS | 10 min | ⏳ Pending |
| Update CORS | 5 min | ⏳ Pending |
| Update OAuth URIs | 5 min | ⏳ Pending |
| Testing | 30-60 min | ⏳ Pending |
| **Total** | **~2 hours** | |

---

## Rollback Plan

If ALB causes issues:

1. Remove ALB resources from Terraform
2. `terraform apply` to destroy ALB
3. Keep using ECS public IP for demo
4. Document limitations in README

**But:** Google OAuth won't work without HTTPS, so ALB is recommended.

---

## After Submission

Once project is submitted (January 22):

```bash
cd terraform
terraform destroy -auto-approve
```

This will delete all AWS resources and stop charges.

**Keep:** GitHub repository, Vercel deployment (free tier)

---

## Questions to Resolve

1. Do you want to proceed with ALB now?
2. Do you have access to Cloudflare DNS settings?
3. Should we test locally first or go straight to production deployment?

---

**Next Command:** Ready to add ALB to Terraform when you confirm.
