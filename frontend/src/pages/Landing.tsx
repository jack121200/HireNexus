import { Link } from "react-router-dom";
import { Button } from "../components/Button";

/* ════════════════════════════════════════════════════════════════════════════
   LANDING PAGE — Midnight Prism Theme (Vercel + Linear inspired)
   ════════════════════════════════════════════════════════════════════════════ */

const FEATURES = [
  {
    icon: "🤖",
    title: "AI-Powered Interviews",
    description: "Real-time voice interviews with natural AI that listens, responds, and scores your answers instantly.",
  },
  {
    icon: "📊",
    title: "Smart Scoring Engine",
    description: "Multi-dimensional scoring using semantic similarity, technical depth, and rubric coverage.",
  },
  {
    icon: "🧠",
    title: "Career Intelligence",
    description: "RAG-based career guidance chatbot that gives personalized roadmaps, skill gaps, and career advice.",
  },
  {
    icon: "📝",
    title: "Resume Analysis",
    description: "AI-powered resume parsing and eligibility scoring against job descriptions.",
  },
  {
    icon: "🎯",
    title: "Job Matching",
    description: "Intelligent matching between candidates and positions based on skills, experience, and preferences.",
  },
  {
    icon: "⚡",
    title: "Real-time Experience",
    description: "Live transcription, instant feedback, and WebSocket-powered notifications throughout.",
  },
];

const STATS = [
  { value: "94%", label: "STT Accuracy", description: "AssemblyAI streaming" },
  { value: "<1s", label: "AI Response", description: "Cached TTS + streaming" },
  { value: "3x", label: "Faster Screening", description: "vs manual interviews" },
  { value: "15+", label: "Career Paths", description: "RAG knowledge base" },
];

const WORKFLOW_STEPS = [
  {
    step: "01",
    title: "Post a Job",
    description: "HR posts job description with skills, experience requirements, and rubric criteria.",
  },
  {
    step: "02",
    title: "AI Matches Candidates",
    description: "System scores resume eligibility and ranks candidates automatically.",
  },
  {
    step: "03",
    title: "Live AI Interview",
    description: "Candidates take a real-time voice interview with the AI interviewer.",
  },
  {
    step: "04",
    title: "Instant Report",
    description: "Detailed scoring report generated instantly with per-question breakdown.",
  },
];

