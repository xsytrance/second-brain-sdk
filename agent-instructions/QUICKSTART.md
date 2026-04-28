# Agent Quick-Start - Second Brain
## 30-Second Install
bash <(curl -fsSL https://raw.githubusercontent.com/xsytrance/second-brain-sdk/master/agent-instructions/bootstrap.sh)
echo 'export SECOND_BRAIN_SERVER_URL="http://100.104.159.48:8009"' >> ~/.bashrc
echo 'export SECOND_BRAIN_TOKEN="tok_GET_FROM_PRIME"' >> ~/.bashrc
source ~/.bashrc
## Verify
second-brain status
second-brain log heartbeat "agent up" --agent $(hostname)
curl -s "$SECOND_BRAIN_SERVER_URL/health"
## Troubleshoot
python3 ~/second-brain-sdk/agent-instructions/diagnostic.py
## Full Docs
- DEPLOY_GUIDE.md - comprehensive manual
- docs/ - technical reference
