# FastAPI + Streamlit Application

This application consists of a FastAPI backend and a Streamlit frontend. Follow the instructions below to set up and run the application on your local machine or using Docker.
## Groq api key
```
Get your own free groq api key from: https://groq.com/
```
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

```bash
pip install -r requirements.txt
```

### 4. Run the Application

#### Start FastAPI Backend (Development Mode)

Open a new terminal, navigate to the project directory, activate your virtual environment, and run:

```bash
cd backend
fastapi dev main.py
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

## Environment Variables

Create a `.env` file in the root directory:

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
fastapi dev main.py

# Run Streamlit with debug mode
cd frontend
streamlit run app.py --logger.level debug
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
