from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    groq,
    assemblyai,
    elevenlabs,
    silero,
    noise_cancellation,
    bey
)
from tools import unblock_user, send_email
from prompts import AGENT_INSTRUCTIONS
import os
from livekit.agents import BackgroundAudioPlayer, AudioConfig, BuiltinAudioClip

load_dotenv(".env.local")

# Domain vocabulary boosted in AssemblyAI transcription so support-specific
# terms (product name, tool names, IT jargon) are recognized reliably.
SUPPORT_KEYTERMS = [
    "VoiceDesk AI",
    "unblock",
    "blocked account",
    "support ticket",
    "login",
    "password reset",
    "username",
    "domain",
    "screen share",
    "Beyond Presence",
    "LiveKit",
]


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=AGENT_INSTRUCTIONS,
        tools=[unblock_user, send_email])


async def entrypoint(ctx: agents.JobContext):
    # Modular voice pipeline (replaces the bundled OpenAI Realtime API):
    #   AssemblyAI (STT)  ->  OpenAI (LLM)  ->  ElevenLabs (TTS)
    # with Silero VAD for interruptions and AssemblyAI's built-in
    # end-of-turn detection driving turn-taking (turn_detection="stt").
    session = AgentSession(
        stt=assemblyai.STT(
            keyterms_prompt=SUPPORT_KEYTERMS,
        ),
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        tts=elevenlabs.TTS(
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            model="eleven_turbo_v2_5",
        ),
        vad=silero.VAD.load(),
        turn_detection="stt",
    )

    avatar = bey.AvatarSession(
    avatar_id=os.getenv("BEY_AVATAR_ID"),  # ID of the Beyond Presence avatar to use
    )

    # Start the avatar and wait for it to join
    await avatar.start(session, room=ctx.room)

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            # For telephony applications, use `BVCTelephony` instead for best results
            noise_cancellation=noise_cancellation.BVC(),
            video_enabled=True,

        ),
    )

    background_audio = BackgroundAudioPlayer(
        thinking_sound=[
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=1),
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=1),
        ],
    )
    await background_audio.start(room=ctx.room, agent_session=session)

    await session.generate_reply(
        instructions="Greet the user and offer your assistance. You should start by speaking in English."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))