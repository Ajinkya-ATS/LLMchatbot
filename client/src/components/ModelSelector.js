import React from 'react';
import { HardDrive, Calendar, ChevronDown, ChevronUp, Settings } from 'lucide-react';

const ModelSelector = ({ models, selectedModel, onModelChange, isConnected, isCollapsed, onToggle }) => {
  if (!isConnected) {
    return (
      <div className="model-selector">
        <h2>Available Models</h2>
        <div className="error-message">
          Cannot load models. Please ensure Ollama is running and try reconnecting.
        </div>
      </div>
    );
  }

  return (
    <div className={`model-selector ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="model-selector-header" onClick={onToggle}>
        <div className="model-selector-title">
          <Settings size={18} />
          <span>
            {selectedModel ? `Selected: ${selectedModel.name}` : 'Select a Model'}
          </span>
        </div>
        <div className="model-selector-toggle">
          {isCollapsed ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
        </div>
      </div>
      
      {!isCollapsed && (
        <div className="models-grid">
          {models.map((model) => (
            <div
              key={model.id}
              className={`model-card ${selectedModel?.id === model.id ? 'selected' : ''}`}
              onClick={() => onModelChange(model)}
            >
              <div className="model-name">{model.name}</div>
              <div className="model-details">
                <div className="model-info">
                  <HardDrive size={14} />
                  <span className="model-size">{model.size}</span>
                </div>
                <div className="model-info">
                  <Calendar size={14} />
                  <span>Modified {model.modified}</span>
                </div>
                <div className="model-description">
                  {model.description}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ModelSelector;
