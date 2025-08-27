#!/bin/bash

# BuddyAgents India - Stop All Services Script
# =============================================

echo "🛑 Stopping BuddyAgents India Services"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Change to backend directory
cd /home/jitesh/Desktop/Programing/Python/BuddyAgents/backend

# Function to stop service by PID file
stop_service() {
    local service_name="$1"
    local pid_file="${service_name,,}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${YELLOW}🛑 Stopping $service_name (PID: $pid)...${NC}"
            kill -TERM $pid
            sleep 2
            
            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                echo -e "${RED}🔧 Force stopping $service_name...${NC}"
                kill -KILL $pid
            fi
            echo -e "${GREEN}✅ $service_name stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  $service_name was not running${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}⚠️  No PID file found for $service_name${NC}"
    fi
}

# Function to stop services by port
stop_by_port() {
    local port="$1"
    local service_name="$2"
    
    local pids=$(lsof -ti:$port)
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}🛑 Stopping $service_name on port $port...${NC}"
        echo $pids | xargs kill -TERM
        sleep 2
        
        # Check if still running and force kill
        local remaining_pids=$(lsof -ti:$port)
        if [ ! -z "$remaining_pids" ]; then
            echo -e "${RED}🔧 Force stopping $service_name...${NC}"
            echo $remaining_pids | xargs kill -KILL
        fi
        echo -e "${GREEN}✅ $service_name stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  No process found on port $port${NC}"
    fi
}

echo -e "${BLUE}🛑 Stopping services by PID files...${NC}"

# Stop services by PID files
stop_service "Enhanced-Backend"
stop_service "Original-Backend" 
stop_service "Multi-Agent-App"
stop_service "Advanced-Dashboard"

echo ""
echo -e "${BLUE}🛑 Stopping services by ports (fallback)...${NC}"

# Stop services by ports (fallback)
stop_by_port "8002" "Enhanced Backend API"
stop_by_port "8000" "Original Backend API"
stop_by_port "8503" "Multi-Agent Streamlit App"
stop_by_port "8502" "Advanced Dashboard"

echo ""
echo -e "${BLUE}🧹 Cleaning up...${NC}"

# Clean up any remaining PID files
rm -f *.pid

# Optional: Clean up log files (uncomment if needed)
# rm -rf logs/*.log

echo ""
echo -e "${GREEN}✅ All BuddyAgents India services stopped successfully!${NC}"
echo ""
echo -e "${BLUE}💡 To start services again, run: ./start_all_services.sh${NC}"
