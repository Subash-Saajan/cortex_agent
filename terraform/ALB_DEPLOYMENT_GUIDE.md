# ALB Deployment Guide

## What We Added

1. **terraform/alb.tf** - Complete ALB configuration
   - ALB security group
   - Application Load Balancer
   - Target Group for ECS
   - ACM Certificate for `api.cortex.subashsaajan.site`
   - HTTPS Listener (port 443)
   - HTTP Listener (redirects to HTTPS)

2. **terraform/main.tf** - Updated ECS integration
   - ECS security group now only allows traffic from ALB
   - ECS service connected to ALB target group
   - Added dependency on HTTPS listener

3. **terraform/outputs.tf** - Added ALB outputs
   - ALB DNS name
   - ALB Zone ID
   - ACM certificate ARN
   - ACM certificate validation records

4. **backend/app/main.py** - Updated CORS
   - Added `https://cortex.subashsaajan.site` to allowed origins

---

## Deployment Steps

### Step 1: Validate DNS Setup in Cloudflare First

Before running Terraform, you need to add the ACM certificate validation record.

**Important:** ACM certificate requires DNS validation BEFORE Terraform can complete.

### Step 2: Run Terraform Plan

```bash
cd terraform
terraform plan
```

This will show you what will be created:
- ALB security group
- Application Load Balancer
- Target Group
- ACM Certificate (pending validation)
- HTTPS Listener
- HTTP Listener
- Modified ECS security group
- Modified ECS service

### Step 3: Apply Terraform (Partial - Will Pause)

```bash
terraform apply
```

**Expected Behavior:**
- Terraform will create the ACM certificate
- It will **pause** waiting for DNS validation
- You'll see output like: "Still creating... [10s elapsed]"

### Step 4: Add DNS Validation Record to Cloudflare

While Terraform is waiting, check the validation requirements:

```bash
# In another terminal
terraform output acm_certificate_validation_options
```

This will show you something like:
```json
{
  "domain_name" = "api.cortex.subashsaajan.site"
  "resource_record_name" = "_abc123.api.cortex.subashsaajan.site"
  "resource_record_type" = "CNAME"
  "resource_record_value" = "_xyz456.acm-validations.aws."
}
```

**Add this record to Cloudflare:**
1. Go to Cloudflare DNS settings
2. Add CNAME record:
   - Type: CNAME
   - Name: `_abc123.api` (without the full domain)
   - Target: `_xyz456.acm-validations.aws.`
   - Proxy: OFF (gray cloud)

### Step 5: Wait for Certificate Validation

Once you add the DNS record:
- ACM will detect it (takes 1-5 minutes)
- Terraform will continue automatically
- The rest of the resources will be created

### Step 6: Get ALB DNS Name

After Terraform completes:

```bash
terraform output alb_dns_name
```

Example output: `cortex-agent-alb-1234567890.us-east-1.elb.amazonaws.com`

### Step 7: Add ALB CNAME to Cloudflare

Add the backend API CNAME:
1. Go to Cloudflare DNS settings
2. Add CNAME record:
   - Type: CNAME
   - Name: `api`
   - Target: `<alb-dns-name from step 6>`
   - Proxy: OFF (gray cloud)

### Step 8: Test the ALB Endpoint

Wait 2-3 minutes for DNS propagation, then test:

```bash
curl https://api.cortex.subashsaajan.site/health
```

Expected response:
```json
{"status":"healthy","service":"cortex-agent-api"}
```

### Step 9: Commit and Push Changes

```bash
git add .
git commit -m "Add ALB for HTTPS backend endpoint

- Add Application Load Balancer with ACM certificate
- Update ECS security group to only allow ALB traffic
- Connect ECS service to ALB target group
- Update CORS for new domain
"
git push
```

This will trigger GitHub Actions to rebuild and redeploy the backend.

---

## Troubleshooting

### Certificate Validation Stuck

**Problem:** Terraform stuck on "Still creating... aws_acm_certificate_validation"

**Solution:**
1. Verify DNS record is correctly added to Cloudflare
2. Make sure Proxy is OFF (gray cloud)
3. Wait up to 10 minutes
4. Check AWS Console → Certificate Manager to see validation status

### ALB Health Checks Failing

**Problem:** Target group shows unhealthy targets

**Solution:**
1. Check ECS task is running: `aws ecs list-tasks --cluster cortex-agent-cluster`
2. Verify security group allows traffic from ALB
3. Check CloudWatch logs for errors
4. Verify health check path `/health` returns 200

### HTTPS Not Working

**Problem:** `curl https://api.cortex.subashsaajan.site/health` fails

**Solution:**
1. Verify DNS CNAME is correct: `dig api.cortex.subashsaajan.site`
2. Check certificate is validated in AWS Console
3. Wait 5-10 minutes for DNS propagation
4. Try HTTP first: `curl http://api.cortex.subashsaajan.site/health` (should redirect)

---

## Cost Impact

**New Monthly Costs:**
- ALB: ~$16.20/month ($0.0225/hour)
- ALB LCU: ~$0.50-2/month (very low for demo traffic)

**Total New Cost:** ~$16-18/month

**For 3-day demo:** ~$1.60-1.80

---

## Rollback Plan

If ALB causes issues:

```bash
cd terraform

# Remove ALB resources
rm alb.tf

# Revert ECS security group and service changes
git checkout main.tf

# Apply changes
terraform apply
```

This will destroy the ALB and revert to public IP setup.

---

## Next Steps After ALB Deployment

1. Deploy frontend to Vercel
2. Configure Vercel custom domain
3. Update Google OAuth redirect URIs
4. End-to-end testing
5. Submit project

---

## DNS Records Summary

After completing all steps, you should have these DNS records in Cloudflare:

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| CNAME | `_abc123.api` | `_xyz456.acm-validations.aws.` | OFF |
| CNAME | `api` | `cortex-agent-alb-xxx.us-east-1.elb.amazonaws.com` | OFF |
| CNAME | `cortex` | `cname.vercel-dns.com` | OFF |

---

**Ready to deploy!** Run `terraform plan` to see the changes.
