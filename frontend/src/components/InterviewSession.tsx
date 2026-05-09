import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Vapi from "@vapi-ai/web";
import type { CreateAssistantDTO } from "@vapi-ai/web/dist/api";
import { apiFetch } from "../lib/api";

const VAPI_PUBLIC_KEY = import.meta.env.VITE_VAPI_PUBLIC_KEY as string | undefined;

// ── Module-level singleton — prevents KrispSDK double-init (React Strict Mode) ─
let _vapiInstance: InstanceType<typeof Vapi> | null = null;

function getVapi(): InstanceType<typeof Vapi> | { error: string } {
  if (!VAPI_PUBLIC_KEY)
    return { error: "VITE_VAPI_PUBLIC_KEY is not configured in frontend/.env" };
  if (!_vapiInstance) {
    try {
      const VapiClass = ((Vapi as unknown as { default?: typeof Vapi }).default) ?? Vapi;
      _vapiInstance = new VapiClass(VAPI_PUBLIC_KEY);
    } catch (e) {
      return { error: e instanceof Error ? e.message : "Vapi SDK init failed." };
    }
  }
  return _vapiInstance;
}

// ── Types ─────────────────────────────────────────────────────────────────────
interface StartVapiResponse {
  interview_id: number;
  system_prompt: string;
  first_message: string;
  role_name: string;
  interview_type: string;
  candidate_name: string;
  duration_minutes: string;
  tags: string[];
}

interface TranscriptLine {
  role: "assistant" | "user";
  text: string;
  time: string;
}

// ── Waveform bars — animated when AI is speaking ──────────────────────────────
const WaveformBars = ({ active }: { active: boolean }) => (
  <div className="flex items-end justify-center gap-[3px] h-10">
    {[0.4, 0.7, 1, 0.8, 0.5, 0.9, 0.6, 1, 0.7, 0.4].map((h, i) => (
      <div
        key={i}
        className="w-[3px] rounded-full transition-all duration-150"
        style={{
          height: active ? `${h * 38}px` : "4px",
          background: active ? `hsl(${220 + i * 5}, 100%, 70%)` : "rgba(255,255,255,0.15)",
          // Use individual animation props — never mix with animationDelay shorthand
          animationName: active ? "waveBar" : "none",
          animationDuration: `${0.6 + i * 0.07}s`,
          animationTimingFunction: "ease-in-out",
          animationIterationCount: "infinite",
          animationDirection: "alternate",
          animationDelay: `${i * 0.05}s`,
        }}
      />
    ))}
    <style>{`@keyframes waveBar { from { transform: scaleY(0.4); } to { transform: scaleY(1); } }`}</style>
  </div>
);

// ── Timer hook ────────────────────────────────────────────────────────────────
function useTimer(running: boolean) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [running]);
  const m = String(Math.floor(seconds / 60)).padStart(2, "0");
  const s = String(seconds % 60).padStart(2, "0");
  return `${m}:${s}`;
}

