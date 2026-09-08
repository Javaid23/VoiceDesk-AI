# Support Agent – Voice AI Backend

Python-based AI agent for real-time voice support with avatar presence and intelligent automation tools.

## 🎯 What This Does

This is the **backend server** that:
- Listens for LiveKit room events
- Processes user audio through OpenAI's Realtime API
- Renders a realistic AI avatar (Beyond Presence)
- Executes support tools (unblock users, send emails)
- Provides audio/visual feedback to users

## 📋 Prerequisites

- Python 3.12+
- Virtual environment (venv or conda)
- LiveKit server running (local or cloud)
- OpenAI API key
- Beyond Presence account & avatar ID
- Gmail account with App Password

## 🚀 Installation

### 1. Create Virtual Environment
```bash
cd support-agent
python -m venv venv

# Activate
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -e .
```

This installs:
- `livekit-agents[bey,openai]` – Agent framework with Beyond Presence & OpenAI plugins
- `livekit-plugins-noise-cancellation` – Audio preprocessing
- `python-dotenv` – Environment variable loading

### 3. Configure Environment
Create `.env.local`:
```bash
cat > .env.local << EOF
# LiveKit Connection
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Beyond Presence Avatar
BEY_AVATAR_ID=your_avatar_id_here

# Gmail (for support tickets)
GMAIL_USER=support@yourcompany.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
EOF
```

## ▶️ Running the Agent

### Development Mode
```bash
python agent.py dev
```

Watches for LiveKit room creation and joins automatically.

### Production (with worker pool)
```bash
python agent.py
```

Uses LiveKit's distributed worker system.

## 🔧 Key Components

### `agent.py` — Main Entrypoint
- Defines `Assistant` class with system instructions and tools
- Initializes LiveKit session with OpenAI Realtime LLM
- Starts Beyond Presence avatar session
- Configures room input (audio, video, noise cancellation)
- Adds background audio (typing sounds for thinking states)

### `prompts.py` — Agent Personality
- `AGENT_INSTRUCTIONS` – System prompt controlling agent behavior
- Includes troubleshooting workflow for support scenarios
- Email templates for resolved/unresolved cases
- Domain-specific knowledge (e.g., GenericCorporateApp login handling)

### `tools.py` — Custom Functions
Two main tools:

**`unblock_user(username: str)`**
- Clears `generic_corporate_app/public/blockusers.txt`
- Sends RPC notification to client showing success
- Returns confirmation message

**`send_email(to_email, subject, message, cc_email?)`**
- Connects to Gmail SMTP server
- Sends HTML/plain text email
- RPC notification to client
- Returns delivery confirmation

## 🎨 Audio & Feedback System

**Background Audio (Thinking Sounds)**
- Plays typing sounds while agent processes user input
- Files: `KEYBOARD_TYPING`, `KEYBOARD_TYPING2`
- Improves UX by signaling agent is thinking

**RPC Notifications**
- Agent calls `client.showNotification` method on frontend
- Passes event type (`unblock_user`, `send_email`) & parameters
- Frontend displays toast/popup to user

## 🔐 Environment Variables Reference

| Variable | Required | Purpose |
|----------|----------|---------|
| `LIVEKIT_URL` | ✅ | WebSocket URL to LiveKit server |
| `LIVEKIT_API_KEY` | ✅ | LiveKit API credential |
| `LIVEKIT_API_SECRET` | ✅ | LiveKit API secret |
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `BEY_AVATAR_ID` | ✅ | Beyond Presence avatar ID |
| `GMAIL_USER` | ✅ | Sender email address |
| `GMAIL_APP_PASSWORD` | ✅ | Gmail 16-character app password |

### Getting Gmail App Password
1. Enable 2-Step Verification on Google Account
2. Go to https://myaccount.google.com/apppasswords
3. Select "Mail" and "Windows Computer"
4. Copy the 16-character password (remove spaces)
5. Paste into `GMAIL_APP_PASSWORD`

## 📦 Dependencies Explained

