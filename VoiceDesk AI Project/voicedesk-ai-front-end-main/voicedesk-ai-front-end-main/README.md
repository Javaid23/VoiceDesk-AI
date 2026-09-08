# VoiceDesk AI Front-End – Voice Agent UI

Modern Next.js + React app for real-time voice chat with an AI avatar agent.

## 🎯 What This Does

This is the **client-facing interface** that:
- Initializes LiveKit room connection
- Displays video stream of remote participants (agent + avatar)
- Manages local audio/video input
- Shows chat & conversation transcripts
- Provides call controls (mute, screen share, hang up)
- Renders responsive, accessible UI with Radix + Tailwind

## 📋 Prerequisites

- Node.js 18+
- pnpm 9+ (or npm/yarn)
- LiveKit server running (local or cloud)
- OpenAI API key (shared backend)
- Modern browser (Chrome, Firefox, Safari, Edge)

## 🚀 Installation

### 1. Install Dependencies
```bash
cd voicedesk-ai-front-end-main
pnpm install
```

### 2. Configure Environment
Create `.env.local`:
```bash
cat > .env.local << EOF
# LiveKit Connection
NEXT_PUBLIC_LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
EOF
```

**Note:** Variables prefixed with `NEXT_PUBLIC_` are exposed to browser.

### 3. Run Development Server
```bash
pnpm dev
```

Opens http://localhost:3000

## 📂 Project Structure

```
voicedesk-ai-front-end-main/
├── app/
│   ├── layout.tsx           # Root layout + theme provider
│   ├── globals.css          # Global Tailwind styles
│   ├── (app)/
│   │   ├── layout.tsx       # App layout
│   │   ├── page.tsx         # Main page
│   │   └── opengraph-image.tsx  # Social preview
│   ├── api/
│   │   └── connection-details/
│   │       └── route.ts     # Generate LiveKit token
│   └── components/
│       ├── layout.tsx       # Layout page component
│       └── page.tsx         # Page component
├── components/
│   ├── session-view.tsx     # Main participant display
│   ├── agent-control-bar/   # Agent interaction controls
│   ├── chat/                # Chat UI components
│   ├── livekit/             # LiveKit-specific components
│   │   ├── agent-tile.tsx   # Agent video display
│   │   ├── avatar-tile.tsx  # Avatar rendering
│   │   ├── media-tiles.tsx  # All participant videos
│   │   └── video-tile.tsx   # Single participant
│   ├── ui/                  # Radix UI primitives
│   │   ├── button.tsx
│   │   ├── select.tsx
│   │   ├── toggle.tsx
│   │   └── alert.tsx
│   ├── app.tsx              # Main app component
│   ├── Rpc_Handler.tsx      # RPC message handling
│   ├── welcome.tsx          # Welcome screen
│   └── theme-toggle.tsx     # Dark/light mode
├── hooks/
│   ├── useChatAndTranscription.ts  # Message handling
│   ├── useConnectionDetails.ts     # Token generation
│   └── useDebug.ts                 # Debug utilities
├── lib/
│   ├── types.ts             # TypeScript interfaces
│   └── utils.ts             # Helper functions
├── public/
│   └── lk-logo.svg          # Assets
├── app-config.ts            # Centralized configuration
├── package.json             # Node dependencies
├── tsconfig.json            # TypeScript config
├── tailwind.config.ts       # Tailwind CSS config
└── next.config.ts           # Next.js configuration
```

## ▶️ Running the App

### Development
```bash
pnpm dev
```
- Runs with Turbopack (fast refresh)
- Opens http://localhost:3000
- Hot reload on file changes

### Production Build
```bash
pnpm build && pnpm start
```

### Linting
```bash
pnpm lint              # Check code
pnpm format            # Auto-format
pnpm format:check      # Check formatting
```

## 🔧 Key Components

### `app.tsx` — Main Application
- Initializes LiveKit room connection
- Manages audio/video tracks
- Handles room events (participant join/leave)
- Renders session view with controls

### `session-view.tsx` — Room Display
- Shows all participant video tiles
- Video grid layout
- Participant info & status

### `components/livekit/` — LiveKit Components
- `agent-tile.tsx` – Agent video feed
- `avatar-tile.tsx` – Avatar rendering
- `media-tiles.tsx` – All participant videos
- `video-tile.tsx` – Individual participant

### `components/chat/` — Chat UI
- `chat-message-view.tsx` – Message history
- `chat-input.tsx` – User message input
- `chat-entry.tsx` – Individual message

### `components/agent-control-bar/` — Controls
- Mute/unmute buttons
- Video toggle
- Screen share button
- Hang up button

### `Rpc_Handler.tsx` — Backend Integration
- Listens for RPC messages from agent
- Handles `client.showNotification` calls
- Displays toast alerts (unblock, email sent, etc.)

### `app-config.ts` — Configuration
Centralized config object:
```typescript
{
  companyName: string;
  pageTitle: string;
  pageDescription: string;
  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;
  logo: string;
  accent: string;
  logoDark: string;
  accentDark: string;
  startButtonText: string;
}
```

## 🎨 Theming

