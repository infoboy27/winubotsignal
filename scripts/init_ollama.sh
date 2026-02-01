#!/bin/bash
# Initialize Ollama with Llama 3.1 8B model

set -e

echo "🚀 Initializing Ollama with Llama 3.1 8B model..."

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama is ready!"
        break
    fi
    echo "   Attempt $i/30..."
    sleep 2
done

# Pull Llama 3.1 8B model
echo "📥 Pulling Llama 3.1 8B model (this may take a while)..."
curl -X POST http://localhost:11434/api/pull -d '{
    "name": "llama3.1:8b"
}'

# Verify model is available
echo "🔍 Verifying model installation..."
MODELS=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"llama3.1:8b"' || echo "")

if [ -n "$MODELS" ]; then
    echo "✅ Llama 3.1 8B model successfully installed!"
    echo "📊 Available models:"
    curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g'
else
    echo "⚠️  Model installation may have failed. Please check manually."
    exit 1
fi

echo "🎉 Ollama initialization complete!"