```toml
livekit-agents[bey,openai]~=1.2
  ├── bey: Beyond Presence avatar plugin
  ├── openai: OpenAI Realtime model plugin
  └── agents: Core agent framework

livekit-plugins-noise-cancellation~=0.2
  └── BVC algorithm: Noise/echo reduction

python-dotenv>=1.2.1
  └── Load .env.local into os.environ
```

## 🧪 Testing the Agent

### 1. Start LiveKit Server (if local)
```bash
docker run -d --name livekit \
  -p 7880:7880 \
  -p 7881:7881 \
  -p 7882:7882 \
  livekit/livekit-server:latest
```

### 2. Start Agent
```bash
python agent.py dev
```

### 3. Start Frontend (from other terminal)
```bash
cd ../voicedesk-ai-front-end-main
pnpm dev
```

### 4. Test in Browser
- Navigate to http://localhost:3000
- Click "Start Call"
- Agent joins and greets you
- Test: "Unblock user john.doe" or "Send me the ticket"

## 🐛 Troubleshooting

### Agent doesn't join room
- Check `LIVEKIT_URL` points to correct server
- Verify `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET`
- Look for error in agent console output

### OpenAI not responding
- Verify `OPENAI_API_KEY` is valid
- Check API quota/rate limits
- Review OpenAI error logs

### Avatar not showing
- Confirm `BEY_AVATAR_ID` is correct
- Check Beyond Presence account is active
- Look for avatar initialization errors in logs

### Email not sending
- Verify `GMAIL_USER` is correct email
- Confirm `GMAIL_APP_PASSWORD` is exactly 16 chars (from Google Account)
- Check user has 2-Step Verification enabled
- Look for SMTP errors in logs

### RPC notifications fail
- Frontend must have `client.showNotification` handler
- Check network/WebSocket connectivity
- Add logging in `tools.py` to debug RPC calls

## 🔄 Agent Workflow Example

User says: *"I can't log in, it says my account is blocked"*

1. Agent hears audio → OpenAI processes
2. Agent recognizes "blocked" keyword
3. Asks for username: *"What's your username?"*
4. User: *"john.doe"*
5. Agent calls `unblock_user("john.doe")`
6. Tool clears blockusers.txt
7. Tool sends RPC notification to frontend
8. Frontend shows toast: "User john.doe unblocked!"
9. Agent: *"I've unblocked your account. Can you try logging in again?"*
10. User confirms success
11. Agent asks for email, calls `send_email()`
12. Sends ticket summary via Gmail
13. Agent: *"I've sent a confirmation email to your inbox. Is there anything else?"*

## 📚 Further Reading

- [LiveKit Agents Docs](https://docs.livekit.io/agents/)
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)
- [Beyond Presence SDK](https://www.beyondpresence.com/docs)
- [Python AsyncIO](https://docs.python.org/3/library/asyncio.html)

## 📝 Customization

### Change Agent Personality
Edit `prompts.py` – modify `AGENT_INSTRUCTIONS` string to change behavior, tone, domain knowledge.

### Add New Tools
In `tools.py`:
```python
@function_tool()
async def my_tool(context: RunContext, param: str) -> str:
    """Description for the LLM"""
    return "result"
```

### Change Voice
In `agent.py`:
```python
llm=openai.realtime.RealtimeModel(
    voice="alloy"  # Options: alloy, echo, fable, onyx, nova, shimmer
)
```

### Customize Avatar
In `agent.py`:
```python
avatar_id=os.getenv("BEY_AVATAR_ID")  # Change to different avatar
```

## ⚠️ Security Notes

- Never commit `.env.local` to Git
- Use environment variable vaults in production
- Rotate API keys regularly
- Don't log sensitive data (emails, usernames)
- Validate all user inputs before using in tools
- Use HTTPS/TLS for all connections

## 📄 License

Proprietary – See root LICENSE file.

---

**Status**: Active  
**Python Version**: 3.12+  
**Last Updated**: May 2026
