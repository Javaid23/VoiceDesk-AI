from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import AgentSession, Agent, RoomInputOptions, llm, utils
from livekit.agents.voice.io import AudioOutput
# Private module; pinned by uv.lock (livekit-agents 1.2.16). Re-check on upgrade.
from livekit.agents.voice.avatar._datastream_io import (
    AUDIO_STREAM_TOPIC,
    DataStreamAudioOutput,
)
from livekit.plugins import (
    groq,
    assemblyai,
    deepgram,
    silero,
    bey
)
from tools import unblock_user, send_email
from prompts import AGENT_INSTRUCTIONS
import asyncio
import logging
import os
import time
from livekit.agents import BackgroundAudioPlayer, AudioConfig, BuiltinAudioClip

load_dotenv(".env.local")

logger = logging.getLogger("voicedesk")

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


async def wait_for_stable_avatar(
    room: rtc.Room,
    identity: str,
    *,
    settle: float = 4.0,
    timeout: float = 30.0,
) -> bool:
    """Wait until the avatar participant has been present, with a video
    track, for `settle` uninterrupted seconds.

    Observed on LiveKit Cloud (DEBUG logs, room 6261): the Beyond Presence
    avatar joins, then leaves and rejoins ~8s later. bey.AvatarSession.start()
    returns on the *first* join, so the greeting was streamed into the gap
    and stalled -- the agent stayed "speaking", never took the user's turn,
    and hung on shutdown. Whether a call worked was a race against the swap.
    Waiting for a stable participant makes the greeting land on the instance
    that stays. Returns False (and the caller proceeds anyway) on timeout.
    """
    stable_since: float | None = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        p = room.remote_participants.get(identity)
        has_video = p is not None and any(
            pub.kind == rtc.TrackKind.KIND_VIDEO for pub in p.track_publications.values()
        )
        now = time.monotonic()
        if has_video:
            if stable_since is None:
                stable_since = now
            elif now - stable_since >= settle:
                return True
        elif stable_since is not None:
            logger.info("avatar %s left during settle window; waiting for it to rejoin", identity)
            stable_since = None
        await asyncio.sleep(0.25)
    logger.warning("avatar %s never stabilised within %.0fs; continuing anyway", identity, timeout)
    return False


