import { useState, useRef, useEffect } from "react";
import { Button } from "../../components/Button";
import { apiFetch } from "../../lib/api";

/* ════════════════════════════════════════════════════════════════════════════
   CAREER INTELLIGENCE — Full RAG chatbot UI
   Features: Profile sidebar, intent badge, confidence, source URLs
   ════════════════════════════════════════════════════════════════════════════ */

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  intent?: string;
  confidence?: number;
};

type Source = {
  title: string;
  source: string;
  category: string;
  score: number;
};

type CareerResponse = {
  response: string;
  sources: Source[];
  query: string;
  intent: string;
  confidence: number;
};

type Profile = {
  skills: string;
  goal: string;
  level: string;
  current_role: string;
  target_role: string;
  industry: string;
};

const QUICK_PROMPTS = [
  { icon: "🗺️", text: "Frontend Developer roadmap for 2025" },
  { icon: "📝", text: "How to write a standout ATS resume" },
  { icon: "🎯", text: "Interview tips for FAANG companies" },
  { icon: "🤖", text: "How to become an ML Engineer" },
  { icon: "💰", text: "Salary negotiation strategies for freshers" },
  { icon: "🚀", text: "Best career path from software dev to product manager" },
];

const INTENT_COLORS: Record<string, string> = {
  resume: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  interview: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  salary: "bg-green-500/20 text-green-300 border-green-500/30",
  career_path: "bg-orange-500/20 text-orange-300 border-orange-500/30",
  skills: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
  job_search: "bg-pink-500/20 text-pink-300 border-pink-500/30",
  networking: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  general: "bg-gray-500/20 text-gray-300 border-gray-500/30",
};

function MarkdownContent({ content }: { content: string }) {
  const lines = content.split("\n");
  return (
    <div className="space-y-1 text-sm leading-relaxed">
      {lines.map((line, j) => {
        if (line.startsWith("### ")) return <h4 key={j} className="text-sm font-bold text-white mt-3 mb-1">{line.slice(4)}</h4>;
        if (line.startsWith("## ")) return <h3 key={j} className="text-base font-bold text-white mt-4 mb-1">{line.slice(3)}</h3>;
        if (line.startsWith("# ")) return <h2 key={j} className="text-lg font-bold text-white mt-4 mb-2">{line.slice(2)}</h2>;
        if (line.startsWith("**") && line.endsWith("**")) return <div key={j} className="font-semibold text-white mt-2">{line.replace(/\*\*/g, "")}</div>;
        if (line.startsWith("- ") || line.startsWith("* ")) return (
          <div key={j} className="flex gap-2 text-textMuted">
            <span className="text-accent mt-0.5">•</span>
            <span>{line.slice(2)}</span>
          </div>
        );
        if (/^\d+\.\s/.test(line)) return <div key={j} className="pl-3 text-textMuted">{line}</div>;
        if (!line.trim()) return <div key={j} className="h-2" />;
        return <div key={j} className="text-textMuted">{line}</div>;
      })}
    </div>
  );
}

