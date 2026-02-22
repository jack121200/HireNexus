import { Link } from "react-router-dom";
import { motion } from "framer-motion";

import { Button } from "../components/Button";
import { Card } from "../components/Card";
import heroProduct from "../assets/landing/hero-product.svg";
import featureAi from "../assets/landing/feature-ai-interviewer.svg";
import featureResume from "../assets/landing/feature-resume-intel.svg";
import featureMatch from "../assets/landing/feature-job-match.svg";
import logoStrip from "../assets/landing/logo-strip.svg";
import testimonialPortrait from "../assets/landing/testimonial-portrait.svg";

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.2 },
};

export const Landing = () => {
  return (
    <div className="min-h-screen bg-ink text-text">
      <div className="relative overflow-hidden">
        <div className="absolute -top-32 left-10 h-72 w-72 rounded-full bg-accent/20 blur-[120px]" />
        <div className="absolute right-0 top-10 h-80 w-80 rounded-full bg-accentCool/20 blur-[140px]" />
        <div className="min-h-screen neo-aurora-bg">
          <div className="mx-auto flex max-w-6xl flex-col gap-20 px-6 py-12">
            <header className="flex flex-wrap items-center justify-between gap-4">
              <div className="font-display text-2xl font-semibold text-white">
                Hire<span className="text-gradient">Nexus</span>
              </div>
              <nav className="hidden items-center gap-6 text-sm text-textMuted md:flex">
                <a className="hover:text-white" href="#features">
                  Features
                </a>
                <a className="hover:text-white" href="#workflow">
                  Workflow
                </a>
                <a className="hover:text-white" href="#stories">
                  Stories
                </a>
              </nav>
              <div className="flex items-center gap-2">
                <Link to="/candidate/login">
                  <Button variant="ghost" size="sm">
                    Candidate Login
                  </Button>
                </Link>
                <Link to="/hr/login">
                  <Button variant="outline" size="sm">
                    HR Login
                  </Button>
                </Link>
              </div>
            </header>

            <motion.section {...fadeUp} className="grid items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
              <div className="space-y-6">
                <div className="inline-flex w-fit items-center gap-2 rounded-full border border-accent/40 bg-panel/70 px-4 py-2 text-xs uppercase tracking-[0.35em] text-textMuted">
                  AI Recruitment Suite
                </div>
                <h1 className="font-display text-4xl font-semibold text-white md:text-5xl">
                  Build interview-ready candidates and high-signal hiring teams with{" "}
                  <span className="text-gradient">Neo-Aurora</span> AI.
                </h1>
                <p className="max-w-2xl text-lg text-textMuted">
                  HireNexus blends resume intelligence, adaptive AI interviews, and live eligibility scoring so every
                  candidate knows exactly what to improve and every HR team hires faster.
                </p>
                <div className="flex flex-wrap gap-3">
                  <Link to="/candidate/register">
                    <Button size="lg" glow>
                      Start as Candidate
                    </Button>
                  </Link>
                  <Link to="/hr/register">
                    <Button variant="secondary" size="lg">
                      Launch HR Workspace
                    </Button>
                  </Link>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  {[
                    { label: "Resume Score", value: "Skill gaps + eligibility" },
                    { label: "AI Interviews", value: "Live scoring + feedback" },
                    { label: "Job Matches", value: "Confidence % per role" },
                  ].map((stat) => (
                    <Card key={stat.label} variant="muted" padding="sm" className="space-y-2">
                      <div className="text-xs uppercase tracking-[0.2em] text-textMuted">{stat.label}</div>
                      <div className="text-lg font-semibold text-white">{stat.value}</div>
                    </Card>
                  ))}
                </div>
              </div>

              <Card variant="glass" glow className="space-y-4">
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.3em] text-textMuted">
                  <span>Product Preview</span>
                  <span className="text-gradient">Live</span>
                </div>
                <img
                  src={heroProduct}
                  alt="HireNexus product preview"
                  className="w-full rounded-2xl border border-border/60 bg-panelMuted/60"
                />
                <div className="grid gap-3 md:grid-cols-3">
                  {[
                    "AI avatar interview room",
                    "Scorecards with confidence",
                    "Eligibility and gaps map",
                  ].map((item) => (
                    <div
                      key={item}
                      className="rounded-xl border border-border/60 bg-panelMuted/60 px-3 py-2 text-xs text-textMuted"
                    >
                      {item}
                    </div>
                  ))}
                </div>
              </Card>
            </motion.section>

            <motion.section {...fadeUp} className="space-y-6">
              <div className="text-center text-xs uppercase tracking-[0.4em] text-textMuted">
                Trusted by modern hiring teams
              </div>
              <img src={logoStrip} alt="Trusted teams" className="w-full opacity-80" />
            </motion.section>

            <motion.section id="features" {...fadeUp} className="space-y-8">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <div className="text-xs uppercase tracking-[0.4em] text-textMuted">Features</div>
                  <h2 className="font-display text-3xl font-semibold text-white">
                    A full-stack hiring advantage, from resume to offer.
                  </h2>
                </div>
                <p className="max-w-xl text-sm text-textMuted">
                  Candidates level up faster while recruiters get higher-quality pipelines with fewer interviews.
                </p>
              </div>
              <div className="grid gap-6 md:grid-cols-3">
                {[
                  {
                    title: "AI Interviewer",
                    body: "Human-style questioning, follow-ups, and instant skill scoring.",
                    image: featureAi,
                  },
                  {
                    title: "Resume Intelligence",
                    body: "Extract skills, compare to job descriptions, and prioritize the gaps.",
                    image: featureResume,
                  },
                  {
                    title: "Job Match Engine",
                    body: "See live eligibility percentages before you apply.",
                    image: featureMatch,
                  },
                ].map((feature) => (
                  <Card key={feature.title} variant="glass" className="space-y-4">
                    <img
                      src={feature.image}
                      alt={feature.title}
                      className="h-40 w-full rounded-xl border border-border/60 bg-panelMuted/60 object-cover"
                      loading="lazy"
                    />
                    <div className="text-lg font-semibold text-white">{feature.title}</div>
                    <p className="text-sm text-textMuted">{feature.body}</p>
                  </Card>
                ))}
              </div>
            </motion.section>

            <motion.section id="workflow" {...fadeUp} className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
              <Card variant="glass" className="space-y-6">
                <div>
                  <div className="text-xs uppercase tracking-[0.4em] text-textMuted">Workflow</div>
                  <h2 className="font-display text-2xl font-semibold text-white">
                    From upload to offer in four clear steps.
                  </h2>
                </div>
                <div className="grid gap-4">
                  {[
                    "Upload resume, extract strengths, highlight missing skills.",
                    "Paste job description to get tailored improvement moves.",
                    "Run adaptive mock interviews with instant scoring.",
                    "Track eligibility gains and apply with confidence.",
                  ].map((step, idx) => (
                    <div key={step} className="flex items-start gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent text-xs font-semibold text-white">
                        {idx + 1}
                      </div>
                      <div className="text-sm text-textMuted">{step}</div>
                    </div>
                  ))}
                </div>
              </Card>
              <Card variant="muted" className="space-y-5">
                <div className="text-sm uppercase tracking-[0.3em] text-textMuted">Outcome</div>
                <h3 className="text-2xl font-semibold text-white">
                  Candidates feel ready. HR teams move faster.
                </h3>
                <p className="text-sm text-textMuted">
                  Every report includes scores, confidence, strengths, missing skills, and tailored guidance. Use it
                  to coach, shortlist, and close roles quickly.
                </p>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-xl border border-border/60 bg-panelMuted/60 p-3 text-xs text-textMuted">
                    Average eligibility lift: 22%
                  </div>
                  <div className="rounded-xl border border-border/60 bg-panelMuted/60 p-3 text-xs text-textMuted">
                    Faster screening: 3x speed
                  </div>
                </div>
              </Card>
            </motion.section>

            <motion.section id="stories" {...fadeUp} className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
              <Card variant="glass" className="flex flex-col gap-6 md:flex-row md:items-center">
                <img
                  src={testimonialPortrait}
                  alt="Candidate testimonial portrait"
                  className="h-32 w-32 rounded-2xl border border-border/60 object-cover"
                  loading="lazy"
                />
                <div className="space-y-3">
                  <div className="text-xs uppercase tracking-[0.4em] text-textMuted">Candidate story</div>
                  <p className="text-lg text-white">
                    "The AI interviews felt real. I knew exactly how to improve before final round and landed the offer."
                  </p>
                  <div className="text-xs text-textMuted">Candidate, Full-Stack Engineer</div>
                </div>
              </Card>
              <Card variant="muted" className="space-y-4">
                <div className="text-xs uppercase tracking-[0.4em] text-textMuted">For HR teams</div>
                <h3 className="text-2xl font-semibold text-white">Signals you can trust.</h3>
                <p className="text-sm text-textMuted">
                  Replace guesswork with AI-generated scorecards and structured feedback. HireNexus helps you align
                  recruiters, hiring managers, and candidates on what matters.
                </p>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-xl border border-border/60 bg-panelMuted/60 p-3 text-xs text-textMuted">
                    Structured interview data
                  </div>
                  <div className="rounded-xl border border-border/60 bg-panelMuted/60 p-3 text-xs text-textMuted">
                    Confidence scoring
                  </div>
                  <div className="rounded-xl border border-border/60 bg-panelMuted/60 p-3 text-xs text-textMuted">
                    Missing skills map
                  </div>
                  <div className="rounded-xl border border-border/60 bg-panelMuted/60 p-3 text-xs text-textMuted">
                    Actionable next steps
                  </div>
                </div>
              </Card>
            </motion.section>

            <motion.section
              {...fadeUp}
              className="rounded-[32px] border border-accent/40 bg-panel/80 p-10 text-center shadow-glow"
            >
              <div className="mx-auto max-w-2xl space-y-4">
                <div className="text-xs uppercase tracking-[0.4em] text-textMuted">Ready to begin</div>
                <h2 className="font-display text-3xl font-semibold text-white">
                  Make every interview feel like a win.
                </h2>
                <p className="text-sm text-textMuted">
                  Start with a resume upload or launch your HR workspace in minutes.
                </p>
                <div className="flex flex-wrap justify-center gap-3">
                  <Link to="/candidate/register">
                    <Button size="lg" glow>
                      Join as Candidate
                    </Button>
                  </Link>
                  <Link to="/hr/register">
                    <Button size="lg" variant="secondary">
                      Create HR Workspace
                    </Button>
                  </Link>
                </div>
              </div>
            </motion.section>
          </div>
        </div>
      </div>
    </div>
  );
};
