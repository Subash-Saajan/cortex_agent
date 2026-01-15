# Sentellent Hiring Challenge - Implementation Plan

**Deadline:** January 24th, 11:59 PM
**Target Submission:** January 22nd (2 days early for bonus)
**Budget:** ~$10-15/month AWS costs

---

## Project Overview

Build a **Personal Agentic AI Assistant** ("Chief of Staff") that:
- Authenticates users via Google OAuth
- Connects to Gmail & Calendar (Google Workspace)
- Uses Claude + LangGraph for intelligent chat
- Maintains dynamic memory of user preferences & extracted facts
- Fully deployed on AWS with Infrastructure as Code (Terraform) + CI/CD

---

## Architecture Decision: ECS Public IP (Optimized Choice)

### Why ECS Public IP over ALB?

| Factor | ECS Public IP | ALB |
|--------|---------------|-----|
| **Cost** | $0 extra | ~$16-22/month |
| **Terraform Complexity** | 5 lines | 50+ lines |
| **Setup Time** | 1 hour | 3+ hours |
| **HTTPS Handling** | Via CloudFront for OAuth | Native (but more config) |
| **Evaluation Impact** | Acceptable | Slight bonus (not worth the risk) |

**Decision Rationale:** Complexity is the enemy of deadlines. ECS Public IP proves AWS deployment skills with minimum risk.

---

## Final Tech Stack

```
Frontend:        Next.js (Static) → S3 + CloudFront (HTTPS)
Backend:         FastAPI + LangGraph + Claude
Agent Memory:    PostgreSQL + pgvector (vector search)
Infrastructure:  ECS Fargate (public IP) + RDS
DevOps:          Terraform + GitHub Actions CI/CD
Authentication:  Google OAuth (GCP)
```

---

## Cloud Architecture

```
┌────────────────────────────────────────────┐
│     CloudFront + S3 (Frontend + HTTPS)     │
│    Handles Google OAuth callback routing    │
│                  ~$1/month                  │
└──────────────────┬─────────────────────────┘
                   │ API calls (HTTP)
                   ▼
┌────────────────────────────────────────────┐
│    ECS Fargate Service (Public IP)         │
│   FastAPI + LangGraph + Claude Agent       │
│    (0.25 vCPU, 512MB memory)               │
│                ~$8-12/month                │
└──────────────────┬─────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────┐
│  RDS PostgreSQL (db.t3.micro) + pgvector   │
│         AWS Free Tier (12 months)          │
└────────────────────────────────────────────┘
```

**Total Monthly Cost:** ~$10-15

---

## Project Structure

```
CortexAgent/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── index.tsx          # Login page
│   │   │   ├── chat.tsx           # Main chat interface
│   │   │   └── api/
│   │   │       └── auth/          # OAuth callback handler
│   │   └── components/
│   ├── Dockerfile
│   ├── next.config.js
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app
│   │   ├── agent/
│   │   │   ├── graph.py           # LangGraph agent workflow
│   │   │   ├── tools.py           # Gmail, Calendar tools
│   │   │   └── memory.py          # Dynamic memory management
│   │   ├── api/
│   │   │   ├── routes.py          # Chat, Gmail, Calendar endpoints
│   │   │   └── auth.py            # Google OAuth
│   │   ├── services/
│   │   │   ├── gmail_service.py
│   │   │   ├── calendar_service.py
│   │   │   └── memory_service.py
│   │   ├── models/
│   │   │   └── schemas.py         # Pydantic models
│   │   └── db/
│   │       ├── database.py        # PostgreSQL + pgvector
│   │       └── migrations/        # Alembic migrations
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── terraform/
│   ├── main.tf                    # VPC, networking
│   ├── ecs.tf                     # ECS Fargate service
│   ├── rds.tf                     # PostgreSQL + pgvector
│   ├── s3_cloudfront.tf           # Frontend hosting
│   ├── ecr.tf                     # Docker registry
│   ├── variables.tf               # Input variables
│   ├── outputs.tf                 # Output values
│   ├── terraform.tfvars           # Configuration (local)
│   └── terraform.tfvars.example
│
├── .github/
│   └── workflows/
│       └── deploy.yml             # GitHub Actions CI/CD
│
├── docker-compose.yml             # Local development
├── IMPLEMENTATION_PLAN.md         # This file
└── README.md                       # Setup instructions
```

