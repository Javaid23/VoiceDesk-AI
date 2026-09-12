# VoiceDesk AI

VoiceDesk AI is a real-time voice support agent with a talking avatar. A user opens the web app, starts a call, and speaks to an AI support assistant that can see their shared screen, walk them through a problem, unblock their account, and email them a ticket summary when the session ends.

It was built for the lablab.ai voice AI agent hackathon.

## What it does

- Holds a natural spoken conversation with sub-second response times.
- Renders a photorealistic avatar that speaks the agent's replies with lip sync.
- Reads the user's shared screen so it can diagnose what the user is actually looking at.
- Calls tools to act on the user's behalf: unblocking a locked account and sending a support ticket by email.
- Keeps replies short and conversational, the way a phone agent would.

## How it works

The agent runs as a LiveKit worker. When a user joins a room, the worker connects, starts the avatar, and runs a speech pipeline made of independently chosen providers:

| Stage | Provider | Notes |
|---|---|---|
| Speech to text | AssemblyAI | Streaming transcription with end-of-turn detection and a support vocabulary boost |
| Language model | Groq, Qwen 3.6 27B | Vision-capable, so it can read the shared screen; reasoning is disabled to keep latency low |
| Text to speech | Deepgram Aura | Low-latency streaming voice |
| Voice activity | Silero VAD | Runs locally, handles interruptions |
| Avatar | Beyond Presence | Joins the room as a participant and lip-syncs the agent's audio |
| Transport | LiveKit | WebRTC rooms, agent dispatch, and hosting |

The frontend is a Next.js application that creates the LiveKit room, publishes the user's microphone and screen, and renders the avatar's video and audio.

### Screen sharing

LiveKit only forwards video to realtime models, so a modular pipeline like this one is blind by default. The agent subscribes to the user's screen-share track itself, keeps the most recent frame, and attaches it to the user's turn when the user is asking about the screen. Frames are downscaled and sent at most once every few seconds to stay inside the language model's free-tier limits.

### Tools

- `unblock_user` clears the demo application's block list and notifies the frontend over RPC so it can show a confirmation.
- `send_email` sends a ticket summary through Gmail SMTP.

## Repository layout

```
frontend/                         Next.js web app
VoiceDesk AI Project/
  voicedesk-ai-support-agent-main/
    voicedesk-ai-support-agent-main/
      support-agent/
        agent.py                  Worker entrypoint and voice pipeline
        prompts.py                Agent instructions
        tools.py                  unblock_user and send_email
        Dockerfile                Image used by LiveKit Cloud
        livekit.toml              Binds the directory to the deployed agent
        generic_corporate_app/    Demo app the agent provides support for
```

## Running locally

### Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node.js 18 or newer with pnpm 9 (`corepack enable`)
- Accounts and API keys for LiveKit Cloud, AssemblyAI, Groq, Deepgram, and Beyond Presence
- A Gmail account with an app password, if you want the email tool to work

Every provider used here has a free tier, and the project runs entirely within them.

### Agent

```bash
cd "VoiceDesk AI Project/voicedesk-ai-support-agent-main/voicedesk-ai-support-agent-main/support-agent"
uv sync
```

Create `.env.local` in that directory:

```
LIVEKIT_URL=wss://<project>.livekit.cloud
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=

ASSEMBLYAI_API_KEY=
GROQ_API_KEY=
DEEPGRAM_API_KEY=
DEEPGRAM_TTS_MODEL=aura-2-andromeda-en

BEY_API_KEY=
BEY_AVATAR_ID=

GMAIL_USER=
GMAIL_APP_PASSWORD=
```

Then start the worker:

```bash
uv run agent.py dev
```

`dev` reloads on file changes. Use `uv run agent.py start` for production behaviour.

### Frontend

```bash
cd frontend
pnpm install
```

Create `frontend/.env.local` with the same three LiveKit values:

```
LIVEKIT_URL=wss://<project>.livekit.cloud
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
```

Then:

```bash
pnpm dev
```

Open http://localhost:3000 and start a call.

### Demo application

The agent is written to support a small corporate login app included in the repository. It ships with one blocked user so the support flow can be demonstrated end to end.

```bash
cd "VoiceDesk AI Project/voicedesk-ai-support-agent-main/voicedesk-ai-support-agent-main/support-agent/generic_corporate_app"
pnpm install
pnpm dev
```

Open http://localhost:8080 and sign in with username `\vienna\maxman123` and password `passw0rd`. The login is rejected because `maxman123` is listed in `public/blockusers.txt`. Share that screen with the agent, describe the problem, and ask it to unblock the account. The agent clears the block list, the login succeeds on the next attempt, and the agent offers to email a ticket.

Note that `unblock_user` edits a file on the machine running the agent. For the unblock to take effect on the demo app, run the agent on the same machine as the app.

## Deployment

The agent is hosted on LiveKit Cloud and the frontend on Vercel. Both run on free tiers.

### Agent on LiveKit Cloud

Install the [LiveKit CLI](https://docs.livekit.io/home/cli/), then from the `support-agent` directory:

```bash
lk agent deploy --secrets-file <path-to-secrets> --yes .
```

The secrets file holds the provider keys from `.env.local` except the three `LIVEKIT_*` values, which LiveKit Cloud injects itself. Set `LIVEKIT_USE_ASSIGNED_URL=1` in the secrets so the agent uses the regional URL it is assigned rather than the project URL.

The `Dockerfile` pins Python 3.12 to match `uv.lock` and pre-downloads the Silero model at build time so it is not fetched on the first call.

### Frontend on Vercel

Import the repository, set the root directory to `frontend`, and add the three `LIVEKIT_*` environment variables. The build uses the committed `pnpm-lock.yaml`.

## Configuration

Optional environment variables for the agent:

| Variable | Default | Purpose |
|---|---|---|
| `GROQ_MODEL` | `qwen/qwen3.6-27b` | Language model. Must support images for screen sharing to work. |
| `GROQ_MAX_TOKENS` | `250` | Output cap per reply. Kept low to stay within Groq's free-tier output limit. |
| `DEEPGRAM_TTS_MODEL` | `aura-2-andromeda-en` | Voice used for replies. |
| `BLOCKUSERS_FILE` | bundled demo app path | Location of the block list `unblock_user` edits. |
| `LIVEKIT_USE_ASSIGNED_URL` | unset | Set to `1` in cloud deployments. |
| `LIVEKIT_FORCE_RELAY` | unset | Set to `1` to force TURN relay on networks that block direct WebRTC. |

Agent behaviour and tone are defined in `prompts.py`. Tools are defined in `tools.py` using LiveKit's `@function_tool` decorator.

## Limitations

- Groq's free tier allows roughly 7,000 input tokens per minute. A screen frame costs a large share of that, so the agent only sends the screen when the user refers to it and no more than once every few seconds. A rapid series of screen questions may be briefly rate limited.
- The Beyond Presence avatar leaves and rejoins the room shortly after connecting. The agent waits for it to settle before speaking, which adds a few seconds to the start of each call.
- `unblock_user` writes to a local file, so it only affects the demo app when the agent and the app run on the same machine.

## Author

Muhammad Javaid Butt
