#!/bin/bash

echo "🚀 Address Validation Platform - Startup Script"
echo "================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    echo "Please install Docker Compose from: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker is installed"
echo "✅ Docker Compose is installed"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "✅ .env file created"
else
    echo "✅ .env file exists"
fi

echo ""
echo "🏗️  Building and starting containers..."
echo "This may take 3-5 minutes on first run"
echo ""

# Start services
docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check health
echo "🔍 Checking system health..."
health_response=$(curl -s http://localhost:8000/api/v1/health/simple 2>/dev/null)

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ System is UP and RUNNING!"
    echo ""
    echo "📊 Access Points:"
    echo "   Frontend:  http://localhost"
    echo "   API Docs:  http://localhost:8000/api/docs"
    echo "   Health:    http://localhost:8000/api/v1/health"
    echo ""
    echo "📖 Quick Start:"
    echo "   1. Visit: http://localhost"
    echo "   2. Upload an Excel file with columns: "
    echo "   3. Click 'Start Validation'"
    echo ""
    echo "🛠️  Useful Commands:"
    echo "   View logs:    docker-compose logs -f"
    echo "   Stop:         docker-compose down"
    echo "   Restart:      docker-compose restart"
    echo ""
else
    echo ""
    echo "⚠️  Services are starting but not ready yet..."
    echo "Wait 30 seconds and try: http://localhost"
    echo ""
    echo "To view startup progress:"
    echo "   docker-compose logs -f"
    echo ""
fi

echo "🎉 Setup complete!"