export const Landing = () => {
  return (
    <div className="min-h-screen bg-ink text-text page-enter">
      {/* ── Ambient glow ──────────────────────────────────────────────────── */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-accent/5 rounded-full blur-[120px]" />
      </div>

      <div className="relative">
        <div className="mx-auto max-w-6xl px-6">

          {/* ════ HEADER ═══════════════════════════════════════════════════ */}
          <header className="flex items-center justify-between py-6">
            <Link to="/" className="font-display text-xl font-bold text-text tracking-tight">
              Hire<span className="text-accent">Nexus</span>
            </Link>

            <nav className="hidden md:flex items-center gap-8 text-sm text-textMuted">
              <a href="#features" className="hover:text-text transition-colors">Features</a>
              <a href="#workflow" className="hover:text-text transition-colors">How it Works</a>
              <a href="#stats" className="hover:text-text transition-colors">Stats</a>
            </nav>

            <div className="flex items-center gap-3">
              <Link to="/candidate/login">
                <Button variant="ghost" size="sm">Sign In</Button>
              </Link>
              <Link to="/hr/login">
                <Button variant="primary" size="sm">HR Portal →</Button>
              </Link>
            </div>
          </header>

          {/* ════ HERO ═════════════════════════════════════════════════════ */}
          <section className="py-24 md:py-32 text-center max-w-3xl mx-auto">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 rounded-full border border-border bg-panelMuted px-4 py-1.5 text-xs text-textMuted mb-8 animate-fadeIn">
              <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
              AI-powered hiring platform
            </div>

            {/* Headline */}
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-text tracking-tight leading-[1.1] animate-fadeInUp">
              Hire smarter with{" "}
              <span className="text-gradient">AI interviews</span>
            </h1>

            <p className="mt-6 text-lg md:text-xl text-textMuted max-w-xl mx-auto leading-relaxed animate-fadeInUp" style={{ animationDelay: "80ms" }}>
              Real-time voice interviews, intelligent scoring, and career guidance — all in one platform.
            </p>

            {/* CTA */}
            <div className="flex flex-wrap items-center justify-center gap-4 mt-10 animate-fadeInUp" style={{ animationDelay: "160ms" }}>
              <Link to="/candidate/register">
                <Button variant="primary" size="lg">Get Started — Free</Button>
              </Link>
              <Link to="/hr/register">
                <Button variant="outline" size="lg">For Recruiters →</Button>
              </Link>
            </div>

            {/* Trusted by label */}
            <div className="mt-16 text-xs text-textDim animate-fadeIn" style={{ animationDelay: "300ms" }}>
              Built with FastAPI · React · AWS Polly · Gemini AI · AssemblyAI
            </div>
          </section>

          {/* ════ STATS BAR ══════════════════════════════════════════════════ */}
          <section id="stats" className="py-16 border-t border-border">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
              {STATS.map((stat) => (
                <div key={stat.label} className="text-center group">
                  <div className="text-3xl md:text-4xl font-bold text-text group-hover:text-accent transition-colors">
                    {stat.value}
                  </div>
                  <div className="mt-1 text-sm font-medium text-textMuted">{stat.label}</div>
                  <div className="mt-0.5 text-xs text-textDim">{stat.description}</div>
                </div>
              ))}
            </div>
          </section>

          {/* ════ FEATURES ════════════════════════════════════════════════════ */}
          <section id="features" className="py-20 border-t border-border">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-text tracking-tight">
                Everything you need
              </h2>
              <p className="mt-4 text-textMuted max-w-lg mx-auto">
                A complete AI hiring platform, from job posting to interview scoring.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {FEATURES.map((feature) => (
                <div
                  key={feature.title}
                  className="group rounded-xl border border-border bg-panel p-6 card-interactive"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-panelMuted border border-border text-xl mb-4 group-hover:border-accent/30 transition-colors">
                    {feature.icon}
                  </div>
                  <h3 className="text-sm font-semibold text-text">{feature.title}</h3>
                  <p className="mt-2 text-sm text-textMuted leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </section>

          {/* ════ HOW IT WORKS ════════════════════════════════════════════════ */}
          <section id="workflow" className="py-20 border-t border-border">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-text tracking-tight">
                How it works
              </h2>
              <p className="mt-4 text-textMuted max-w-lg mx-auto">
                From job posting to hiring decision — 4 simple steps.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {WORKFLOW_STEPS.map((item) => (
                <div key={item.step} className="relative">
                  {/* Step number */}
                  <div className="text-6xl font-bold text-border/40 font-display">{item.step}</div>
                  <h3 className="mt-2 text-sm font-semibold text-text">{item.title}</h3>
                  <p className="mt-2 text-sm text-textMuted leading-relaxed">{item.description}</p>
                </div>
              ))}
            </div>
          </section>

          {/* ════ CTA SECTION ═════════════════════════════════════════════════ */}
          <section className="py-20 border-t border-border">
            <div className="rounded-2xl border border-border bg-panel p-12 md:p-16 text-center gradient-border">
              <h2 className="text-3xl md:text-4xl font-bold text-text tracking-tight">
                Ready to transform hiring?
              </h2>
              <p className="mt-4 text-textMuted max-w-md mx-auto">
                Start conducting AI-powered interviews today. No credit card required.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-4 mt-8">
                <Link to="/candidate/register">
                  <Button variant="primary" size="lg">Start Free Trial</Button>
                </Link>
                <Link to="/hr/register">
                  <Button variant="secondary" size="lg">Contact Sales</Button>
                </Link>
              </div>
            </div>
          </section>

          {/* ════ FOOTER ══════════════════════════════════════════════════════ */}
          <footer className="py-10 border-t border-border flex flex-wrap items-center justify-between gap-4">
            <div className="font-display text-sm font-bold text-textMuted">
              Hire<span className="text-accent">Nexus</span>
            </div>
            <div className="flex items-center gap-6 text-xs text-textDim">
              <span>© {new Date().getFullYear()} HireNexus</span>
              <a href="#" className="hover:text-textMuted transition-colors">Privacy</a>
              <a href="#" className="hover:text-textMuted transition-colors">Terms</a>
            </div>
          </footer>

        </div>
      </div>
    </div>
  );
};
