import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, AlertCircle, Settings } from 'lucide-react';
import { sendMessage } from '../services/api';

const ChatInterface = ({ selectedModel, isConnected, onToggleModelSelector }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [inputMessage]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!inputMessage.trim() || !selectedModel || isLoading || !isConnected) {
      return;
    }

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setError(null);

    try {
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const response = await sendMessage({
        message: userMessage.content,
        model: selectedModel.name,
        conversationHistory
      });

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.response,
        timestamp: response.timestamp,
        model: response.model
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      
      let errorMessage = 'Failed to send message. Please try again.';
      
      if (error.code === 'ECONNABORTED') {
        errorMessage = `Request timed out. The ${selectedModel.name} model is taking longer than expected. Try a smaller model or simpler question.`;
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      } else if (error.message.includes('timeout')) {
        errorMessage = `The ${selectedModel.name} model is taking too long to respond. Try a smaller model or check if Ollama is running properly.`;
      }
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setError(null);
  };

  if (!selectedModel) {
    return (
      <div className="chat-interface">
        <div className="no-model-selected">
          <Bot size={48} />
          <h3>Select a Model</h3>
          <p>Choose a model from the list above to start chatting</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="chat-model-info">
          <Bot size={20} />
          <span>{selectedModel.name}</span>
          <span className="model-size">({selectedModel.size})</span>
        </div>
        <div className="chat-header-actions">
          <button 
            className="toggle-model-btn"
            onClick={onToggleModelSelector}
            title="Change model"
          >
            <Settings size={16} />
            Change Model
          </button>
          {messages.length > 0 && (
            <button 
              className="clear-chat-btn"
              onClick={clearChat}
              title="Clear chat"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <Bot size={48} />
            <h3>Start a conversation</h3>
            <p>Ask me anything! I'm powered by {selectedModel.name}</p>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={`message ${message.role}`}>
              <div className="message-avatar">
                {message.role === 'user' ? <User size={16} /> : <Bot size={16} />}
              </div>
              <div className="message-content">
                <div className="message-text">{message.content}</div>
                <div className="message-meta">
                  {new Date(message.timestamp).toLocaleTimeString()}
                  {message.model && ` • ${message.model}`}
                </div>
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div className="message assistant">
            <div className="message-avatar">
              <Bot size={16} />
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span>Thinking</span>
                <div className="typing-dots">
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="error-message">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <form onSubmit={handleSendMessage} className="chat-input-form">
          <textarea
            ref={textareaRef}
            className="chat-input"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={`Message ${selectedModel.name}...`}
            disabled={!isConnected || isLoading}
            rows={1}
          />
          <button
            type="submit"
            className="send-button"
            disabled={!inputMessage.trim() || !isConnected || isLoading}
          >
            <Send size={16} />
            Send
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatInterface;
