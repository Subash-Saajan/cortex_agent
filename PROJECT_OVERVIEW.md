# Cortex AI: Personal Chief of Staff - Project Overview

## 🌟 Executive Summary
**Cortex** is a sophisticated, agentic AI platform designed to act as a personal "Chief of Staff." Unlike traditional chatbots, Cortex is an autonomous agent that integrates deeply with a user's professional life through Google Workspace (Gmail, Calendar). It features a multi-layered memory system that allows it to maintain long-term context, learn user preferences, and execute complex workflows like drafting context-aware emails and managing schedules.

---

## 🛠️ Technology Stack

### 🔹 Frontend
- **Framework**: Next.js (React)
- **Styling**: Vanilla CSS with a modern "Glassmorphism" aesthetic and dynamic mesh backgrounds.
- **Interactions**: Real-time chat interface with interactive draft UIs for Emails and Calendar events.
- **State Management**: React Hooks (useState, useEffect) for sync-less updates.

### 🔹 Backend
- **Language**: Python 3.10+
- **Framework**: FastAPI (Asynchronous execution)
- **Database**: PostgreSQL with **pgvector** extension for semantic search.
- **ORM**: SQLAlchemy (Async)
- **Security**: Google OAuth 2.0 & JWT (JSON Web Tokens).

### 🔹 AI Intelligence (The "Brain")
- **Orchestration**: **LangGraph** (StateGraph) for managing cyclic agentic workflows.
- **LLM**: Google **Gemini 2.0 Flash** (utilizing high speed and tool-calling capabilities).
- **Embeddings**: Google `embedding-001` (768 dimensions) for semantic memory.
- **Memory System**: Hybrid approach using both structured SQL data and unstructured vector embeddings.

---

## 🧠 Core Architecture & Workflow

### 1. Agentic Logic (LangGraph)
Cortex uses a **ReAct (Reason + Act)** pattern implemented via LangGraph. 
- **Cycle**: The agent receives a message -> Consults memory -> Decides to call a tool (Gmail, Calendar, or Memory) -> Receives tool output -> Reasons again -> Responds.
- **Self-Correction**: The agent is programmed to show drafts to the user before performing destructive actions (like sending an email).

### 2. Multi-Layered Memory System
- **Profile Memory**: High-priority facts (Importance: 1.0) about the user's name, position, and AI personalization preferences.
- **Semantic Memory**: Uses **pgvector** to perform L2-distance similarity searches. When a user asks "What was that project I mentioned last week?", the agent generates an embedding and finds the most relevant "MemoryFact" from the database.
- **Hybrid Context**: Every message sent to the LLM includes a dynamically generated "Context Block" consisting of recent memories, current time, and personalization rules.

### 3. Google Workspace Integration
- **Gmail**: Deep integration supporting searching across all labels (Inbox, Sent, etc.), reading attachments (PDF extraction), and threading (keeping replies within existing conversations).
- **Calendar**: Automated scheduling with free/busy checks and relative time calculation (e.g., "Schedule a meeting for next Tuesday").

---

## 📋 Data Models (Schema)
The system operates on 5 core tables:
- **`users`**: Central hub for identity, OAuth tokens, and personalization strings.
- **`conversations`**: Groups chat history into logical threads with auto-generated titles.
- **`chat_messages`**: Durable storage for every interaction.
- **`memory_facts`**: Key takeaways extracted from conversations (categories: preference, habit, project, etc.).
- **`memory_embeddings`**: High-dimensional vectors linked to facts for semantic retrieval.

## 🌐 AWS Infrastructure Architecture

The project is deployed on **Amazon Web Services (AWS)** using a production-grade, scalable architecture managed via **Terraform (Infrastructure as Code)**.

### 🏗️ Component Breakdown

1. **Traffic Entry (Cloudflare + ALB)**:
   - **Cloudflare**: Acts as the first layer for DNS management, SSL/TLS encryption, and WAF (Web Application Firewall) protection.
   - **Application Load Balancer (ALB)**: Situated in public subnets, the ALB terminates SSL and routes traffic to the appropriate ECS services based on path (e.g., `/api/*` to Backend).

2. **Compute Layer (AWS ECS Fargate)**:
   - **Serverless Containers**: Both the Next.js frontend and FastAPI backend run on **AWS ECS with Fargate**. This removes the need to manage EC2 instances while providing auto-scaling capabilities.
   - **Task Definitions**: Each service has specific CPU/Memory allocations and environment variables (Secrets) managed via GitHub Actions.

3. **Data Layer (AWS RDS PostgreSQL)**:
   - **Managed Database**: A dedicated RDS instance running PostgreSQL 15. 
   - **Persistence & Extensions**: Configured with the `pgvector` extension for AI semantic search and automated daily backups.

4. **Network & Security (VPC)**:
   - **Virtual Private Cloud (VPC)**: Segregated into Public and Private subnets.
   - **Security Groups**: 
     - *ALB Group*: Allows HTTP/HTTPS from Cloudflare IPs.
     - *ECS Group*: Only allows traffic from the ALB Security Group.
     - *DB Group*: Only allows inbound traffic on port 5432 from the ECS Security Group (ensuring the DB is never exposed to the public internet).

### 🔄 Deployment Pipeline (CI/CD)
- **GitHub Actions**: Triggered on `push` to `main`.
- **Workflow**:
  1. Build Docker images.
  2. Push to **Amazon ECR** (Elastic Container Registry).
  3. Update **ECS Service** with the new Task Definition.
  4. Automatic DB migrations run during the container startup sequence.

---

## 🚀 Key Features to Highlight in an Interview

### ✅ Adaptive Personalization
Users can define an "AI Personalization" string (e.g., *"Be extremely concise and use technical terms"*). This is injected into the system prompt, ensuring the AI's "personality" shifts per user.

### ✅ Privacy & Data Control
Implemented a granular cleanup system. Users can clear chat history or perform a "Deep Wipe," which deletes conversations/messages but intelligently preserves the core profile and AI personalization settings.

### ✅ Automated Migrations
The backend features a self-healing database layer. On startup, it checks the PostgreSQL schema and automatically adds missing columns or extensions (like `vector`), ensuring zero-downtime deployments.

### ✅ Smart Drafting
Cortex doesn't just send emails; it generates a **Shared State Draft**. The AI produces a specific block format (`--- DRAFT START ---`) which the frontend intercepts to display an editable UI, bridging the gap between AI autonomy and user control.

---

## 🏗️ Deployment & Infrastructure
- **Containerization**: Fully Dockerized (Postgres, Backend, Frontend).
- **Orchestration**: AWS ECS (Elastic Container Service) with Load Balancers.
- **CDN**: Cloudflare for SSL/TLS and global edge caching.
- **CI/CD**: GitHub Actions for automated testing and deployment to AWS.

---

## ❓ Potential Interview Questions

**Q: How do you handle long-term memory without blowing up the context window?**
> A: We use a Retrieval Augmented Generation (RAG) approach. We don't send every message ever sent; instead, we use pgvector to retrieve only the top 5-10 most relevant "facts" based on the current user query.

**Q: Why use LangGraph instead of a simple OpenAI chain?**
> A: LangGraph allows for "cycles." A Chief of Staff often needs to perform multiple steps (e.g., check calendar -> search email -> update memory) before responding. LangGraph treats these as nodes in a graph, allowing the agent to loop until the task is complete.

**Q: How do you ensure the user's data is secure when using Google API?**
> A: We use Google OAuth with restricted scopes. Refresh tokens are stored encrypted in the database, and we implement a custom JWT-based Auth layer to ensure one user can never access another user's emails or memories.
