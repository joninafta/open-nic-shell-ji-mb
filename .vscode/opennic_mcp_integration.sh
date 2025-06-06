#!/bin/bash
# OpenNIC MCP Server Integration Script
# Source this file in your shell profile or run it when working on the project

export OPENNIC_PROJECT_ROOT="/Users/jonafta/Dev/open-nic-shell-ji-mb"
export MCP_SERVER_PATH="/Users/jonafta/Dev/open-nic-mcp/build/index.js"

# Function to start MCP server if not running
start_mcp_server() {
    if ! pgrep -f "node.*index.js" > /dev/null; then
        echo "Starting OpenNIC MCP Server..."
        node "$MCP_SERVER_PATH" &
        sleep 2
        echo "MCP Server started on port 3000"
    else
        echo "MCP Server is already running"
    fi
}

# Function to call MCP tools directly
mcp_call() {
    local tool_name="$1"
    local args="$2"
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"method\": \"tools/call\", \"params\": {\"name\": \"$tool_name\", \"arguments\": $args}}" \
        http://localhost:3000 | jq '.'
}

# Convenient aliases
alias opennic-test-basic='mcp_call "run-filter-simulation" "{\"test_type\": \"basic\", \"debug\": true}"'
alias opennic-test-all='mcp_call "run-filter-simulation" "{\"test_type\": \"all\", \"debug\": true, \"waves\": true}"'
alias opennic-check-reqs='mcp_call "check-requirements-compliance" "{\"requirement_type\": \"all\"}"'
alias opennic-analyze='mcp_call "analyze-filter-code" "{\"analysis_type\": \"all\"}"'

# Auto-start MCP server when this script is sourced
start_mcp_server

echo "OpenNIC MCP integration loaded!"
echo "Available commands:"
echo "  opennic-test-basic   - Run basic filter tests"
echo "  opennic-test-all     - Run all filter tests with waveforms"
echo "  opennic-check-reqs   - Check requirements compliance"
echo "  opennic-analyze      - Analyze filter code"
echo "  mcp_call <tool> <args> - Call any MCP tool directly"
