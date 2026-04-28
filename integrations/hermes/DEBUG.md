# Plugin Debugging & Development Guide

If the Hermes plugin isn't logging events, follow this checklist.

## 1. Verify plugin discovery
```bash
cat ~/.hermes/config.yaml | grep -A5 plugins
# plugins.enabled should include: second_brain
```
Plugin path: `~/.hermes/plugins/second_brain/plugin.py`

## 2. Check Hermes startup logs
```bash
journalctl --user -u hermes -f
# Look for: [second_brain] plugin loaded
```

## 3. Verify brain exists
```bash
ls -la ~/.second-brain/
second-brain status
```

## 4. Test plugin in isolation
```bash
source ~/.hermes/hermes-agent/venv/bin/activate
python3 -c "
import sys; sys.path.insert(0, '/home/xsyprime/.hermes/plugins')
from second_brain import plugin
print('Hooks:', plugin.register().keys())
from second_brain import Brain; print('Brain OK')
"
```

## 5. Generate test conversation
Start new Hermes chat → send message → then:
```bash
second-brain events --limit 10
# Should see: session_started, llm_call, llm_response, session_ended
```

## 6. Enable debug logging
```bash
export HERMES_SECOND_BRAIN_DEBUG=1
# Restart Hermes — plugin prints session IDs and every event
```

## 7. Common issues
| Symptom | Fix |
|---------|-----|
| No events | Plugin not loaded → check `plugins.enabled` |
| Only session_started | Hook method name mismatch → check Hermes source for `run_conversation` vs `chat` |
| ImportError | Second Brain not in Hermes venv → `pip install second-brain` |
| DB locked | WAL enabled; avoid concurrent local+server writes to same DB |