### Dark/Light Mode
- Toggle in top-right corner
- Uses `next-themes` provider
- Colors defined in `tailwind.config.ts`

### Customizing Colors
Edit `app-config.ts`:
```typescript
accent: '#FF6B6B',      // Primary color
accentDark: '#FF8E8E',  // Dark mode primary
```

Edit `tailwind.config.ts` for granular control:
```typescript
colors: {
  primary: {
    light: '#002cf2',
    dark: '#1fd5f9',
  }
}
```

## 🔑 Configuration Reference

### Environment Variables

**Required**
```env
NEXT_PUBLIC_LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

**Optional**
```env
NEXT_PUBLIC_LOG_LEVEL=info  # Debug, info, warn, error
NEXT_PUBLIC_AGENT_AVATAR_ID=avatar_xyz
```

### App Config (app-config.ts)

```typescript
export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'Your Company',
  pageTitle: 'Support Agent',
  pageDescription: 'AI-powered voice support',
  supportsChatInput: true,
  supportsVideoInput: true,
  supportsScreenShare: true,
  isPreConnectBufferEnabled: true,
  logo: '/logo.svg',
  accent: '#002cf2',
  logoDark: '/logo-dark.svg',
  accentDark: '#1fd5f9',
  startButtonText: 'Start Call',
};
```

## 🧪 Testing

### Manual Testing Checklist
- [ ] Page loads without errors
- [ ] Dark/light theme toggle works
- [ ] Start Call button creates room
- [ ] Microphone/camera permissions requested
- [ ] Agent video appears
- [ ] Audio is bidirectional
- [ ] Chat messages appear
- [ ] Screen share works (if enabled)
- [ ] Notifications display (unblock, email)
- [ ] End call disconnects properly

### Browser DevTools Debugging
```javascript
// In console:
window.livekit     // LiveKit client instance
window.room        // Current room
window.agent       // Agent session
```

## 🔐 Security & Privacy

**What's Sent to Backend**
- Audio stream (encrypted via WebRTC)
- Video stream (if enabled)
- Screen share (if enabled)
- Chat messages
- Participant metadata

**What's Stored**
- Session data (in memory only)
- No persistent storage without explicit user action
- Browser local storage for theme preference

**Best Practices**
- Don't share sensitive passwords on camera
- Review what agent can see via screen share
- Monitor email notifications for sensitive data
- Use HTTPS in production

## 🚀 Deployment

### Netlify
```bash
pnpm build
# Deploy `out/` or `.next/` directory
```

### Vercel (Recommended for Next.js)
```bash
# Push to GitHub, connect to Vercel
# Auto-deploys on push
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY . .
RUN pnpm install && pnpm build
CMD ["pnpm", "start"]
```

### Environment Variables in Deployment
Set in hosting platform (don't commit to Git):
- `NEXT_PUBLIC_LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `next` | React framework + SSR |
| `@livekit/components-react` | LiveKit UI components |
| `livekit-client` | WebRTC + room management |
| `@radix-ui/*` | Accessible UI primitives |
| `tailwindcss` | Utility CSS framework |
| `typescript` | Type safety |
| `sonner` | Toast notifications |

See `package.json` for full list & versions.

## 🎓 Learning Resources

- [Next.js Docs](https://nextjs.org/docs)
- [React 19 Docs](https://react.dev)
- [LiveKit Client SDK](https://docs.livekit.io/client-sdk-js/)
- [Radix UI](https://www.radix-ui.com/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [TypeScript](https://www.typescriptlang.org/docs/)

## 🐛 Troubleshooting

### Page won't load
- Check `NEXT_PUBLIC_LIVEKIT_URL` is set
- Verify LiveKit server is running
- Check browser console for errors

### No audio/video
- Check browser permissions (camera/mic)
- Verify `supportsVideoInput` in config
- Check WebRTC connectivity

### Agent not appearing
- Confirm agent is running (python agent.py dev)
- Check room name matches
- Verify LiveKit tokens are valid

### Chat messages not appearing
- Check `useChatAndTranscription` hook
- Verify message event handlers
- Check browser console for errors

### Theme not persisting
- Check `next-themes` provider in layout
- Verify localStorage is enabled
- Check for JavaScript errors in console

## 📝 Customization

### Change Company Branding
Edit `app-config.ts`:
```typescript
companyName: 'Acme Support',
pageTitle: 'Acme AI Agent',
logo: '/acme-logo.svg',
```

### Add Custom Component
```bash
mkdir components/custom
touch components/custom/MyComponent.tsx
```

### Modify UI Colors
Edit `tailwind.config.ts` or use Tailwind classes in components.

### Add Analytics
Integrate Google Analytics, Mixpanel, etc. in `app/layout.tsx`.

## ⚠️ Known Limitations

- WebRTC requires modern browser (Edge 79+, Chrome 75+, Firefox 64+, Safari 12+)
- Screen share not available on all browsers/OSs
- Avatar rendering depends on Beyond Presence service availability
- Requires HTTPS in production (for camera/mic access)

## 📄 License

Proprietary – See root LICENSE file.

---

**Status**: Active  
**Next.js Version**: 15.4.6  
**Node Version**: 18+  
**Last Updated**: May 2026