class ResilientAvatarAudioOutput(DataStreamAudioOutput):
    """DataStreamAudioOutput that cannot wedge the session.

    The stock output awaits each stream open/write on an FFI ack with no
    timeout, and the session then awaits the avatar's "playback finished"
    RPC with no timeout. On LiveKit Cloud the Beyond Presence avatar was
    observed to stop consuming audio (DEBUG logs, rooms 6896/7671/4464/6261):
    the greeting never drained, no ack ever came, the agent stayed
    "speaking", ignored every user turn, and had to be force-killed.

    Two bounded behaviours instead:
    - capture_frame: the open/write is bounded. On stall the writer is dropped
      and the next frame opens a fresh stream to whichever participant holds
      the avatar identity now. Frames during the stall are lost (a glitch
      beats a hang).
    - flush: a watchdog is armed per segment. If the avatar never confirms
      playback, we report it ourselves so the session can take the next turn.
    """

    WRITE_TIMEOUT = 5.0
    PLAYOUT_GRACE = 5.0

    # AudioOutput tracks these privately; read them rather than keeping a
    # parallel count, which drifts when flushes and acks interleave and
    # caused spurious "playback_finished called more times than captured".
    _SEGMENTS = "_AudioOutput__playback_segments_count"
    _FINISHED = "_AudioOutput__playback_finished_count"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def capture_frame(self, frame: rtc.AudioFrame) -> None:
        # Same readiness gate as the base class, deliberately unbounded: the
        # avatar participant must exist before anything can be sent.
        if self._start_atask is None:
            self._start_atask = asyncio.create_task(self._start_task())
        await asyncio.shield(self._start_atask)

        # Segment accounting lives in the grandparent; skip the base class's
        # unbounded open/write and do a bounded version of it below.
        await AudioOutput.capture_frame(self, frame)
        try:
            await asyncio.wait_for(self._open_and_write(frame), timeout=self.WRITE_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning(
                "avatar audio stream stalled for %.0fs; dropping it, will re-open on next frame",
                self.WRITE_TIMEOUT,
            )
            self._stream_writer = None

    async def _open_and_write(self, frame: rtc.AudioFrame) -> None:
        if not self._stream_writer:
            self._stream_writer = await self._room.local_participant.stream_bytes(
                name=utils.shortuuid("AUDIO_"),
                topic=AUDIO_STREAM_TOPIC,
                destination_identities=[self._destination_identity],
                attributes={
                    "sample_rate": str(frame.sample_rate),
                    "num_channels": str(frame.num_channels),
                },
            )
            self._pushed_duration = 0.0
        await self._stream_writer.write(bytes(frame.data))
        self._pushed_duration += frame.duration

    def flush(self) -> None:
        pushed = self._pushed_duration
        super().flush()
        # Nothing was streamed (e.g. the LLM turn failed), so there is no
        # playback to wait for and nothing to rescue.
        if pushed <= 0:
            return

        segment = getattr(self, self._SEGMENTS, 0)

        async def _watchdog() -> None:
            await asyncio.sleep(pushed + self.PLAYOUT_GRACE)
            # Only step in if this segment is still unacknowledged.
            if getattr(self, self._FINISHED, 0) < segment:
                logger.warning(
                    "avatar never confirmed playback of segment %d (%.1fs of audio); "
                    "reporting playback finished so the session can continue",
                    segment, pushed,
                )
                self.on_playback_finished(playback_position=pushed, interrupted=False)

        task = asyncio.create_task(_watchdog())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


class Assistant(Agent):
    """Support agent that can see the user's shared screen.

    AgentSession only forwards video frames to a *realtime* model
    (AgentActivity.push_video is a no-op when _rt_session is None), so with a
    modular STT -> LLM -> TTS pipeline every screen-share frame is discarded
    and the agent is effectively blind. Instead we keep the most recent frame
    ourselves and attach it to each completed user turn, which is the
    supported way to give a non-realtime pipeline vision.
    """

    def __init__(self) -> None:
        super().__init__(instructions=AGENT_INSTRUCTIONS,
        tools=[unblock_user, send_email])
        self._latest_frame: rtc.VideoFrame | None = None
        self._frame_tasks: set[asyncio.Task] = set()
        self._last_image_at: float = 0.0

    def watch_video(self, room: rtc.Room) -> None:
        """Track the newest frame from any video the user publishes."""

        def _consume(track: rtc.Track, source: rtc.TrackSource.ValueType) -> None:
            async def _reader() -> None:
                label = rtc.TrackSource.Name(source)
                logger.info("watching video source=%s", label)
                try:
                    async for ev in rtc.VideoStream(track):
                        self._latest_frame = ev.frame
                finally:
                    logger.info("video source ended source=%s", label)
                    self._latest_frame = None

            task = asyncio.create_task(_reader())
            self._frame_tasks.add(task)
            task.add_done_callback(self._frame_tasks.discard)

        # Screen share only. The webcam tells a support agent nothing, and
        # subscribing to it meant a frame was attached to every turn even when
        # nothing was being shared -- pure token cost.
        WANTED = (rtc.TrackSource.SOURCE_SCREENSHARE,)

        @room.on("track_subscribed")
        def _on_sub(track: rtc.Track, pub: rtc.TrackPublication, participant: rtc.RemoteParticipant):
            if track.kind == rtc.TrackKind.KIND_VIDEO and pub.source in WANTED:
                _consume(track, pub.source)

        # Anything already published before we attached the handler.
        for participant in room.remote_participants.values():
            for pub in participant.track_publications.values():
                if (
                    pub.kind == rtc.TrackKind.KIND_VIDEO
                    and pub.source in WANTED
                    and pub.track is not None
                ):
                    _consume(pub.track, pub.source)

    # Groq's free tier allows 7000 input tokens per minute. A 1920x1080 frame
    # costs ~7000 on its own and 768x432 still costs ~3184 (measured from the
    # 429s), so attaching the screen to every turn throttled the whole
    # conversation. Send a smaller frame, and only when the user is actually
    # asking about the screen.
    VISION_WIDTH = 640
    VISION_HEIGHT = 360

    # Words that suggest the user is referring to what is on screen.
    VISION_CUES = (
        "screen", "see", "look", "show", "watch", "view", "display",
        "error", "issue", "problem", "wrong", "message", "warning",
        "this", "that", "here", "page", "button", "login", "log in",
        "blocked", "red", "popup", "dialog", "says",
    )
    # Never send two frames closer together than this.
    VISION_MIN_INTERVAL = 6.0

    async def on_user_turn_completed(
        self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage
    ) -> None:
        # Old turns keep their images, so the context accumulates them until
        # the model refuses ("Too many images provided. This model supports up
        # to 3 images") and the token cost multiplies. Only the current screen
        # is useful, so drop the rest.
        dropped = 0
        for item in turn_ctx.items:
            if getattr(item, "type", None) != "message":
                continue
            content = getattr(item, "content", None)
            if not isinstance(content, list):
                continue
            kept = [c for c in content if not isinstance(c, llm.ImageContent)]
            dropped += len(content) - len(kept)
            item.content = kept
        if dropped:
            logger.debug("dropped %d stale screen frame(s) from context", dropped)

        frame = self._latest_frame
        if frame is None:
            return

        # Only spend the image budget when the turn is plausibly about the
        # screen. Chit-chat ("hi, how are you") does not need a screenshot,
        # and sending one anyway used up the per-minute allowance so the
        # turns that *did* need it got rate-limited instead.
        said = (new_message.text_content or "").lower()
        relevant = any(cue in said for cue in self.VISION_CUES)
        since = time.monotonic() - self._last_image_at
        if not relevant:
            logger.debug("skipping screen frame; turn not about the screen: %r", said[:60])
            return
        if since < self.VISION_MIN_INTERVAL:
            logger.debug("skipping screen frame; sent one %.1fs ago", since)
            return
        self._last_image_at = time.monotonic()
        image = llm.ImageContent(
            image=frame,
            inference_width=self.VISION_WIDTH,
            inference_height=self.VISION_HEIGHT,
        )
        if isinstance(new_message.content, list):
            new_message.content.append(image)
        else:
            new_message.content = [new_message.content, image]
        logger.info(
            "attached screen frame to user turn (%dx%d -> %dx%d)",
            frame.width, frame.height, self.VISION_WIDTH, self.VISION_HEIGHT,
        )


def prewarm(proc: agents.JobProcess):
    # Load the (CPU-bound) Silero VAD model once per worker process, before
    # any job arrives. Loading it inside the entrypoint blocks the asyncio
    # event loop for several seconds on every call, which delays ctx.connect()
    # and can trip the server's room-join / job-assignment timeout.
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: agents.JobContext):
    t0 = time.perf_counter()

    def mark(phase: str) -> None:
        # Per-phase join timings, so slow joins can be attributed precisely.
        logger.info("timing: %-16s +%.1fs", phase, time.perf_counter() - t0)

    # --- join diagnostics: what does this job connect with, and does the
    # connection go through a retry cycle? (ctx.connect() is a thin wrapper
    # around rtc.Room.connect(url, token); a standalone Room.connect() from
    # this machine takes ~5s while the job's takes a near-constant ~44s.)
    info = ctx._info  # RunningJobInfo: the url/token the server assigned
    try:
        import base64
        import json as _json
        payload = info.token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = _json.loads(base64.urlsafe_b64decode(payload))
        video = dict(claims.get("video", {}))
        logger.info(
            "join: url=%s room=%s identity=%s grants=%s",
            info.url, video.pop("room", None), claims.get("sub"), video,
        )
    except Exception as e:  # diagnostics must never break the call
        logger.info("join: url=%s (token decode failed: %s)", getattr(info, "url", "?"), e)

    def _trace(ev: str) -> None:
        def _h(*args):
            mark(f"room event {ev} {args[0] if args else ''}")
        ctx.room.on(ev, _h)

    for _ev in ("connected", "disconnected", "reconnecting", "reconnected",
                "connection_state_changed"):
        _trace(_ev)

    # Participant/track lifecycle, with identity. livekit-agents does not log
    # these itself, and they are what shows whether the avatar participant
    # leaves and rejoins (and when) relative to the greeting stream.
    def _trace_participant(ev: str) -> None:
        def _h(*args):
            ident = next((getattr(a, "identity", None) for a in args
                          if getattr(a, "identity", None)), "?")
            mark(f"participant event {ev} identity={ident}")
        ctx.room.on(ev, _h)

    for _ev in ("participant_connected", "participant_disconnected",
                "track_published", "track_unpublished",
                "track_subscribed", "track_unsubscribed"):
        _trace_participant(_ev)

    # --- workaround: the SFU node hostname in the job assignment publishes
    # IPv6 (AAAA) records, and IPv6 is black-holed on this network -- every
    # TCP connect to those addresses hangs until timeout before the engine
    # falls back to IPv4 (measured: two ~20s timeouts = the constant ~44s
    # join). The project's main hostname is IPv4-only and the token is
    # project-scoped, so connecting through it works and takes ~2-5s.
    # Set LIVEKIT_USE_ASSIGNED_URL=1 to restore the default (e.g. once IPv6
    # is fixed or disabled on this machine).
    main_url = os.getenv("LIVEKIT_URL")
    if main_url and os.getenv("LIVEKIT_USE_ASSIGNED_URL") != "1" and info.url != main_url:
        try:
            import dataclasses
            ctx._info = dataclasses.replace(info, url=main_url)
        except Exception:
            info.url = main_url  # not a dataclass? plain assignment
        logger.info("join: overriding assigned url -> LIVEKIT_URL=%s", main_url)

    # Let ICE use every candidate type (direct UDP first, TURN relay as the
    # automatic fallback) -- fastest path on a healthy network. Relay-only was
    # forced while a firewall was blocking inbound traffic to python.exe; set
    # LIVEKIT_FORCE_RELAY=1 to get that behaviour back without a code change.
    rtc_config = None
    if os.getenv("LIVEKIT_FORCE_RELAY") == "1":
        rtc_config = rtc.RtcConfiguration(
            ice_transport_type=rtc.IceTransportType.TRANSPORT_RELAY,
        )
    await ctx.connect(rtc_config=rtc_config)
    mark("room connected")

    # Modular voice pipeline (replaces the bundled OpenAI Realtime API):
    #   AssemblyAI (STT)  ->  Groq (LLM)  ->  Deepgram Aura (TTS)
    # with Silero VAD for interruptions and AssemblyAI's built-in
    # end-of-turn detection driving turn-taking (turn_detection="stt").
    session = AgentSession(
        stt=assemblyai.STT(
            keyterms_prompt=SUPPORT_KEYTERMS,
        ),
        # Vision-capable, so the agent can read the user's shared screen.
        # openai/gpt-oss-* are text-only and reject images outright
        # ("content must be a string"), which made screen share useless.
        # reasoning_effort="none" is required: without it this model emits
        # <think> blocks that the TTS would read aloud, and a "say hello"
        # turn measured 2332ms instead of 191ms.
        llm=groq.LLM(
            model=os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b"),
            reasoning_effort="none",
            # Groq's free tier caps *requested* output tokens per minute at
            # 1000 for this model. The default (2048) is rejected outright:
            #   429 "Request too large ... OTPM: Limit 1000, Requested 2048"
            # so every turn burned its retries before answering. Spoken replies
            # and tool calls need far less than this.
            max_completion_tokens=int(os.getenv("GROQ_MAX_TOKENS", "250")),
        ),
        tts=deepgram.TTS(
            model=os.getenv("DEEPGRAM_TTS_MODEL", "aura-2-andromeda-en"),
        ),
        vad=ctx.proc.userdata["vad"],
        turn_detection="stt",
        # Start LLM inference on interim transcripts, before end-of-turn is
        # final; the draft is discarded if the transcript changes. Cuts
        # perceived response latency noticeably.
        preemptive_generation=True,
        # Shorter pause after AssemblyAI signals end-of-turn before we commit
        # the user's turn (default 0.5s).
        min_endpointing_delay=0.3,
    )
    mark("session built")

    # --- per-turn latency breakdown: how long after the user stops talking
    # until the reply starts. eou = end-of-utterance detection, ttft = LLM
    # time-to-first-token, ttfb = TTS time-to-first-byte. Their sum is what
    # the caller perceives as "thinking time" (the avatar adds its own
    # render delay on top, which is not visible from here).
    @session.on("metrics_collected")
    def _on_metrics(ev) -> None:  # MetricsCollectedEvent
        m = ev.metrics
        kind = type(m).__name__
        if kind == "EOUMetrics":
            logger.info(
                "latency: EOU  end_of_utterance=%.2fs transcription=%.2fs",
                m.end_of_utterance_delay, m.transcription_delay,
            )
        elif kind == "LLMMetrics":
            logger.info(
                "latency: LLM  ttft=%.2fs total=%.2fs tokens=%s cancelled=%s",
                m.ttft, m.duration, m.completion_tokens, m.cancelled,
            )
        elif kind == "TTSMetrics":
            logger.info(
                "latency: TTS  ttfb=%.2fs total=%.2fs audio=%.2fs chars=%s cancelled=%s",
                m.ttfb, m.duration, m.audio_duration, m.characters_count, m.cancelled,
            )

    avatar = bey.AvatarSession(
        avatar_id=os.getenv("BEY_AVATAR_ID"),  # ID of the Beyond Presence avatar to use
    )

    # Beyond Presence's API strictly requires ws:// or wss:// and rejects
    # anything else. bey.AvatarSession defaults to os.getenv("LIVEKIT_URL"),
    # but on LiveKit Cloud's hosted-agent runtime that env var is injected as
    # https://... (LiveKit's own client tolerates that scheme; Bey's
    # validator does not), which made every cloud call fail with "Invalid
    # LiveKit URL" and the avatar never joining. Normalize the scheme and
    # pass it explicitly rather than relying on the env var.
    bey_livekit_url = os.getenv("LIVEKIT_URL", "")
    if bey_livekit_url.startswith("https://"):
        bey_livekit_url = "wss://" + bey_livekit_url[len("https://"):]
    elif bey_livekit_url.startswith("http://"):
        bey_livekit_url = "ws://" + bey_livekit_url[len("http://"):]

    # Start the avatar and wait for it to join
    await avatar.start(session, room=ctx.room, livekit_url=bey_livekit_url)
    mark("avatar joined")

    # avatar.start() resolves on the first join, but the avatar participant
    # leaves and rejoins shortly after. Don't start the session (and the
    # greeting) until it has been stable, or the audio streams into the gap.
    avatar_identity = getattr(avatar, "_avatar_participant_identity", "bey-avatar-agent")
    await wait_for_stable_avatar(ctx.room, avatar_identity)
    mark("avatar stable")

    # Replace the plugin's output with the bounded one. session.start() wraps
    # whatever is in output.audio, so this has to happen before it.
    session.output.audio = ResilientAvatarAudioOutput(
        ctx.room,
        destination_identity=avatar_identity,
        wait_remote_track=rtc.TrackKind.KIND_VIDEO,
    )

    assistant = Assistant()
    assistant.watch_video(ctx.room)

    await session.start(
        room=ctx.room,
        agent=assistant,
        room_input_options=RoomInputOptions(
            # BVC noise cancellation requires a LiveKit Cloud entitlement that
            # isn't enabled on this project (it was timing out on every call
            # trying to fetch that config, adding delay) -- left off for now.
            video_enabled=True,
        ),
    )
    mark("session started")

    background_audio = BackgroundAudioPlayer(
        thinking_sound=[
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=1),
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=1),
        ],
    )
    await background_audio.start(room=ctx.room, agent_session=session)

    # Speak a fixed greeting rather than generating one. generate_reply() with
    # only instructions produces a context with no user message, and this
    # model's chat template rejects that outright:
    #   400 "minijinja: rendering failed: No user query found in messages"
    # A fixed line also removes an LLM round-trip from call startup.
    await session.say(
        "Hi, I'm your VoiceDesk AI support assistant. How can I help you today?",
        allow_interruptions=True,
    )
    mark("greeting sent")


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            # Run each job in its own process (the default on Linux/macOS; Windows
            # falls back to THREAD only because of an old BrokenPipeError bug).
            # Measured here: the same rtc.Room.connect() took ~44s inside the
            # thread-executor worker process vs ~5s in a fresh process.
            job_executor_type=agents.JobExecutorType.PROCESS,
            # NOTE: `agent.py dev` force-overrides the executor back to THREAD
            # (livekit/agents/cli/cli.py); run `agent.py start` to get PROCESS.
            # In `start` mode the worker refuses jobs above 70% CPU load by
            # default, which a busy dev laptop exceeds -- disable that gate.
            load_threshold=float("inf"),
            # Keep one executor pre-spawned and pre-warmed (VAD already loaded)
            # so the first call doesn't pay the model-load cost on its critical path.
            num_idle_processes=1,
            # The Silero VAD load in prewarm() can take well over the 10s default on
            # a slow/cold machine, which showed up as "error initializing process".
            initialize_process_timeout=120.0,
        )
    )