# LLM Chatbot

A ChatGPT-like interface for interacting with locally hosted Large Language Models via Ollama. This application provides a modern, responsive web interface to chat with multiple LLMs running on your local machine.

## Features

- 🤖 **Multiple Model Support**: Chat with different LLMs including Gemma, Qwen, DeepSeek, and Mistral
- 💬 **Real-time Chat**: Seamless conversation experience with typing indicators
- 🎨 **Modern UI**: Clean, responsive design inspired by ChatGPT
- 🔄 **Model Switching**: Easy switching between different models
- 📱 **Mobile Friendly**: Responsive design that works on all devices
- 🔌 **Ollama Integration**: Direct integration with Ollama API

## Supported Models

The application is pre-configured to work with these models:

- **gemma3n:e4b** (7.5 GB) - Google Gemma 3N with enhanced capabilities
- **qwen2.5-coder:7b** (4.7 GB) - Qwen2.5 Coder optimized for programming tasks
- **deepseek-r1:8b** (5.2 GB) - DeepSeek R1 with reasoning capabilities
- **mistral:latest** (4.1 GB) - Mistral latest model for general purpose tasks

## Prerequisites

Before running this application, ensure you have:

1. **Node.js** (v16 or higher)
2. **Ollama** installed and running locally
3. The required LLM models installed in Ollama

### Installing Ollama

1. Visit [https://ollama.ai](https://ollama.ai)
2. Download and install Ollama for your operating system
3. Start the Ollama service

### Installing Models

Run these commands to install the required models:

```bash
# Install the models
ollama pull gemma3n:e4b
ollama pull qwen2.5-coder:7b
ollama pull deepseek-r1:8b
ollama pull mistral:latest
```

## Installation

1. **Clone or download this repository**

2. **Install dependencies for all parts of the application:**
   ```bash
   npm run install-all
   ```

   This will install dependencies for:
   - Root project (concurrently for running both servers)
   - Backend server (Express.js with Ollama integration)
   - Frontend client (React application)

## Running the Application

### Development Mode

To run both the backend and frontend in development mode:

```bash
npm run dev
```

This will start:
- Backend server on `http://localhost:5000`
- Frontend React app on `http://localhost:3000`

### Individual Services

You can also run the services individually:

**Backend only:**
```bash
npm run server
```

**Frontend only:**
```bash
npm run client
```

## Usage

1. **Start the application** using `npm run dev`
2. **Open your browser** and navigate to `http://localhost:3000`
3. **Ensure Ollama is running** - the app will show connection status
4. **Select a model** from the available options
5. **Start chatting** with your selected LLM!

## Configuration

### Environment Variables

You can customize the application using environment variables:

**Backend (.env file in server directory):**
```
PORT=5000
OLLAMA_BASE_URL=http://localhost:11434
```

**Frontend (.env file in client directory):**
```
REACT_APP_API_URL=http://localhost:5000/api
```

### Adding New Models

To add support for additional models:

1. **Install the model in Ollama:**
   ```bash
   ollama pull your-model-name
   ```

2. **Add the model to the server configuration** in `server/index.js`:
   ```javascript
   const AVAILABLE_MODELS = [
     // ... existing models
     {
       id: 'your-model-id',
       name: 'your-model-name',
       size: 'X.X GB',
       modified: 'X weeks ago',
       description: 'Your model description'
     }
   ];
   ```

## Troubleshooting

# Running Python Agents

This guide explains how to run the Python agents locally.

## Requirements
- Python **3.12**
- `pip` (included with Python)

Check your Python version:

```bash
python3.12 --version
```

## Setup

1. Navigate to the Python server directory:

```bash
cd python_server
```

2. Create a virtual environment:

```bash
python3.12 -m venv venv
```

3. Activate the virtual environment:

**macOS / Linux**
```bash
source venv/bin/activate
```

**Windows**
```bash
venv\Scripts\activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Agent

Start the Python server:

```bash
python app.py
```
### Setup and Database Initialization

Run the application containers in detached mode:

```bash
docker-compose up -d
```

Create a new database named LLMDB using your preferred SQL client or CLI.
Then initialize and apply Flask database migrations:

Create a .env file and add the following string into it:
```bash
DATABASE_URL=mssql+pyodbc://sa:YourStrongPassword123!@localhost:1433/LLMDB?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes
```

```bash
flask db init
flask db migrate -m "initial"
flask db upgrade
```


The Python agents should now be running.

### Common Issues

1. **"Cannot connect to Ollama"**
   - Ensure Ollama is running: `ollama serve`
   - Check if Ollama is accessible at `http://localhost:11434`

2. **"Model not found"**
   - Verify the model is installed: `ollama list`
   - Install the model: `ollama pull model-name`

3. **Port conflicts**
   - Backend runs on port 5000, frontend on port 3000
   - Change ports in the respective configuration files if needed

4. **CORS errors**
   - The backend is configured to allow CORS from the frontend
   - If you encounter CORS issues, check the CORS configuration in `server/index.js`

### Logs

- Backend logs are displayed in the terminal where you run `npm run server`
- Frontend logs are available in the browser's developer console
- Ollama logs can be viewed by running `ollama serve` in a separate terminal

## Project Structure

```
LLMChatbot/
├── client/                 # React frontend
│   ├── public/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API service layer
│   │   └── App.js         # Main App component
│   └── package.json
├── server/                 # Node.js backend
│   ├── index.js           # Express server with Ollama integration
│   └── package.json
├── package.json           # Root package.json
└── README.md
```

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this application.

## License

MIT License - feel free to use this project for personal or commercial purposes.
