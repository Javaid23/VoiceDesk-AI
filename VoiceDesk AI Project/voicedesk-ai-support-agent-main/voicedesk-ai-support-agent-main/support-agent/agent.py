from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    groq,
    assemblyai,
    deepgram,
    silero,
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


def prewarm(proc: agents.JobProcess):
    # Load the (CPU-bound) Silero VAD model once per worker process, before
    # any job arrives. Loading it inside the entrypoint blocks the asyncio
    # event loop for several seconds on every call, which delays ctx.connect()
    # and can trip the server's room-join / job-assignment timeout.
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: agents.JobContext):
    # Force ICE onto TURN relay (TCP/TLS 443) instead of direct UDP.
    # Direct UDP host/srflx candidates are blocked or unreliable on some
    # networks/firewalls, which shows up as "Subscriber pc state failed" /
    # "resuming connection" and eventually an AssignmentTimeoutError.
    await ctx.connect(
        rtc_config=rtc.RtcConfiguration(
            ice_transport_type=rtc.IceTransportType.TRANSPORT_RELAY,
        ),
    )

    # Modular voice pipeline (replaces the bundled OpenAI Realtime API):
    #   AssemblyAI (STT)  ->  Groq (LLM)  ->  Deepgram Aura (TTS)
    # with Silero VAD for interruptions and AssemblyAI's built-in
    # end-of-turn detection driving turn-taking (turn_detection="stt").
    session = AgentSession(
        stt=assemblyai.STT(
            keyterms_prompt=SUPPORT_KEYTERMS,
        ),
        llm=groq.LLM(model="openai/gpt-oss-20b"),
        tts=deepgram.TTS(
            model=os.getenv("DEEPGRAM_TTS_MODEL", "aura-2-andromeda-en"),
        ),
        vad=ctx.proc.userdata["vad"],
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
            # BVC noise cancellation requires a LiveKit Cloud entitlement that
            # isn't enabled on this project (it was timing out on every call
            # trying to fetch that config, adding delay) -- left off for now.
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
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            # Keep one executor pre-spawned and pre-warmed (VAD already loaded)
            # so the first call doesn't pay the model-load cost on its critical path.
            num_idle_processes=1,
            # The Silero VAD load in prewarm() can take well over the 10s default on
            # a slow/cold machine, which showed up as "error initializing process".
            initialize_process_timeout=120.0,
        )
    )