# 🤖 VoiceDesk AI – Full Stack Voice & Avatar Application

A full-stack AI-powered support platform combining **real-time voice interaction**, **realistic AI avatars**, and **intelligent automation tools** for enterprise customer support.

## 🎯 Project Overview

This project demonstrates a complete implementation of a modern support system where an AI agent:
- **Engages users in natural voice conversations** using OpenAI's Realtime API
- **Displays a realistic AI avatar** from Beyond Presence
- **Observes user screens** to provide context-aware support
- **Automates support tasks** (user unblocking, ticket generation, email notifications)
- **Provides real-time feedback** with audio and visual cues

Perfect for portfolio demonstration of **full-stack development**, **AI/ML integration**, **real-time communication**, and **modern DevOps practices**.

---

## 📁 Project Structure

```
VoiceDesk AI Project/
├── README.md (this file)
├── voicedesk-ai-support-agent-main/
│   └── support-agent/              # Python backend agent
│       ├── agent.py                # LiveKit agent entrypoint
│       ├── prompts.py              # Agent instructions & personalities
│       ├── tools.py                # Custom tools (unblock_user, send_email)
│       ├── pyproject.toml          # Python dependencies
│       ├── .env.local              # Environment variables (secrets)
│       └── generic_corporate_app/  # Client app (TypeScript)
│
└── voicedesk-ai-front-end-main/    # Next.js frontend
    ├── app-config.ts               # Frontend configuration
    ├── package.json                # Node dependencies
    ├── app/                        # Next.js app directory
    ├── components/                 # React components
    │   ├── livekit/               # LiveKit UI integration
    │   └── ui/                    # Radix UI components
    └── hooks/                      # Custom React hooks
```

---

## ⚙️ Tech Stack

### Backend (Python)
- **LiveKit Agents** – Real-time communication framework
- **OpenAI Realtime API** – Voice LLM with natural conversation
- **Beyond Presence** – AI avatar rendering and animation
- **Python 3.12+** – Modern async/await support
- **Gmail SMTP** – Support ticket email automation

### Frontend (TypeScript/React)
- **Next.js 15** – Full-stack React framework with Turbopack
- **LiveKit Client SDK** – Room management & participant handling
- **Radix UI** – Accessible component primitives
- **Tailwind CSS** – Utility-first styling
- **TypeScript** – Type-safe development

### DevOps & Tools
- **pnpm** – Fast Node.js package manager
- **python-dotenv** – Environment variable management
- **SMTP with TLS** – Secure email delivery

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+ (with pnpm)
- LiveKit server instance (self-hosted or cloud)
- OpenAI API key
- Beyond Presence account
- Gmail account with App Password

### 1️⃣ Backend Setup (Support Agent)

```bash
cd voicedesk-ai-support-agent-main/support-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Configure environment
cat > .env.local << EOF
LIVEKIT_URL=ws://your-livekit-server:7880
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
OPENAI_API_KEY=sk-your-openai-key
BEY_AVATAR_ID=your_avatar_id
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
EOF

# Run the agent
python agent.py dev
```

### 2️⃣ Frontend Setup

```bash
cd voicedesk-ai-front-end-main

# Install dependencies
pnpm install

# Set up local environment
cat > .env.local << EOF
NEXT_PUBLIC_LIVEKIT_URL=ws://your-livekit-server:7880
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
EOF

# Run development server
pnpm dev

# Open browser
# Navigate to http://localhost:3000
```

---

## 🎬 How It Works

### Agent Workflow
1. **User initiates call** → Creates LiveKit room
2. **Agent joins room** → Avatar renders via Beyond Presence
3. **Natural conversation** → OpenAI Realtime processes audio bi-directionally
4. **User shares screen** → Agent can see and reference the display
5. **Agent resolves issue** → Uses tools (unblock, email) as needed
6. **Confirmation & ticket** → Sends email summary to user

### Key Features in Action

**🎤 Voice Interaction**
- Real-time audio streaming with noise cancellation (BVC algorithm)
- Natural language understanding with context awareness
- Audio feedback (typing sounds) during agent thinking

**👁️ Screen Sharing**
- User shares screen → agent receives video stream
- Agent can guide user through UI problems
- Perfect for visual troubleshooting

**🔓 User Management**
- Unblock users via `unblock_user` tool
- Modifies `blockusers.txt` in real-time
- RPC notification system for UI feedback

**📧 Ticket Automation**
- Generate support ticket summary
- Send via Gmail SMTP
- Supports both resolved & unresolved cases

**🎨 Avatar Presence**
- Live streaming of AI avatar using Beyond Presence SDK
- Synchronized with voice output for lip-sync
- Customizable appearance & personality

---

## 🛠️ Configuration

### Environment Variables

