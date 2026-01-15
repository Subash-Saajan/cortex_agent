# Cortex Agent - Personal AI Assistant

A personal agentic AI assistant that integrates with Google Workspace (Gmail & Calendar) and uses Claude for intelligent decision-making.

## Project Structure

```
CortexAgent/
├── backend/               # FastAPI backend with LangGraph agent
├── frontend/              # Next.js frontend
├── terraform/             # AWS infrastructure as code
├── docker-compose.yml     # Local development setup
└── README.md
```

## Prerequisites

- Docker & Docker Compose
- Terraform
- Node.js 18+
- Python 3.11+
- AWS Account

## Local Development

### 1. Clone and Setup

```bash
git clone https://github.com/Subash-Saajan/cortex_agent.git
cd cortex_agent
```

### 2. Configure Environment Variables

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env with your actual values

# Frontend
cp frontend/.env.example frontend/.env
```

### 3. Start Local Services

```bash
docker-compose up --build
```

Services will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Database: localhost:5432

## AWS Deployment

### 1. Configure Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your actual values
```

### 2. Deploy to AWS

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply configuration
terraform apply
```

### 3. Deploy Docker Images to ECR

```bash
# Build and push backend
docker build -t cortex-agent-backend:latest ./backend
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
docker tag cortex-agent-backend:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/cortex-agent-backend:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/cortex-agent-backend:latest

# Build and push frontend
docker build -t cortex-agent-frontend:latest ./frontend
docker tag cortex-agent-frontend:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/cortex-agent-frontend:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/cortex-agent-frontend:latest
```

## Tech Stack

- **Frontend**: Next.js + React
- **Backend**: FastAPI + LangGraph + Claude
- **Database**: PostgreSQL + pgvector (vector embeddings)
- **Infrastructure**: AWS (ECS Fargate, RDS, S3, CloudFront)
- **IaC**: Terraform
- **CI/CD**: GitHub Actions

## Features (Roadmap)

- [ ] Day 1-2: "Hello World" chat on AWS
- [ ] Day 3-4: Dynamic memory with PostgreSQL
- [ ] Day 5-6: Google OAuth + Gmail/Calendar integration
- [ ] Day 7-8: Production-ready frontend
- [ ] Day 9: Testing & early submission

## Environment Variables

### Backend (.env)

```
DATABASE_URL=postgresql://user:password@host:5432/cortexdb
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REDIRECT_URI=https://your-cloudfront-domain/api/auth/callback
CLAUDE_API_KEY=sk-xxx
JWT_SECRET=your-secret-key
BACKEND_URL=http://your-ecs-public-ip:8000
```

### Frontend (.env.local)

```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## Testing

```bash
# Run backend tests
cd backend
pytest

# Run frontend tests
cd frontend
npm test
```

## Troubleshooting

### Docker Compose Issues
- Ensure ports 3000, 8000, 5432 are not in use
- Clear volumes: `docker-compose down -v`

### Terraform Issues
- Validate syntax: `terraform validate`
- Format code: `terraform fmt`
- Check state: `terraform state list`

### ECS Issues
- Check logs: `aws logs tail /ecs/cortex-agent --follow`
- Verify task: `aws ecs describe-tasks --cluster cortex-agent-cluster --tasks <task-arn>`

## Deployment to AWS

The infrastructure uses:
- **ECS Fargate** with public IP (no ALB needed)
- **RDS Aurora PostgreSQL** (db.t3.micro - free tier eligible)
- **S3 + CloudFront** for frontend hosting
- **ECR** for container registry

Estimated monthly cost: $10-15

## Contributing

Pull requests welcome. For major changes, please open an issue first to discuss.

## License

MIT
