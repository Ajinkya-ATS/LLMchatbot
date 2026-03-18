import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, AlertCircle, Settings, Plus } from 'lucide-react';
import { sendMessage, uploadFile } from '../services/api';

const ChatInterface = ({ selectedModel, isConnected, onToggleModelSelector, showMessage }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const [thinkingMs, setThinkingMs] = useState(0);
  const thinkingIntervalRef = useRef(null);
  const thinkingStartRef = useRef(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);

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

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['text/csv', 'application/pdf'];
    if (!allowedTypes.includes(file.type)) {
      setError('Please upload a CSV or PDF file');
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('File size must be less than 10MB');
      return;
    }

    try {
      setUploadLoading(true);
      setError(null);
      const response = await uploadFile(file);
      setUploadedFile({
        name: file.name,
        fileId: response.fileId,
        type: file.type
      });
      if (showMessage) {
        showMessage(`${file.name} uploaded successfully`, 2000);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      setError(`Failed to upload file: ${error.message}`);
    } finally {
      setUploadLoading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

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

    const startTime = Date.now();
    // start thinking timer (in case the effect doesn't pick it up immediately)
    thinkingStartRef.current = startTime;
    setThinkingMs(0);
    if (thinkingIntervalRef.current) clearInterval(thinkingIntervalRef.current);
    thinkingIntervalRef.current = setInterval(() => {
      setThinkingMs(Date.now() - thinkingStartRef.current);
    }, 100);

    try {
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const response = await sendMessage({
        message: userMessage.content,
        model: selectedModel.name,
        conversationHistory,
        uploadedFile: uploadedFile ? {
          fileId: uploadedFile.fileId,
          fileName: uploadedFile.name,
          fileType: uploadedFile.type
        } : null
      });

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.response,
        timestamp: response.timestamp,
        model: response.model
      };


      // compute time taken
      const durationMs = Date.now() - startTime;
      assistantMessage.timeTaken = durationMs; // ms

      // stop thinking timer
      if (thinkingIntervalRef.current) {
        clearInterval(thinkingIntervalRef.current);
        thinkingIntervalRef.current = null;
      }
      setThinkingMs(durationMs);

      // show final toast: 'Thought for S.MS Seconds'
      if (showMessage) {
        showMessage(`Thought for ${(durationMs / 1000).toFixed(2)} Seconds`, 2000);
      }

      setMessages(prev => [...prev, assistantMessage]);
      // setUploadedFile(null); // Clear uploaded file after sending
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
    setUploadedFile(null);
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
                  {message.role !== 'user' && (
                    <>
                      <br />
                      Thought for {message.timeTaken != null && `${(message.timeTaken / 1000).toFixed(2)}s`}
                    </>
                  )}
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
                <span>Thinking {(thinkingMs / 1000).toFixed(2)}s</span>
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
          <div className="chat-input-wrapper">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.pdf"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
              disabled={uploadLoading || isLoading}
            />
            <button
              type="button"
              className="upload-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadLoading || isLoading}
              title="Upload CSV or PDF"
            >
              <Plus size={16} />
            </button>
            {uploadedFile && (
              <div className="uploaded-file-badge">
                {uploadedFile.name}
                <button
                  type="button"
                  className="remove-file-btn"
                  onClick={() => setUploadedFile(null)}
                  title="Remove file"
                >
                  ×
                </button>
              </div>
            )}
          </div>
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