export const CareerGuide = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [profile, setProfile] = useState<Profile>({
    skills: "", goal: "", level: "fresher",
    current_role: "", target_role: "", industry: "",
  });

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text?: string) => {
    const query = text ?? input.trim();
    if (!query || loading) return;

    const userMsg: Message = { role: "user", content: query };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const chatHistory = messages.map((m) => ({ role: m.role, content: m.content }));
      const skills = profile.skills ? profile.skills.split(",").map((s) => s.trim()).filter(Boolean) : undefined;

      const res = await apiFetch<CareerResponse>("/api/career-guide/ask", {
        method: "POST",
        body: JSON.stringify({
          query,
          skills,
          goal: profile.goal || undefined,
          level: profile.level || undefined,
          current_role: profile.current_role || undefined,
          target_role: profile.target_role || undefined,
          industry: profile.industry || undefined,
          chat_history: chatHistory.length > 0 ? chatHistory : undefined,
        }),
        auth: false,
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.response,
          sources: res.sources,
          intent: res.intent,
          confidence: res.confidence,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `❌ **Error:** ${(err as Error).message}. Make sure the backend is running and your Gemini API key is set.` },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const updateProfile = (key: keyof Profile, val: string) =>
    setProfile((p) => ({ ...p, [key]: val }));

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      {/* ── Header ── */}
      <div className="flex items-center justify-between pb-4 border-b border-border flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-text tracking-tight">Career Intelligence</h1>
          <p className="text-sm text-textMuted mt-0.5">
            RAG-powered engine — roadmaps, interview prep, salary insights
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-textDim border border-border rounded-full px-2 py-0.5">
            Gemini + Groq
          </span>
          <Button variant="secondary" size="sm" onClick={() => setShowProfile(!showProfile)}>
            {showProfile ? "Hide Profile" : "🎯 My Profile"}
          </Button>
        </div>
      </div>

      {/* ── Profile Panel ── */}
      {showProfile && (
        <div className="mt-3 rounded-xl border border-border bg-panel p-4 animate-fadeIn flex-shrink-0">
          <div className="text-xs font-semibold text-textMuted mb-3 uppercase tracking-wider">
            Your Profile — for personalized advice
          </div>
          <div className="grid sm:grid-cols-3 gap-3">
            {[
              { label: "Current Role", key: "current_role", placeholder: "e.g. Software Engineer" },
              { label: "Target Role", key: "target_role", placeholder: "e.g. ML Engineer" },
              { label: "Industry", key: "industry", placeholder: "e.g. FinTech" },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="text-xs text-textDim">{label}</label>
                <input
                  className="mt-1 w-full rounded-lg border border-border bg-panelMuted px-3 py-2 text-sm text-text outline-none focus:border-accent"
                  placeholder={placeholder}
                  value={profile[key as keyof Profile]}
                  onChange={(e) => updateProfile(key as keyof Profile, e.target.value)}
                />
              </div>
            ))}
            <div>
              <label className="text-xs text-textDim">Experience Level</label>
              <select
                className="mt-1 w-full rounded-lg border border-border bg-panelMuted px-3 py-2 text-sm text-text outline-none focus:border-accent"
                value={profile.level}
                onChange={(e) => updateProfile("level", e.target.value)}
              >
                <option value="fresher">Fresher (0-1 yr)</option>
                <option value="mid">Mid Level (2-5 yr)</option>
                <option value="senior">Senior (5+ yr)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-textDim">Career Goal</label>
              <input
                className="mt-1 w-full rounded-lg border border-border bg-panelMuted px-3 py-2 text-sm text-text outline-none focus:border-accent"
                placeholder="e.g. Get into FAANG"
                value={profile.goal}
                onChange={(e) => updateProfile("goal", e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-textDim">Your Skills (comma-separated)</label>
              <input
                className="mt-1 w-full rounded-lg border border-border bg-panelMuted px-3 py-2 text-sm text-text outline-none focus:border-accent"
                placeholder="React, Python, Docker..."
                value={profile.skills}
                onChange={(e) => updateProfile("skills", e.target.value)}
              />
            </div>
          </div>
        </div>
      )}

      {/* ── Chat ── */}
      <div className="flex-1 overflow-y-auto mt-4 space-y-4 scrollbar-thin pr-1">
        {/* Welcome */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center animate-fadeInUp">
            <div className="text-6xl mb-4">🧠</div>
            <h2 className="text-2xl font-bold text-text">Ask me anything about your career</h2>
            <p className="text-sm text-textMuted mt-2 max-w-md">
              Powered by RAG — I search a curated career knowledge base, then generate personalized advice with Gemini AI.
            </p>
            <div className="grid sm:grid-cols-2 gap-2 mt-6 max-w-xl">
              {QUICK_PROMPTS.map((p) => (
                <button
                  key={p.text}
                  onClick={() => sendMessage(p.text)}
                  className="text-left rounded-xl border border-border bg-panel px-4 py-3 text-sm text-textMuted hover:border-accent/50 hover:text-text transition-all flex gap-2 items-start"
                >
                  <span className="text-lg">{p.icon}</span>
                  <span>{p.text}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-fadeIn`}>
            <div
              className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === "user"
                  ? "bg-accent text-white rounded-br-sm"
                  : "bg-panel border border-border text-text rounded-bl-sm"
              }`}
            >
              {/* Intent + Confidence badges */}
              {msg.role === "assistant" && msg.intent && (
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-[10px] border rounded-full px-2 py-0.5 font-medium ${INTENT_COLORS[msg.intent] ?? INTENT_COLORS.general}`}>
                    {msg.intent.replace("_", " ")}
                  </span>
                  {msg.confidence !== undefined && (
                    <span className={`text-[10px] border rounded-full px-2 py-0.5 ${
                      msg.confidence >= 0.7 ? "bg-green-500/10 text-green-300 border-green-500/30"
                        : msg.confidence >= 0.4 ? "bg-yellow-500/10 text-yellow-300 border-yellow-500/30"
                        : "bg-red-500/10 text-red-300 border-red-500/30"
                    }`}>
                      {Math.round(msg.confidence * 100)}% confidence
                    </span>
                  )}
                </div>
              )}

              {msg.role === "assistant" ? (
                <MarkdownContent content={msg.content} />
              ) : (
                <span>{msg.content}</span>
              )}

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-2 border-t border-border/50">
                  <div className="text-[10px] text-textDim mb-1 font-medium uppercase tracking-wider">Sources</div>
                  <div className="flex flex-wrap gap-1">
                    {msg.sources.map((src, k) => (
                      <span
                        key={k}
                        className="rounded-lg bg-panelMuted border border-border/50 px-2 py-0.5 text-[10px] text-textDim"
                        title={`${src.title} — ${(src.score * 100).toFixed(0)}% match`}
                      >
                        {src.source} · {src.category}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading */}
        {loading && (
          <div className="flex justify-start animate-fadeIn">
            <div className="rounded-2xl bg-panel border border-border px-4 py-3 rounded-bl-sm">
              <div className="flex items-center gap-3">
                <div className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="h-2 w-2 rounded-full bg-accent animate-bounce"
                      style={{ animationDelay: `${i * 150}ms` }}
                    />
                  ))}
                </div>
                <span className="text-xs text-textMuted">Searching knowledge base & generating response…</span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input Bar ── */}
      <div className="mt-4 pt-4 border-t border-border flex-shrink-0">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            className="flex-1 rounded-xl border border-border bg-panelMuted px-4 py-2.5 text-sm text-text outline-none transition-all focus:border-accent focus:ring-2 focus:ring-accent/20"
            placeholder="Ask about career paths, skills, interviews, salary…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
            disabled={loading}
          />
          <Button onClick={() => sendMessage()} disabled={!input.trim() || loading}>
            Send ↵
          </Button>
        </div>
        <div className="text-[11px] text-textDim mt-2 text-center">
          RAG + Gemini AI · Searches curated career knowledge base · Results may vary
        </div>
      </div>
    </div>
  );
};