---

## Implementation Timeline (9 Days)

### Days 1-2: Foundation & Infrastructure Setup

**Goal:** Deploy "Hello World" agentic chat live on AWS

**Tasks:**
- [ ] Initialize Git repository
- [ ] Create FastAPI backend skeleton with basic `/chat` endpoint
- [ ] Create Next.js frontend skeleton with simple chat UI
- [ ] Write Dockerfiles (backend + frontend)
- [ ] Write docker-compose.yml for local development
- [ ] Create Terraform scripts:
  - [ ] VPC + Subnets
  - [ ] ECS Cluster + Fargate Service (public IP enabled)
  - [ ] RDS PostgreSQL (db.t3.micro)
  - [ ] S3 + CloudFront
  - [ ] ECR (Docker image registry)
  - [ ] Security groups & IAM roles
- [ ] Test locally with docker-compose
- [ ] Deploy to AWS manually (Terraform apply)
- [ ] Verify backend is accessible at public IP
- [ ] Verify frontend is accessible via CloudFront

**Deliverable:** Working "Hello World" chat on AWS + Terraform code

---

### Days 3-4: Core Agent & Memory

**Goal:** LangGraph agent with Claude + PostgreSQL memory

**Tasks:**
- [ ] Setup PostgreSQL connection in backend
- [ ] Create database schema:
  - [ ] `users` table
  - [ ] `memory_facts` table (extracted preferences/facts)
  - [ ] `chat_history` table
  - [ ] Setup pgvector extension + `memory_embeddings` for semantic search
- [ ] Implement LangGraph agent:
  - [ ] Basic Claude integration (chat endpoint)
  - [ ] Tool definitions for Gmail/Calendar (stub for now)
  - [ ] Memory extraction logic (extract facts from user messages)
  - [ ] Memory retrieval (RAG with pgvector)
- [ ] Create `/api/chat` endpoint:
  - [ ] Accept user message
  - [ ] Extract memory facts
  - [ ] Retrieve relevant past context
  - [ ] Call Claude with full context
  - [ ] Store response in DB
- [ ] Test agent memory:
  - [ ] Tell agent "I hate 9 AM meetings"
  - [ ] Verify it extracts and stores this
  - [ ] Ask later, verify it remembers

**Deliverable:** Working agent with dynamic memory on live AWS deployment

---

### Days 5-6: Google Integration

**Goal:** Google OAuth + Gmail/Calendar APIs

**Tasks:**

#### Google Cloud Setup
- [ ] Create GCP project
- [ ] Enable Gmail API + Calendar API
- [ ] Create OAuth 2.0 credentials (Web application)
- [ ] **CRITICAL:** Add `harisankar@sentellent.com` as Test User
- [ ] Set authorized redirect URI: `https://your-cloudfront-domain/api/auth/callback`

#### Backend: OAuth
- [ ] Implement `/api/auth/login` endpoint (generates Google OAuth URL)
- [ ] Implement `/api/auth/callback` endpoint (handles OAuth callback, exchanges code for tokens)
- [ ] Store refresh tokens securely in PostgreSQL (encrypted)
- [ ] Create JWT session tokens for frontend

#### Frontend: OAuth
- [ ] "Login with Google" button on homepage
- [ ] Redirect to backend login endpoint
- [ ] Handle OAuth callback from CloudFront (frontend routes to backend)
- [ ] Store JWT token in localStorage/cookie
- [ ] Redirect to chat page on successful login

#### Gmail Integration
- [ ] Create `GmailService` class to fetch emails via Gmail API
- [ ] Implement `/api/gmail/inbox` endpoint (fetch last 10 emails)
- [ ] Agent tool: `fetch_emails(count=10)` - returns email summaries
- [ ] Implement `/api/gmail/send` endpoint (send email via Gmail API)
- [ ] Agent tool: `send_email(to, subject, body)` - drafts and sends

