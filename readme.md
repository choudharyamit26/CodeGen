# FastAPI + Streamlit Application

This application consists of a **FastAPI backend** and a **Streamlit frontend**. Follow the instructions below to set up and run the application locally or using Docker.

---

## 🔑 Groq API Key

Get your free Groq API key from: [https://groq.com/](https://groq.com/)

---

## 📁 Project Structure

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
├── start.sh
└── README.md
```

---

## 🖥️ Local Development Setup

### Prerequisites

- Python 3.8 or higher  
- `pip` (Python package installer)

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <project-directory>
```

### 2. Create and Activate Virtual Environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
# To deactivate:
deactivate
```

#### Linux / Ubuntu / macOS

```bash
python3 -m venv venv
source venv/bin/activate
# To deactivate:
deactivate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

#### Start FastAPI Backend (Development Mode)

```bash
cd backend
fastapi dev main.py
```

- API: [http://localhost:8000](http://localhost:8000)  
- Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)  
- Alternative docs: [http://localhost:8000/redoc](http://localhost:8000/redoc)

#### Start Streamlit Frontend

```bash
cd frontend
streamlit run app.py --server.port 8501
```

- Frontend: [http://localhost:8501](http://localhost:8501)

---

## 🐳 Docker Setup

### Prerequisites

- Docker installed on your machine

### Build and Run with Docker

#### Build the Docker image

```bash
docker build -t codegen-app .
```

#### Run the Docker container

##### Interactive Mode

```bash
docker run -p 8000:8000 -p 8501:8501 --env-file .env codegen-app
```

##### Detached Mode

```bash
docker run -d -p 8000:8000 -p 8501:8501 --env-file .env codegen-app
```

### Accessing the Application

- FastAPI backend: [http://localhost:8000](http://localhost:8000)  
- Streamlit frontend: [http://localhost:8501](http://localhost:8501)

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory:

```
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=your-secret-key
DEBUG=True
BACKEND_URL=http://localhost:8000
```

---

## 💡 Development Tips

### Hot Reload

- **FastAPI:** Use `--reload` flag  
- **Streamlit:** Automatically reloads on file save

### API Testing

- Use FastAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)  
- Or tools like Postman or `curl`

### Debugging

#### FastAPI

```bash
cd backend
fastapi dev main.py
```

#### Streamlit

```bash
cd frontend
streamlit run app.py --logger.level debug
```

---

## 🤝 Contributing

1. Fork the repository  
2. Create your feature branch:  
   `git checkout -b feature/amazing-feature`  
3. Commit your changes:  
   `git commit -m 'Add some amazing feature'`  
4. Push to the branch:  
   `git push origin feature/amazing-feature`  
5. Open a Pull Request