**Backend (.env.local)**
```env
# LiveKit
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# OpenAI
OPENAI_API_KEY=sk-...

# Beyond Presence
BEY_AVATAR_ID=avatar_1234abcd

# Gmail
GMAIL_USER=support@company.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx  # 16-character app password
```

**Frontend (.env.local)**
```env
NEXT_PUBLIC_LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

### App Configuration (Frontend)

Edit `app-config.ts` to customize:
- Company name & branding
- Page title & description
- Feature toggles (chat, video, screen share)
- UI colors (light/dark themes)

---

## 📚 File Guides

### Backend Files

| File | Purpose |
|------|---------|
| `agent.py` | Main agent entrypoint; initializes LiveKit session, avatar, and background audio |
| `prompts.py` | System instructions & agent personality; ticket generation examples |
| `tools.py` | Tool definitions (`unblock_user`, `send_email`); RPC client integration |
| `pyproject.toml` | Python dependencies & project metadata |

### Frontend Files

| File | Purpose |
|------|---------|
| `app-config.ts` | Centralized app configuration & feature flags |
| `app/layout.tsx` | Root layout with theme provider |
| `components/session-view.tsx` | Main room participant display |
| `components/livekit/agent-*.tsx` | Agent-specific controls & status displays |
| `components/chat-*.tsx` | Chat UI components |
| `hooks/useChatAndTranscription.ts` | Custom hook for message handling |

---

## 🔐 Security Considerations

⚠️ **Production Deployment Checklist**
- [ ] Use environment variable vaults (AWS Secrets Manager, HashiCorp Vault)
- [ ] Never commit `.env.local` or API keys to Git
- [ ] Enable TLS/HTTPS for all traffic
- [ ] Implement rate limiting on RPC endpoints
- [ ] Validate email inputs and sanitize ticket content
- [ ] Use Gmail App Passwords (not main account password)
- [ ] Add authentication to LiveKit rooms (JWT tokens)
- [ ] Monitor agent logs for abuse/errors
- [ ] Set up error tracking (Sentry, DataDog)

---

## 📝 Customization Guide

### Change Agent Personality
Edit `prompts.py` → `AGENT_INSTRUCTIONS` string:
```python
AGENT_INSTRUCTIONS = """
You are now a billing support specialist...
"""
```

### Add New Tools
In `tools.py`, use the `@function_tool()` decorator:
```python
@function_tool()
async def my_custom_tool(context: RunContext, param: str) -> str:
    """Tool description"""
    return "Tool result"
```

### Modify Frontend Theme
Edit `app-config.ts`:
```typescript
accent: '#FF6B6B',
accentDark: '#FF8E8E',
```

### Change Avatar
In `agent.py`:
```python
avatar_id=os.getenv("BEY_AVATAR_ID")  # Update this ID
```

---

## 🧪 Testing

### Manual Testing Workflow
1. Start backend: `python agent.py dev`
2. Start frontend: `pnpm dev`
3. Open http://localhost:3000
4. Click "Start Call"
5. Share screen (optional)
6. Test: "Unblock my account" or "Send me a ticket"

### Debugging
- **Backend logs**: Check console output from `agent.py`
- **Frontend logs**: Browser DevTools Console
- **Email logs**: Check Gmail "Sent" folder
- **RPC debugging**: Add `logging.info()` statements in `tools.py`

---

## 🤝 Contributing

This is a personal portfolio project. For improvements:
1. Fork the repository
2. Create a feature branch
3. Commit improvements
4. Submit a pull request

---

## 📜 License

**Proprietary License** (See `LICENSE` file)

- Source code authored by **Thanh-Y Nguyen** © 2025
- Licensed for **private/educational use only**
- Commercial use, redistribution, or publication requires written permission

**Third-Party Components:**
- LiveKit SDK — Apache 2.0 / MIT
- OpenAI SDK — MIT
- Next.js & React — MIT
- Radix UI — MIT
- See individual packages for full license details

---

## 📞 Support & Contact

For questions about this project:
- Check the individual README files in each subdirectory
- Review code comments and docstrings
- Refer to LiveKit & OpenAI official documentation

---

## 🎓 Portfolio Highlights

**This project demonstrates:**
- ✅ Full-stack development (Python + TypeScript/React)
- ✅ Real-time communication & streaming (WebSocket, WebRTC)
- ✅ AI/LLM integration (OpenAI Realtime API)
- ✅ Async/await patterns & concurrent programming
- ✅ Email automation & SMTP protocols
- ✅ Modern DevOps (environment management, virtual envs)
- ✅ UI/UX (Radix components, Tailwind, responsive design)
- ✅ Error handling & logging best practices
- ✅ API design (tools, RPC, function definitions)
- ✅ Third-party SDK integration (LiveKit, Beyond Presence, OpenAI)

---

**Last Updated:** May 2026  
**Status:** Active Development  
**Version:** 1.0.0