#### Calendar Integration
- [ ] Create `CalendarService` class to fetch events via Calendar API
- [ ] Implement `/api/calendar/events` endpoint (fetch today's events)
- [ ] Agent tool: `get_calendar_events()` - returns event summaries
- [ ] Implement `/api/calendar/create` endpoint (create event)
- [ ] Agent tool: `create_event(title, time, duration)` - creates event

#### Backend: Add Tools to Agent
- [ ] Register Gmail tools in LangGraph agent
- [ ] Register Calendar tools in LangGraph agent
- [ ] Update agent logic to suggest actions (e.g., "reply to email", "check calendar")

**Deliverable:** Full Google integration + agent can read/send emails & manage calendar

---

### Days 7-8: Frontend & Polish

**Goal:** Production-ready frontend + full feature integration

**Tasks:**
- [ ] Frontend chat interface:
  - [ ] Display chat messages (user + agent)
  - [ ] Input field for user messages
  - [ ] Loading state while agent responds
  - [ ] Display agent actions (e.g., "Checking your inbox...")
- [ ] Frontend: Gmail view
  - [ ] Display inbox with email previews
  - [ ] "Reply" button that triggers agent
- [ ] Frontend: Calendar view
  - [ ] Display today's events
  - [ ] Create event button
- [ ] Frontend: User profile
  - [ ] Show logged-in user
  - [ ] Logout button
- [ ] Error handling & loading states throughout
- [ ] Mobile-friendly responsive design (clean, simple)
- [ ] Test full flow:
  - [ ] Login → Chat → Ask to check inbox → Agent fetches + summarizes
  - [ ] Ask agent to draft email → Agent respects memory (user style/context)
  - [ ] View calendar → Ask agent to schedule → Agent creates event

**Deliverable:** Functional, complete frontend integrated with all backend features

---

### Day 9: Testing, Polish & Early Submission

**Goal:** Submit 2 days before deadline for bonus points

**Tasks:**
- [ ] End-to-end testing:
  - [ ] Login flow (test with `harisankar@sentellent.com`)
  - [ ] Chat with memory persistence
  - [ ] Email read/send workflow
  - [ ] Calendar read/create workflow
  - [ ] Memory extraction from emails
- [ ] Verify CI/CD pipeline:
  - [ ] Push to main branch
  - [ ] GitHub Actions builds + deploys automatically
  - [ ] New deployment is live without manual intervention
- [ ] Take screenshots:
  - [ ] AWS Console showing ECS service running
  - [ ] RDS instance details
  - [ ] ECR images
  - [ ] GitHub Actions workflow passing
- [ ] Test from public internet (on someone else's network)
- [ ] Final bug fixes & polish
- [ ] **SUBMIT** by January 22nd (2 days early)

**Deliverable:** Complete, tested project submitted for evaluation

---

## CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      # Build & push Docker images to ECR
      - name: Build and push backend to ECR
        run: |
          docker build -t cortex-agent-backend:${{ github.sha }} ./backend
          aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com
          docker tag cortex-agent-backend:${{ github.sha }} ${{ secrets.ECR_REGISTRY }}/cortex-agent-backend:latest
          docker push ${{ secrets.ECR_REGISTRY }}/cortex-agent-backend:latest

      - name: Build and push frontend to ECR
        run: |
          docker build -t cortex-agent-frontend:${{ github.sha }} ./frontend
          docker tag cortex-agent-frontend:${{ github.sha }} ${{ secrets.ECR_REGISTRY }}/cortex-agent-frontend:latest
          docker push ${{ secrets.ECR_REGISTRY }}/cortex-agent-frontend:latest

      # Deploy with Terraform
      - name: Terraform Apply
        run: |
          cd terraform
          terraform init
          terraform apply -auto-approve
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      # Update ECS service with new image
      - name: Update ECS Service
        run: |
          aws ecs update-service \
            --cluster cortex-agent-cluster \
            --service cortex-agent-service \
            --force-new-deployment \
            --region us-east-1
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

---

## Key Files to Create

### 1. Dockerfile (Backend)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Dockerfile (Frontend)
```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Use next/image optimization
FROM node:18-alpine

WORKDIR /app

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
```

### 3. Terraform Main (main.tf)
```hcl
provider "aws" {
  region = var.aws_region
}

# VPC & Networking
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "cortex-agent-vpc" }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = { Name = "cortex-agent-public-subnet-${count.index + 1}" }
}

# Security Group for ECS
resource "aws_security_group" "ecs" {
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "cortex-agent-ecs-sg" }
}

# ECR (Docker Registry)
resource "aws_ecr_repository" "backend" {
  name                 = "cortex-agent-backend"
  image_tag_mutability = "MUTABLE"

  tags = { Name = "cortex-agent-backend" }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "cortex-agent-frontend"
  image_tag_mutability = "MUTABLE"

  tags = { Name = "cortex-agent-frontend" }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "cortex-agent-cluster"

  tags = { Name = "cortex-agent-cluster" }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/cortex-agent"
  retention_in_days = 7

  tags = { Name = "cortex-agent-logs" }
}

# IAM Role for ECS Task
resource "aws_iam_role" "ecs_task_role" {
  name = "cortex-agent-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "ecs_task_policy" {
  name   = "cortex-agent-ecs-task-policy"
  role   = aws_iam_role.ecs_task_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.ecs.arn}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "*"
      }
    ]
  })
}

# ECS Task Definition
resource "aws_ecs_task_definition" "backend" {
  family                   = "cortex-agent-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "cortex-agent-backend"
      image     = "${aws_ecr_repository.backend.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      environment = [
        {
          name  = "DATABASE_URL"
          value = "postgresql://${aws_rds_cluster_instance.db.username}:${var.db_password}@${aws_rds_cluster.db.endpoint}:5432/${aws_rds_cluster.db.database_name}"
        },
        {
          name  = "GOOGLE_CLIENT_ID"
          value = var.google_client_id
        },
        {
          name  = "GOOGLE_CLIENT_SECRET"
          value = var.google_client_secret
        },
        {
          name  = "CLAUDE_API_KEY"
          value = var.claude_api_key
        }
      ]
    }
  ])
}

# ECS Service
resource "aws_ecs_service" "backend" {
  name            = "cortex-agent-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  tags = { Name = "cortex-agent-service" }
}

data "aws_availability_zones" "available" {
  state = "available"
}
```

### 4. Terraform RDS (rds.tf)
```hcl
resource "aws_rds_cluster" "db" {
  cluster_identifier      = "cortex-agent-db"
  engine                  = "aurora-postgresql"
  engine_version          = "15.3"
  database_name           = "cortexdb"
  master_username         = "postgres"
  master_password         = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  skip_final_snapshot     = true
  deletion_protection     = false

  tags = { Name = "cortex-agent-db" }
}

resource "aws_rds_cluster_instance" "db" {
  cluster_identifier = aws_rds_cluster.db.id
  instance_class     = "db.t3.micro"
  engine              = aws_rds_cluster.db.engine
  engine_version      = aws_rds_cluster.db.engine_version
  publicly_accessible = true

  tags = { Name = "cortex-agent-db-instance" }
}

resource "aws_db_subnet_group" "main" {
  name       = "cortex-agent-db-subnet-group"
  subnet_ids = aws_subnet.public[*].id

  tags = { Name = "cortex-agent-db-subnet-group" }
}

resource "aws_security_group" "rds" {
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "cortex-agent-rds-sg" }
}
```

### 5. Terraform S3 + CloudFront (s3_cloudfront.tf)
```hcl
resource "aws_s3_bucket" "frontend" {
  bucket = "cortex-agent-frontend-${data.aws_caller_identity.current.account_id}"

  tags = { Name = "cortex-agent-frontend" }
}

resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_identity" "frontend" {
  comment = "OAI for cortex-agent frontend"
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudFrontAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.frontend.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })
}

resource "aws_cloudfront_distribution" "frontend" {
  origin {
    domain_name = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id   = "cortex-agent-s3"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.frontend.cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "cortex-agent-s3"

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = { Name = "cortex-agent-cloudfront" }
}

data "aws_caller_identity" "current" {}
```

### 6. FastAPI Main (backend/app/main.py)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

from .api import routes, auth
from .db import database

app = FastAPI(title="Cortex Agent API")

# CORS for CloudFront domain
origins = [
    "https://your-cloudfront-domain.cloudfront.net",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(routes.router, prefix="/api", tags=["chat"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Required Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://user:password@host:5432/dbname
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REDIRECT_URI=https://your-cloudfront-domain/api/auth/callback
CLAUDE_API_KEY=sk-xxx
JWT_SECRET=your-secret-key
BACKEND_URL=http://your-ecs-public-ip:8000
```

### Terraform (terraform.tfvars)
```
aws_region           = "us-east-1"
db_password          = "SecurePassword123!"
google_client_id     = "xxx.apps.googleusercontent.com"
google_client_secret = "xxx"
claude_api_key       = "sk-xxx"
```

---

## Testing Checklist

- [ ] Local development works with docker-compose
- [ ] Terraform apply runs without errors
- [ ] ECS task is healthy and public IP is accessible
- [ ] RDS instance is reachable from ECS
- [ ] CloudFront serves frontend over HTTPS
- [ ] Google OAuth login works (test with harisankar@sentellent.com)
- [ ] Chat endpoint responds with agent answers
- [ ] Gmail API integration works (fetch emails)
- [ ] Calendar API integration works (view events)
- [ ] Memory extraction stores facts in PostgreSQL
- [ ] Memory retrieval provides context to agent
- [ ] CI/CD pipeline deploys on push to main

---

## Submission Checklist

- [ ] GitHub repo contains all code (frontend + backend)
- [ ] Live URL is accessible and working
- [ ] Screenshots of AWS Console (ECS, RDS, ECR)
- [ ] Screenshots of CI/CD pipeline passing
- [ ] All environment variables configured
- [ ] harisankar@sentellent.com added as test user in GCP
- [ ] Submit by January 22nd (2 days early for bonus)

---

## Success Criteria

**Minimum (Phase 1):** Get a working chat agent deployed on AWS with Terraform + CI/CD
- This alone makes your submission competitive

**Strong (Phase 1 + 2):** Add Google OAuth + Gmail/Calendar integration
- Complete solution with all core features

**Excellent (Phase 1 + 2 + 3):** Add dynamic memory from emails
- Advanced implementation showing contextual intelligence

**Bonus:** Submit 2 days early + clean code + good engineering practices
- Early submission shows you ship fast (hiring signal)

---

## Resources & References

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [Claude API Docs](https://docs.anthropic.com/)
- [Google OAuth Setup](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Docs](https://developers.google.com/gmail/api)
- [Calendar API Docs](https://developers.google.com/calendar)
- [Terraform AWS Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [ECS with Terraform](https://docs.aws.amazon.com/ecs/latest/developerguide/task_definitions.html)
- [pgvector for PostgreSQL](https://github.com/pgvector/pgvector)
- [Next.js Export (Static)](https://nextjs.org/docs/advanced-features/static-html-export)

---

## Key Success Tips

1. **Start with infrastructure** - Terraform + CI/CD first, features second
2. **Deploy early** - Get "Hello World" live by Day 2, catch issues early
3. **Use AI to your advantage** - Claude, ChatGPT, GitHub Copilot for boilerplate code
4. **Test incrementally** - Each phase should be tested on live AWS
5. **Keep it simple** - No fancy UI, focus on clean code + working features
6. **Memory is the highlight** - Dynamic memory extraction + retrieval is what makes this special
7. **Submit early** - January 22nd gets you bonus points

---

**Last Updated:** January 15, 2026
**Status:** Ready to build
