#!/bin/bash
set -e

# Default values
VUS=2
DURATION="10s"
CASE=1

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --case)
      CASE="$2"
      shift 2
      ;;
    --vus)
      VUS="$2"
      shift 2
      ;;
    --duration)
      DURATION="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --case N        Case number (1=REST, 2=Strawberry, 3=Apollo) [default: 1]"
      echo "  --vus N         Number of virtual users [default: 2]"
      echo "  --duration S    Test duration (e.g., 10s, 1m) [default: 10s]"
      echo ""
      echo "Example:"
      echo "  $0 --case 1 --vus 5 --duration 30s"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Find the test script
SCRIPT_PATTERN="$PROJECT_ROOT/k6/case${CASE}-*.js"
SCRIPT=$(ls $SCRIPT_PATTERN 2>/dev/null | head -1)

if [ -z "$SCRIPT" ]; then
  echo "ERROR: No k6 script found for case $CASE"
  echo "Expected pattern: $SCRIPT_PATTERN"
  exit 1
fi

echo "Running k6 duration test:"
echo "  Case:     $CASE"
echo "  Script:   $(basename $SCRIPT)"
echo "  VUs:      $VUS"
echo "  Duration: $DURATION"
echo ""

K6_PROMETHEUS_RW_SERVER_URL=http://localhost:19090/api/v1/write \
K6_PROMETHEUS_RW_TREND_STATS="p(50),p(90),p(99),avg,min,max" \
k6 run \
  --out experimental-prometheus-rw \
  -e GATEWAY_URL=http://localhost:10000 \
  -e TEST_MODE=duration \
  -e VUS="$VUS" \
  -e DURATION="$DURATION" \
  -e CASE="$CASE" \
  "$SCRIPT"