// ── Main Component ─────────────────────────────────────────────────────────────
export const InterviewSession = ({ interviewId }: { interviewId: number }) => {
  const navigate = useNavigate();
  const listenersAdded = useRef(false);
  const transcriptRef = useRef<HTMLDivElement>(null);

  const [status, setStatus] = useState<"idle" | "connecting" | "active" | "ended" | "error">("idle");
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [aiSpeaking, setAiSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState<StartVapiResponse | null>(null);
  const [volume, setVolume] = useState(0);

  const timer = useTimer(status === "active");

  // Auto-scroll transcript
  useEffect(() => {
    transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight, behavior: "smooth" });
  }, [transcript]);

  // ── Attach Vapi listeners ────────────────────────────────────────────────────
  useEffect(() => {
    const vapiOrErr = getVapi();
    if ("error" in vapiOrErr) { setError(vapiOrErr.error); setStatus("error"); return; }
    const vapi = vapiOrErr;
    if (listenersAdded.current) return;
    listenersAdded.current = true;

    const onStart = () => { setStatus("active"); setError(null); };
    const onEnd = () => setStatus("ended");
    const onSpeechStart = () => setAiSpeaking(true);
    const onSpeechEnd = () => { setAiSpeaking(false); setVolume(0); };
    const onVolume = (v: number) => setVolume(v);
    const onError = (e: unknown) => {
      // Vapi v2 error shape: { action: 'error', errorMsg: string, error: {...}, callClientId: string }
      const errObj = e as { errorMsg?: unknown; error?: { message?: unknown } } | null;
      const rawMsg = errObj?.errorMsg ?? errObj?.error?.message ?? "";
      const msg = typeof rawMsg === "string" ? rawMsg : JSON.stringify(rawMsg ?? "");

      // Swallow the harmless Strict Mode first-mount ejection
      if (msg.includes("Meeting has ended") || msg.includes("ejection")) return;

      if (msg) {
        console.error("[Vapi]", e);
        setError(msg);
        setStatus("error");
      }
    };
    const onMessage = (msg: unknown) => {
      const m = msg as { type?: string; transcriptType?: string; role?: string; transcript?: string };
      if (m?.type === "transcript" && m?.transcriptType === "final" && m.transcript && m.role) {
        setTranscript((prev) => [
          ...prev,
          { role: m.role as "assistant" | "user", text: m.transcript!, time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) },
        ]);
      }
    };

    vapi.on("call-start", onStart);
    vapi.on("call-end", onEnd);
    vapi.on("speech-start", onSpeechStart);
    vapi.on("speech-end", onSpeechEnd);
    vapi.on("volume-level", onVolume);
    vapi.on("error", onError);
    vapi.on("message", onMessage);

    return () => {
      vapi.removeListener("call-start", onStart);
      vapi.removeListener("call-end", onEnd);
      vapi.removeListener("speech-start", onSpeechStart);
      vapi.removeListener("speech-end", onSpeechEnd);
      vapi.removeListener("volume-level", onVolume);
      vapi.removeListener("error", onError);
      vapi.removeListener("message", onMessage);
      listenersAdded.current = false;
    };
  }, []);

  // ── Start interview ───────────────────────────────────────────────────────────
  const startInterview = async () => {
    const vapiOrErr = getVapi();
    if ("error" in vapiOrErr) { setError(vapiOrErr.error); return; }
    setStatus("connecting");
    setError(null);

    try {
      const config = await apiFetch<StartVapiResponse>(
        `/api/candidate/interviews/${interviewId}/start-vapi`,
        { method: "POST", body: JSON.stringify({}) }
      );
      setMeta(config);

      const assistantConfig: CreateAssistantDTO = {
        name: "Sarah",
        firstMessage: config.first_message,
        model: {
          provider: "openai",
          model: "gpt-4.1-mini",
          temperature: 0.6,
          maxTokens: 200,
          messages: [{ role: "system", content: config.system_prompt }],
          tools: [{ type: "endCall" }],
        },
        voice: {
          provider: "deepgram",
          voiceId: "luna",
          model: "aura-2",
        },
        transcriber: {
          provider: "deepgram",
          model: "nova-2",
          language: "en",
        },
        // ── Relaxed timing so AI doesn't jump in while you think ─────────────
        startSpeakingPlan: {
          waitSeconds: 1.0,          // Wait 1 FULL second of silence before Sarah replies
          smartEndpointingEnabled: false, // Turn off guessing sentence endings
        },
        stopSpeakingPlan: {
          numWords: 3,               // Need 3 clear words from you to make Sarah stop talking
          voiceSeconds: 0.4,
          backoffSeconds: 1.0,
        },
        endCallPhrases: [
          "thank you for your time",
          "interview is now complete",
          "we'll be in touch",
          "that concludes our interview",
          "best of luck",
        ],
        maxDurationSeconds: 1800,
        backgroundSound: "off",
      };

      await vapiOrErr.start(assistantConfig);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to start.";
      console.error(err);
      setError(msg);
      setStatus("idle");
    }
  };

  const endInterview = () => {
    const vapi = getVapi();
    if (!("error" in vapi)) { try { vapi.stop(); } catch { /* */ } }
    setStatus("ended");
  };

  // ── Latest transcript line ────────────────────────────────────────────────────
  const lastLine = transcript[transcript.length - 1];

  const candidateInitials = (meta?.candidate_name ?? "You")
    .split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  // ── PRE-START SCREEN ─────────────────────────────────────────────────────────
  if (status === "idle" || status === "connecting" || status === "error") {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-4"
        style={{ background: "radial-gradient(ellipse 80% 60% at 50% 0%, #0f1a36 0%, #050a14 100%)" }}
      >
        <div className="w-full max-w-xl space-y-8 text-center">
          {/* Icon */}
          <div className="flex justify-center">
            <div className="relative">
              <div className="h-24 w-24 rounded-2xl bg-gradient-to-br from-indigo-500/30 to-purple-600/20 border border-indigo-500/30 flex items-center justify-center text-5xl shadow-[0_0_60px_rgba(99,102,241,0.3)]">
                🤖
              </div>
              <span className="absolute -bottom-2 -right-2 h-6 w-6 rounded-full bg-indigo-500 border-2 border-[#050a14] flex items-center justify-center">
                <span className="h-2 w-2 rounded-full bg-white" />
              </span>
            </div>
          </div>

          <div>
            <h1 className="text-2xl font-bold text-white">AI Interview Session</h1>
            <p className="text-textMuted text-sm mt-2">
              Jordan, your AI interviewer, will ask you role-specific questions based on your resume.
            </p>
          </div>

          {error && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              ⚠ {error}
            </div>
          )}

          {/* Checklist */}
          <div className="rounded-xl border border-white/5 bg-white/5 backdrop-blur-sm p-5 text-left space-y-3">
            {[
              { icon: "🎙️", label: "Allow microphone access when prompted" },
              { icon: "🔇", label: "Find a quiet room with minimal background noise" },
              { icon: "⏱️", label: "The session is ~30 minutes — don't close this tab" },
              { icon: "💡", label: "Speak clearly and take your time to answer" },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-3 text-sm text-textMuted">
                <span className="text-base">{item.icon}</span>
                {item.label}
              </div>
            ))}
          </div>

          <button
            onClick={startInterview}
            disabled={status === "connecting"}
            className="w-full py-4 rounded-2xl text-sm font-semibold text-white transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
            style={{
              background: status === "connecting"
                ? "rgba(99,102,241,0.4)"
                : "linear-gradient(135deg, #6366f1, #8b5cf6)",
              boxShadow: status === "connecting" ? "none" : "0 0 30px rgba(99,102,241,0.4)",
            }}
          >
            {status === "connecting" ? (
              <span className="flex items-center justify-center gap-2">
                <span className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                Connecting…
              </span>
            ) : (
              "Begin Interview →"
            )}
          </button>
        </div>
      </div>
    );
  }

  // ── ENDED SCREEN ──────────────────────────────────────────────────────────────
  if (status === "ended") {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-4"
        style={{ background: "radial-gradient(ellipse 80% 60% at 50% 0%, #0a1f10 0%, #050a14 100%)" }}
      >
        <div className="w-full max-w-lg text-center space-y-6">
          <div className="text-6xl">✅</div>
          <h1 className="text-2xl font-bold text-white">Interview Complete!</h1>
          <p className="text-textMuted text-sm">
            Great job! Your responses are being analysed. You'll receive a detailed score report once processing is complete.
          </p>
          {transcript.length > 0 && (
            <div className="text-left rounded-xl border border-white/10 bg-white/5 p-4 max-h-48 overflow-y-auto space-y-2">
              <div className="text-xs uppercase tracking-wider text-textMuted/60 mb-2">Session Transcript</div>
              {transcript.map((t, i) => (
                <div key={i} className={`text-sm ${t.role === "assistant" ? "text-indigo-300" : "text-white"}`}>
                  <span className="text-[10px] text-white/30 mr-2">{t.time}</span>
                  <span className="font-medium mr-1">{t.role === "assistant" ? "Jordan:" : "You:"}</span>
                  {t.text}
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => navigate("/candidate/interviews")}
              className="px-6 py-3 rounded-xl text-sm font-medium border border-white/20 text-white hover:bg-white/10 transition-colors"
            >
              View All Interviews
            </button>
            <button
              onClick={() => navigate("/candidate/dashboard")}
              className="px-6 py-3 rounded-xl text-sm font-medium text-white transition-all"
              style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── ACTIVE CALL SCREEN ────────────────────────────────────────────────────────
  return (
    <div
      className="fixed inset-0 z-50 flex flex-col"
      style={{ background: "radial-gradient(ellipse 80% 50% at 50% -10%, #0f1a36 0%, #05080f 70%)" }}
    >
      {/* ── Top bar ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-sm">🤖</div>
          <div>
            <span className="text-white font-semibold text-sm">
              {meta?.role_name ?? "AI Interview"}
            </span>
            <span className="ml-2 text-[11px] px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-textMuted capitalize">
              {meta?.interview_type ?? "technical"}
            </span>
          </div>
          {/* Tech tags */}
          <div className="flex items-center gap-1.5 ml-1">
            {(meta?.tags ?? []).slice(0, 3).map((tag) => (
              <span key={tag} className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/15 border border-indigo-500/25 text-indigo-300 font-medium">
                {tag}
              </span>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Timer */}
          <div className="flex items-center gap-2 text-sm font-mono">
            <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-white/70">{timer}</span>
          </div>
          {/* Status */}
          <div className="text-[11px] px-3 py-1 rounded-full border border-green-500/30 bg-green-500/10 text-green-400 font-medium">
            Live
          </div>
        </div>
      </div>

      {/* ── Two cards ─────────────────────────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center px-6 py-6 gap-5">
        {/* AI Interviewer Card */}
        <div
          className="relative flex-1 max-w-lg h-72 rounded-2xl flex flex-col items-center justify-center gap-5 transition-all duration-300"
          style={{
            background: "linear-gradient(145deg, rgba(99,102,241,0.12) 0%, rgba(10,14,30,0.9) 100%)",
            border: aiSpeaking
              ? "1.5px solid rgba(99,102,241,0.7)"
              : "1.5px solid rgba(255,255,255,0.08)",
            boxShadow: aiSpeaking
              ? "0 0 40px rgba(99,102,241,0.25), inset 0 0 30px rgba(99,102,241,0.05)"
              : "none",
          }}
        >
          {/* Glow when speaking */}
          {aiSpeaking && (
            <div className="absolute inset-0 rounded-2xl pointer-events-none"
              style={{ background: "radial-gradient(ellipse 60% 60% at 50% 50%, rgba(99,102,241,0.08) 0%, transparent 70%)" }}
            />
          )}

          {/* AI Avatar */}
          <div
            className="relative h-20 w-20 rounded-full flex items-center justify-center transition-all duration-300"
            style={{
              background: aiSpeaking
                ? "linear-gradient(135deg, #6366f1, #8b5cf6)"
                : "linear-gradient(135deg, rgba(99,102,241,0.3), rgba(139,92,246,0.2))",
              boxShadow: aiSpeaking ? "0 0 0 8px rgba(99,102,241,0.15), 0 0 0 16px rgba(99,102,241,0.06)" : "none",
            }}
          >
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              <circle cx="9" cy="10" r="1" fill="white" stroke="none" />
              <circle cx="12" cy="10" r="1" fill="white" stroke="none" />
              <circle cx="15" cy="10" r="1" fill="white" stroke="none" />
            </svg>
          </div>

          {/* Waveform */}
          <WaveformBars active={aiSpeaking} />

          <div className="text-center">
            <div className="text-white font-semibold text-sm">Jordan</div>
            <div className="text-xs text-indigo-300/70 mt-0.5">AI Interviewer · HireNexus</div>
          </div>

          {aiSpeaking && (
            <div className="absolute top-3 right-3 flex items-center gap-1.5 text-[10px] font-medium text-indigo-300">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
              Speaking
            </div>
          )}
        </div>

        {/* Candidate Card */}
        <div
          className="relative flex-1 max-w-lg h-72 rounded-2xl flex flex-col items-center justify-center gap-5 transition-all duration-300"
          style={{
            background: "linear-gradient(145deg, rgba(255,255,255,0.04) 0%, rgba(10,14,30,0.9) 100%)",
            border: !aiSpeaking && status === "active"
              ? "1.5px solid rgba(255,255,255,0.2)"
              : "1.5px solid rgba(255,255,255,0.07)",
            boxShadow: !aiSpeaking && status === "active"
              ? "0 0 30px rgba(255,255,255,0.06)"
              : "none",
          }}
        >
          {/* Candidate Avatar */}
          <div
            className="relative h-20 w-20 rounded-full flex items-center justify-center text-white font-bold text-2xl transition-all duration-300"
            style={{
              background: "linear-gradient(135deg, #1e293b, #334155)",
              boxShadow: !aiSpeaking
                ? `0 0 0 ${Math.round(volume * 12)}px rgba(255,255,255,0.06), 0 0 0 ${Math.round(volume * 22)}px rgba(255,255,255,0.03)`
                : "none",
            }}
          >
            {candidateInitials}
          </div>

          {/* User waveform — flips when AI isn't speaking */}
          <WaveformBars active={!aiSpeaking && status === "active"} />

          <div className="text-center">
            <div className="text-white font-semibold text-sm">{meta?.candidate_name ?? "You"}</div>
            <div className="text-xs text-white/40 mt-0.5">Candidate</div>
          </div>

          {!aiSpeaking && status === "active" && (
            <div className="absolute top-3 right-3 flex items-center gap-1.5 text-[10px] font-medium text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Your turn
            </div>
          )}
        </div>
      </div>

      {/* ── Bottom bar ───────────────────────────────────────────────────────── */}
      <div className="border-t border-white/5 px-6 py-4">
        {/* Latest transcript line */}
        <div
          className="mx-auto max-w-2xl mb-4 min-h-[2.5rem] flex items-center justify-center rounded-xl px-5 py-2.5 text-sm text-center transition-all duration-500"
          style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }}
        >
          {lastLine ? (
            <span className={lastLine.role === "assistant" ? "text-indigo-200" : "text-white"}>
              <span className="font-semibold mr-1">{lastLine.role === "assistant" ? "Jordan:" : "You:"}</span>
              {lastLine.text}
            </span>
          ) : (
            <span className="text-white/30 text-xs">Transcript will appear here…</span>
          )}
        </div>

        {/* Controls */}
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={endInterview}
            className="flex items-center gap-2 px-6 py-3 rounded-full text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
            style={{ background: "linear-gradient(135deg, #ef4444, #dc2626)", boxShadow: "0 4px 20px rgba(239,68,68,0.35)" }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
            End Interview
          </button>
        </div>
      </div>
    </div>
  );
};
