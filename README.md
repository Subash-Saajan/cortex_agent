#  Cortex AI: Your Agentic Chief of Staff

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![LangGraph](https://img.shields.io/badge/Agent-LangGraph-orange?style=flat-square)](https://github.com/langchain-ai/langgraph)
[![AWS](https://img.shields.io/badge/Infrastructure-AWS-232F3E?style=flat-square&logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)
[![Gemini](https://img.shields.io/badge/AI-Gemini_2.0_Flash-blue?style=flat-square)](https://ai.google.dev/)

**Cortex** is a high-performance, agentic personal assistant designed to manage your professional and personal life autonomously. Deeply integrated with Google Workspace, it doesn't just "chat"—it executes workflows, manages schedules, and maintains a long-term semantic memory of your preferences.

---

##  Key Features

- ** Agentic Reasoning**: Powered by **LangGraph** and **Gemini 2.0 Flash**, the agent performs complex multi-step reasoning before acting.
- ** Workspace Mastery**: Native integration with **Gmail** and **Google Calendar**. Extract PDF data, manage threads, and schedule meetings relative to "next Tuesday".
- ** Semantic Long-Term Memory**: Uses **pgvector** to remember facts, preferences, and projects across conversations.
- ** Glassmorphism UI**: A premium, responsive interface featuring dynamic mesh backgrounds and real-time interaction states.
- ** User Profiles & Personalization**: Tailor the AI's communication style (e.g., "concise and technical" vs. "formal and polite").
- ** Safety First**: Mandatory "Human-in-the-loop" approval for emails and calendar event creation.

---

##  Architecture Overview

Cortex is built on a **ReAct (Reason + Act)** pattern. Instead of a linear flow, the agent operates in a graph-based cycle:

1.  **Ingest**: Receive user query + dynamic context (Time, Location).
2.  **Retrieve**: Semantic search via `pgvector` for relevant long-term memories.
3.  **Reason**: LLM decides if a tool (Gmail/Calendar) is needed.
4.  **Act**: Execute tool and observe result.
5.  **Refine**: Update status and respond to user.

---

##  Technical Stack

### **Backend**
- **Core**: FastAPI (Asynchronous)
- **AI Orchestration**: LangGraph (StateGraph)
- **Database**: PostgreSQL with `pgvector`
- **Integrations**: Google APIs (OAuth2, Gmail v1, Calendar v3)

### **Frontend**
- **Framework**: Next.js 14 (App Router)
- **Styling**: Vanilla CSS (Custom Glassmorphism system)
- **Real-time**: Axios-based polling and dynamic state management

### **Infrastructure**
- **Cloud**: AWS (ECS Fargate, RDS PostgreSQL, ALB)
- **IaC**: Terraform
- **CI/CD**: GitHub Actions

---

##  Getting Started

### 1. Prerequisites
- Docker & Docker Compose
- Google Cloud Platform Project (with Gmail/Calendar APIs enabled)
- Google API Key (for Gemini)

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/Subash-Saajan/cortex_agent.git
cd cortex_agent

# Configure Backend
cp backend/.env.example backend/.env
# Update backend/.env with your Google Credentials & DB URL

# Configure Frontend
cp frontend/.env.example frontend/.env
```

### 3. Local Deployment
```bash
docker-compose up --build
```
- Access Frontend: `http://localhost:3000`
- Access Backend API: `http://localhost:8000`

---

##  Security & Privacy

- **Row-Level Isolation**: Users can only access their own messages, memories, and workspace data.
- **Secure Auth**: Uses **Google OAuth 2.0** for identity and **JWT** for session management.
- **Data Sovereignty**: Implemented "Right to be Forgotten" logic—users can wipe all chat/memory data while keeping their configuration.

---

##  License
This project is licensed under the MIT License - see the `LICENSE` file for details.

---

*Built by Subash.*
