import React, { useState, useEffect } from 'react';
import './App.css';
import ChatInterface from './components/ChatInterface';
import ModelSelector from './components/ModelSelector';
import Header from './components/Header';
import { getModels, checkHealth } from './services/api';

function App() {
  const [selectedModel, setSelectedModel] = useState(null);
  const [models, setModels] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isModelSelectorCollapsed, setIsModelSelectorCollapsed] = useState(false);

  useEffect(() => {
    initializeApp();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const initializeApp = async () => {
    try {
      setLoading(true);
      
      // Check Ollama connection
      const healthResponse = await checkHealth();
      setIsConnected(healthResponse.status === 'connected');
      
      // Load available models
      const modelsData = await getModels();
      setModels(modelsData);
      
      // Set default model if available
      if (modelsData.length > 0 && !selectedModel) {
        setSelectedModel(modelsData[0]);
      }
    } catch (error) {
      console.error('Failed to initialize app:', error);
      setIsConnected(false);
    } finally {
      setLoading(false);
    }
  };

  const handleModelChange = (model) => {
    setSelectedModel(model);
    // Auto-collapse the model selector after selection
    setIsModelSelectorCollapsed(true);
  };

  const toggleModelSelector = () => {
    setIsModelSelectorCollapsed(!isModelSelectorCollapsed);
  };

  if (loading) {
    return (
      <div className="app">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Initializing LLM Chatbot...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <Header 
        isConnected={isConnected} 
        onReconnect={initializeApp}
      />
      
      <div className="app-content">
        <ModelSelector
          models={models}
          selectedModel={selectedModel}
          onModelChange={handleModelChange}
          isConnected={isConnected}
          isCollapsed={isModelSelectorCollapsed}
          onToggle={toggleModelSelector}
        />
        
        <ChatInterface
          selectedModel={selectedModel}
          isConnected={isConnected}
          onToggleModelSelector={toggleModelSelector}
        />
      </div>
    </div>
  );
}

export default App;
