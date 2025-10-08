#!/bin/bash
# Test VRL Parser with Docker and Show Validation Results

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🧪 Testing VRL Parser with Docker Validation          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running!${NC}"
    echo "Please start Docker and try again."
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker is running"
echo ""

# Check if test log exists
TEST_LOG="docker/vector_logs/test.log"
if [ ! -f "$TEST_LOG" ]; then
    echo -e "${YELLOW}⚠${NC}  No test log found. Creating one..."
    mkdir -p docker/vector_logs
    cat > "$TEST_LOG" << 'EOF'
<190>1 2025-09-16T09:42:55.454937+00:00 ma1-ipa-master dirsrv-errors - - - [16/Sep/2025:09:42:51.709023694 +0000] - ERR - ipa_sidgen_add_post_op - [file ipa_sidgen.c, line 128]: Missing target entry.
EOF
    echo -e "${GREEN}✓${NC} Created test log"
fi

echo -e "${BLUE}📋 Test Log Content:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat "$TEST_LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Clean up old output
rm -f docker/vector_output_new/*.json
mkdir -p docker/vector_output_new

echo -e "${BLUE}🚀 Starting Vector with VRL Parser...${NC}"
echo ""

# Run Vector with docker
cd docker

# Stop any running Vector containers
docker-compose down 2>/dev/null || true

# Start Vector and show output
echo -e "${YELLOW}Starting validation (Press Ctrl+C to stop)...${NC}"
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              VALIDATION OUTPUT (Real-time)                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Run with timeout to show results
timeout 10s docker-compose up 2>&1 | tee validation_output.log || true

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  VALIDATION RESULTS                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if output file was created
OUTPUT_FILE=$(ls -t vector_output_new/processed-logs-*.json 2>/dev/null | head -1)

if [ -f "$OUTPUT_FILE" ]; then
    echo -e "${GREEN}✓${NC} Parser ran successfully!"
    echo ""
    echo -e "${BLUE}📊 Parsed Output:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Pretty print JSON
    if command -v jq &> /dev/null; then
        cat "$OUTPUT_FILE" | jq .
    else
        cat "$OUTPUT_FILE" | python3 -m json.tool
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Count fields extracted
    FIELD_COUNT=$(cat "$OUTPUT_FILE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data))")
    echo -e "${GREEN}✓${NC} Fields extracted: ${FIELD_COUNT}"
    
    # Check for unparsed field
    if cat "$OUTPUT_FILE" | grep -q '"unparsed"'; then
        echo -e "${RED}⚠${NC}  WARNING: 'unparsed' field found - GROK pattern may not be matching!"
    else
        echo -e "${GREEN}✓${NC} No 'unparsed' field - GROK pattern matched successfully!"
    fi
    
    # Check for timestamp
    if cat "$OUTPUT_FILE" | grep -q '"@timestamp"'; then
        echo -e "${GREEN}✓${NC} Timestamp extracted"
    else
        echo -e "${YELLOW}⚠${NC}  No timestamp field"
    fi
    
else
    echo -e "${RED}❌ No output file created!${NC}"
    echo ""
    echo "Possible issues:"
    echo "  1. VRL syntax error"
    echo "  2. GROK pattern not matching"
    echo "  3. Docker/Vector configuration issue"
    echo ""
    echo "Check validation_output.log for details"
fi

# Clean up
docker-compose down 2>/dev/null || true

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                     TEST COMPLETE                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
