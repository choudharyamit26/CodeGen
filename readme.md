# FastAPI + Streamlit Application

This application consists of a FastAPI backend and a Streamlit frontend. Follow the instructions below to set up and run the application on your local machine or using Docker.

## Project Structure

```
project/
├── backend/
│   ├── main.py
│   └── ...
├── frontend/
│   ├── app.py
│   └── ...
├── requirements.txt
├── Dockerfile
└── README.md
```

## Local Development Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <project-directory>
```

### 2. Create and Activate Virtual Environment

#### Windows

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# To deactivate later
deactivate
```

#### Linux/Ubuntu

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# To deactivate later
deactivate
```

#### macOS

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# To deactivate later
deactivate
```

### 3. Install Dependencies

#### Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

#### Frontend Dependencies

```bash
cd ../frontend
pip install -r requirements.txt
```

**Note**: If you have a single `requirements.txt` file in the root directory containing all dependencies, install it from the root:

```bash
pip install -r requirements.txt
```

### 4. Run the Application

#### Start FastAPI Backend (Development Mode)

Open a new terminal, navigate to the project directory, activate your virtual environment, and run:

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The FastAPI backend will be available at:
- API: http://localhost:8000
- Interactive API docs: http://localhost:8000/docs
- Alternative API docs: http://localhost:8000/redoc

#### Start Streamlit Frontend

Open another terminal, navigate to the project directory, activate your virtual environment, and run:

```bash
cd frontend
streamlit run app.py --server.port 8501
```

The Streamlit frontend will be available at: http://localhost:8501

## Docker Setup

### Prerequisites

- Docker

### Single Container Approach

Since your application uses a single Dockerfile that runs both FastAPI and Streamlit in one container:

#### Build Docker Image

```bash
# Build the application image
docker build -t fastapi-streamlit-app .
```

#### Run Docker Container

```bash
# Run the container with both services
docker run -d \
  --name fastapi-streamlit-app \
  -p 8000:8000 \
  -p 8501:8501 \
  fastapi-streamlit-app

# Run in foreground to see logs
docker run --rm \
  --name fastapi-streamlit-app \
  -p 8000:8000 \
  -p 8501:8501 \
  fastapi-streamlit-app
```

#### Access the Application

- FastAPI Backend: http://localhost:8000
- FastAPI Docs: http://localhost:8000/docs
- Streamlit Frontend: http://localhost:8501

#### Stop and Remove Container

```bash
# Stop the container
docker stop fastapi-streamlit-app

# Remove the container
docker rm fastapi-streamlit-app
```

### Docker Management Commands

```bash
# View running containers
docker ps

# View all containers
docker ps -a

# View container logs
docker logs fastapi-streamlit-app

# Follow logs in real-time
docker logs -f fastapi-streamlit-app

# Execute commands inside the running container
docker exec -it fastapi-streamlit-app bash
```

## Environment Variables

Create a `.env` file in the root directory if needed:

```
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=your-secret-key
DEBUG=True
BACKEND_URL=http://localhost:8000
```

## Development Tips

### Hot Reload

- **FastAPI**: Use `--reload` flag for automatic reload on code changes
- **Streamlit**: Streamlit automatically reloads when you save changes to your files

### API Testing

- Use the FastAPI interactive docs at http://localhost:8000/docs
- Test API endpoints with tools like Postman or curl

### Debugging

#### Local Development
```bash
# Run FastAPI with debug logging
cd backend
uvicorn main:app --reload --log-level debug

# Run Streamlit with debug mode
cd frontend
streamlit run app.py --logger.level debug
```

#### Docker Debugging
```bash
# View container logs
docker logs fastapi-streamlit-app

# Follow logs in real-time
docker logs -f fastapi-streamlit-app

# Execute commands inside running container
docker exec -it fastapi-streamlit-app bash

# Check running processes inside container
docker exec fastapi-streamlit-app ps aux
```

## Troubleshooting

### Common Issues

1. **Port already in use**: Change the port numbers in the commands
2. **Permission denied**: Use `sudo` on Linux/macOS if needed
3. **Module not found**: Ensure virtual environment is activated and dependencies are installed
4. **Docker build fails**: Check Dockerfile syntax and ensure all files exist

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
