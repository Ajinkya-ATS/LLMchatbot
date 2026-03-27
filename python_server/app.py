from app.__init__ import create_app
app = create_app()

if __name__ == '__main__':
    app.logger.info(f"Server running on port {app.config.get('PORT', 5001)}")
    app.logger.info(f"Ollama base URL: {app.config.get('OLLAMA_BASE_URL')}")
    app.run(host='0.0.0.0', port=app.config.get('PORT', 5001), debug=False, threaded=True)