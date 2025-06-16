# Grand Central Station

A unified messaging platform for managing conversations across multiple services.

## Features

- Web scraping/API integration for multiple messaging platforms
- AI-powered automatic responses with per-chat configuration
- Rich chat interface with grouping and filtering
- Docker support for easy deployment

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React with TypeScript
- **Database**: PostgreSQL
- **Task Queue**: Celery with Redis
- **Container**: Docker & Docker Compose

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis
- Docker (optional)

### Local Development

1. Clone the repository
2. Set up environment variables (see `.env.example`)
3. Install dependencies and run migrations
4. Start the development servers

Detailed setup instructions coming soon.

## Project Structure

```
grand-central-station/
├── backend/          # FastAPI backend
├── frontend/         # React frontend
├── docker/          # Docker configuration
├── scripts/         # Utility scripts
└── docs/           # Documentation
```