#!/bin/bash

# BuddyAgents India - Complete Multi-Agent System Startup Script
# ==============================================================

echo "🚀 Starting BuddyAgents India - Complete Multi-Agent System"
echo "==========================================================="

# Change to backend directory
cd /home/jitesh/Desktop/Programing/Python/BuddyAgents/backend

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Setting up environment...${NC}"

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${YELLOW}⚠️  Port $1 is already in use${NC}"
        return 1
    else
        return 0
    fi
}

# Function to start service in background
start_service() {
    local command="$1"
    local service_name="$2"
    local port="$3"
    local log_file="$4"
    
    echo -e "${BLUE}🚀 Starting $service_name on port $port...${NC}"
    
    if check_port $port; then
        nohup $command > $log_file 2>&1 &
        local pid=$!
        echo $pid > "${service_name,,}.pid"
        echo -e "${GREEN}✅ $service_name started (PID: $pid)${NC}"
        sleep 2
    else
        echo -e "${YELLOW}⚠️  $service_name port $port already in use, skipping...${NC}"
    fi
}

# Create logs directory
mkdir -p logs

echo -e "${BLUE}📡 Starting Backend Services...${NC}"

# 1. Start Enhanced Multi-Agent Backend API (Port 8002)
start_service "uv run python enhanced_multi_agent_backend.py" "Enhanced-Backend" "8002" "logs/enhanced_backend.log"

# 2. Start Original FastAPI Backend (Port 8000) 
start_service "uv run python app/main.py" "Original-Backend" "8000" "logs/original_backend.log"

echo -e "${BLUE}🖥️  Starting Frontend Services...${NC}"

# 3. Start Multi-Agent Streamlit App (Port 8503)
start_service "uv run streamlit run multi_agent_app.py --server.port 8503" "Multi-Agent-App" "8503" "logs/multi_agent_app.log"

# 4. Start Advanced Dashboard (Port 8502)
start_service "uv run streamlit run advanced_dashboard.py --server.port 8502" "Advanced-Dashboard" "8502" "logs/advanced_dashboard.log"

echo ""
echo -e "${GREEN}🎉 All services started successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Service Overview:${NC}"
echo -e "   🔗 Multi-Agent App:        ${YELLOW}http://localhost:8503${NC}"
echo -e "   🔗 Advanced Dashboard:     ${YELLOW}http://localhost:8502${NC}" 
echo -e "   🔗 Enhanced Backend API:   ${YELLOW}http://localhost:8002${NC}"
echo -e "   🔗 Original Backend API:   ${YELLOW}http://localhost:8000${NC}"
echo ""
echo -e "${BLUE}🏗️  Architecture Overview:${NC}"
echo -e "   👥 Three AI Agents: Mitra (Friend), Guru (Mentor), Parikshak (Interviewer)"
echo -e "   🇮🇳 Cultural Intelligence: Regional adaptation, Hindi/English support"
echo -e "   💬 Real-time Communication: WebSocket + HTTP APIs"
echo -e "   🎤 Voice Features: Murf AI TTS integration"
echo -e "   📊 Session Management: SQLite database with conversation history"
echo -e "   🧠 RAG System: ChromaDB vector storage for contextual memory"
echo ""
echo -e "${BLUE}🔍 API Endpoints:${NC}"
echo -e "   POST ${YELLOW}http://localhost:8002/api/agent/chat${NC} - Chat with agents"
echo -e "   GET  ${YELLOW}http://localhost:8002/api/agent/personalities${NC} - Get agent info"
echo -e "   WS   ${YELLOW}ws://localhost:8002/ws/agent/{agent_type}${NC} - Real-time chat"
echo -e "   GET  ${YELLOW}http://localhost:8002/health${NC} - Health check"
echo ""
echo -e "${BLUE}📁 Log Files:${NC}"
echo -e "   📄 Enhanced Backend: logs/enhanced_backend.log"
echo -e "   📄 Original Backend: logs/original_backend.log"
echo -e "   📄 Multi-Agent App: logs/multi_agent_app.log" 
echo -e "   📄 Advanced Dashboard: logs/advanced_dashboard.log"
echo ""
echo -e "${GREEN}🎯 Ready to use! Open the Multi-Agent App at http://localhost:8503${NC}"
echo ""
echo -e "${BLUE}💡 Usage Guide:${NC}"
echo -e "   1. Set up your user profile in the sidebar"
echo -e "   2. Choose from Global Agent Selector or individual agent pages"
echo -e "   3. Configure cultural preferences (region, languages)"
echo -e "   4. Enable voice/video features in settings"
echo -e "   5. Start chatting with your AI companions!"
echo ""
echo -e "${YELLOW}🛑 To stop all services, run: ./stop_services.sh${NC}"
