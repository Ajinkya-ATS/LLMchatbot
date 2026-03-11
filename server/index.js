const express = require('express');
const cors = require('cors');
const axios = require('axios');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5001;

// Middleware
app.use(cors());
app.use(express.json());

// Ollama API base URL
const OLLAMA_BASE_URL = process.env.OLLAMA_BASE_URL || 'http://localhost:11434';

// Predefined models with their details
const AVAILABLE_MODELS = [
  {
    id: 'gpt-oss-20b',
    name: 'gpt-oss:20b',
    size: '13 GB',
    modified: '1 day ago',
    description: 'GPT-OSS 20B model - Large open source language model'
  },
  {
    id: '15cb39fd9394',
    name: 'gemma3n:e4b',
    size: '7.5 GB',
    modified: '6 weeks ago',
    description: 'Google Gemma 3N model with enhanced capabilities'
  },
  {
    id: 'dae161e27b0e',
    name: 'qwen2.5-coder:7b',
    size: '4.7 GB',
    modified: '2 months ago',
    description: 'Qwen2.5 Coder model optimized for programming tasks'
  },
  {
    id: '6995872bfe4c',
    name: 'deepseek-r1:8b',
    size: '5.2 GB',
    modified: '2 months ago',
    description: 'DeepSeek R1 model with reasoning capabilities'
  },
  {
    id: 'f974a74358d6',
    name: 'mistral:latest',
    size: '4.1 GB',
    modified: '3 months ago',
    description: 'Mistral latest model for general purpose tasks'
  }
];

// Routes

// Get available models
app.get('/api/models', (req, res) => {
  res.json(AVAILABLE_MODELS);
});

// Check if Ollama is running
app.get('/api/health', async (req, res) => {
  try {
    const response = await axios.get(`${OLLAMA_BASE_URL}/api/tags`);
    res.json({ 
      status: 'connected', 
      ollamaVersion: response.data?.version || 'unknown',
      availableModels: response.data?.models || []
    });
  } catch (error) {
    res.status(500).json({ 
      status: 'disconnected', 
      error: 'Cannot connect to Ollama. Please ensure Ollama is running on localhost:11434'
    });
  }
});

// Chat with selected model
app.post('/api/chat', async (req, res) => {
  const { message, model, conversationHistory = [] } = req.body;

  if (!message || !model) {
    return res.status(400).json({ error: 'Message and model are required' });
  }

  try {
    // Prepare messages for the API with a system prompt for natural conversation
    const systemPrompt = {
      role: 'system',
      content: 'You are a helpful AI assistant. Respond naturally and conversationally, like a human would in a casual chat. Keep responses concise, friendly, and conversational. Avoid excessive formatting, numbered lists, bullet points, or markdown unless specifically requested. Just talk naturally like you would to a friend.'
    };

    const messages = [
      systemPrompt,
      ...conversationHistory,
      {
        role: 'user',
        content: message
      }
    ];

    const response = await axios.post(`${OLLAMA_BASE_URL}/api/chat`, {
      model: model,
      messages: messages,
      stream: false
    }, {
      timeout: 120000 // 2 minute timeout for large models
    });

    // Clean up the response
    let cleanResponse = response.data.message.content;
    
    // Remove common prefixes that models sometimes add
    cleanResponse = cleanResponse.replace(/^(Assistant:|AI:|Bot:)\s*/i, '');
    cleanResponse = cleanResponse.replace(/^(I am an AI|I am an artificial intelligence).*?How can I help you today\?/i, '');
    
    // Convert numbered lists to more natural text
    cleanResponse = cleanResponse.replace(/\n\d+\.\s*/g, '\n• ');
    cleanResponse = cleanResponse.replace(/^\d+\.\s*/gm, '• ');
    
    // Remove excessive whitespace and line breaks
    cleanResponse = cleanResponse.replace(/\n{3,}/g, '\n\n');
    cleanResponse = cleanResponse.trim();

    res.json({
      response: cleanResponse,
      model: model,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Chat error:', error.message);
    
    if (error.code === 'ECONNREFUSED') {
      res.status(500).json({ 
        error: 'Cannot connect to Ollama. Please ensure Ollama is running and the model is available.' 
      });
    } else if (error.response?.status === 404) {
      res.status(404).json({ 
        error: `Model '${model}' not found. Please ensure the model is installed in Ollama.` 
      });
    } else {
      res.status(500).json({ 
        error: error.response?.data?.error || 'An error occurred while processing your request.' 
      });
    }
  }
});

// Pull/install a model
app.post('/api/models/pull', async (req, res) => {
  const { modelName } = req.body;

  if (!modelName) {
    return res.status(400).json({ error: 'Model name is required' });
  }

  try {
    const response = await axios.post(`${OLLAMA_BASE_URL}/api/pull`, {
      name: modelName,
      stream: false
    });

    res.json({
      success: true,
      message: `Model ${modelName} pulled successfully`,
      details: response.data
    });

  } catch (error) {
    console.error('Pull model error:', error.message);
    res.status(500).json({ 
      error: error.response?.data?.error || 'Failed to pull model' 
    });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Ollama base URL: ${OLLAMA_BASE_URL}`);
});
