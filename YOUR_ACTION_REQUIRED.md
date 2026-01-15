# 🚨 ACTION REQUIRED - DNS Validation

## Current Status

✅ **What's Done:**
- ALB created successfully
- ACM certificate created
- Target group ready
- HTTP listener ready

❌ **What Failed:**
- HTTPS listener needs validated certificate

## What YOU Need to Do (5 minutes)

### Step 1: Get Certificate Validation Record

Go to AWS Console:
1. Open https://console.aws.amazon.com/acm/home?region=us-east-1
2. You'll see certificate for `api.cortex.subashsaajan.site` with status "Pending validation"
3. Click on the certificate ID
4. Under "Domains", you'll see a section "CNAME name" and "CNAME value"

**OR** run this command:
```bash
aws acm describe-certificate \
  --certificate-arn "arn:aws:acm:us-east-1:045230654519:certificate/0adbe5e1-e880-4f6e-ae65-11f20e2f3b06" \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord'
```

### Step 2: Add DNS Record to Cloudflare

You'll get something like:
```json
{
  "Name": "_abc123def456.api.cortex.subashsaajan.site",
  "Type": "CNAME",
  "Value": "_xyz789.acm-validations.aws."
}
```

**Add to Cloudflare:**
1. Go to https://dash.cloudflare.com
2. Select domain: `subashsaajan.site`
3. Click "DNS" tab
4. Click "Add record"
5. Fill in:
   - **Type:** CNAME
   - **Name:** `_abc123def456.api` (the part before `.cortex.subashsaajan.site`)
   - **Target:** `_xyz789.acm-validations.aws.` (the full validation value)
   - **Proxy status:** DNS only (gray cloud, NOT orange)
6. Click "Save"

### Step 3: Wait for Validation (1-5 minutes)

The certificate will automatically validate once DNS propagates.

### Step 4: Re-run Terraform

Once the certificate shows "Issued" in AWS Console:

```bash
cd terraform
terraform apply -auto-approve
```

This will create the HTTPS listener and connect ECS to ALB.

### Step 5: Get ALB DNS Name

After terraform completes:
```bash
cd terraform
terraform output alb_dns_name
```

You'll get something like: `cortex-agent-alb-123456789.us-east-1.elb.amazonaws.com`

### Step 6: Add API CNAME to Cloudflare

1. Go back to Cloudflare DNS
2. Add another record:
   - **Type:** CNAME
   - **Name:** `api`
   - **Target:** `<the ALB DNS name from step 5>`
   - **Proxy status:** DNS only (gray cloud)
3. Save

### Step 7: Test Backend

Wait 2-3 minutes for DNS propagation, then:
```bash
curl https://api.cortex.subashsaajan.site/health
```

Expected: `{"status":"healthy","service":"cortex-agent-api"}`

---

## What I'll Do After You Complete This

Once your backend is accessible at `https://api.cortex.subashsaajan.site/health`:

1. Deploy frontend to Vercel
2. Configure Vercel custom domain
3. Add frontend CNAME to Cloudflare
4. Update Google OAuth settings
5. End-to-end testing
6. Help with final submission

---

## Quick Summary

**Your tasks (in order):**
1. ✋ Get ACM validation record from AWS Console
2. ✋ Add CNAME to Cloudflare
3. ⏳ Wait for validation (1-5 min)
4. ✋ Run `terraform apply` again
5. ✋ Get ALB DNS name
6. ✋ Add `api` CNAME to Cloudflare
7. ✋ Test: `curl https://api.cortex.subashsaajan.site/health`

**Time:** ~10 minutes total

Let me know when you're done or if you need help!
