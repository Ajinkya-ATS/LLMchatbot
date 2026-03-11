import React from 'react';
import { Wifi, WifiOff, RotateCcw } from 'lucide-react';

const Header = ({ isConnected, onReconnect }) => {
  return (
    <div className="header">
      <h1>LLM Chatbot</h1>
      <div className="header-controls">
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? <Wifi size={16} /> : <WifiOff size={16} />}
          <span className="status-dot"></span>
          <span>{isConnected ? 'Connected to Ollama' : 'Disconnected'}</span>
        </div>
        {!isConnected && (
          <button className="reconnect-btn" onClick={onReconnect}>
            <RotateCcw size={16} />
            Reconnect
          </button>
        )}
      </div>
    </div>
  );
};

export default Header;
