import { ArrowRight, BrainCircuit, FileText, ShieldCheck, Sparkles, BookOpen, Layers, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

const features = [
  {
    title: "Upload course material",
    description: "Start from PDFs, DOCX notes, or PPTX decks without changing your study workflow.",
    icon: FileText
  },
  {
    title: "AI exam pack generation",
    description: "Transform messy source files into structured summaries, questions, tips, and revision sheets.",
    icon: BrainCircuit
  },
  {
    title: "Export polished PDFs",
    description: "Finish with a clean study pack that is ready to revise, share, and download.",
    icon: ShieldCheck
  }
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-indigo-500/30 selection:text-white bg-grid-pattern relative overflow-x-hidden">
      {/* Soft Radial Ambient Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[600px] bg-[radial-gradient(ellipse_60%_60%_at_50%_-20%,rgba(99,102,241,0.12),rgba(255,255,255,0))] pointer-events-none z-0" />

      {/* Premium Minimal Navigation Bar */}
      <header className="sticky top-0 z-50 w-full border-b border-zinc-800/40 bg-zinc-950/70 backdrop-blur-md">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <Sparkles className="h-4.5 w-4.5 text-white" />
            </div>
            <span className="font-bold tracking-tight text-zinc-100 text-lg">Exam Slayer</span>
            <span className="text-[10px] font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/25 px-2 py-0.5 rounded-full">
              v2.0
            </span>
          </div>

          <nav className="hidden md:flex items-center gap-6 text-sm text-zinc-400 font-medium">
            <a href="#features" className="hover:text-zinc-100 transition-colors duration-300">Features</a>
            <a href="#preview" className="hover:text-zinc-100 transition-colors duration-300">Product</a>
            <a href="#faq" className="hover:text-zinc-100 transition-colors duration-300">Methodology</a>
          </nav>

          <div className="flex items-center gap-3">
            <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
              <Link to="/upload">Demo Flow</Link>
            </Button>
            <Button asChild size="sm">
              <Link to="/upload">
                Get Started
                <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="relative z-10">
        <section className="container mx-auto px-4 pt-20 pb-16 text-center">
          {/* Announcement Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-zinc-800 bg-zinc-900/60 text-xs text-zinc-400 mb-8 animate-fade-in">
            <span className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />
            <span>Powering next-gen OCR & study packs</span>
          </div>

          {/* Title */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-zinc-100 max-w-4xl mx-auto leading-[1.1] mb-6">
            Turn study files into{" "}
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 via-purple-400 to-indigo-300">
              exam-ready PDFs
            </span>
          </h1>

          {/* Description */}
          <p className="text-zinc-400 text-base sm:text-lg md:text-xl max-w-2xl mx-auto leading-relaxed mb-10">
            Upload notes, slides, and textbook PDFs. Exam Slayer automatically creates custom structured summaries, 
            targeted practice questions, exam tips, and a beautifully paginated PDF ready for review.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Button asChild size="lg" className="w-full sm:w-auto">
              <Link to="/upload">
                Upload materials
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="w-full sm:w-auto">
              <Link to="/processing/demo">View processing flow</Link>
            </Button>
          </div>

          {/* AI Product Preview / Mockup Container */}
          <div id="preview" className="relative max-w-4xl mx-auto mt-6 transition-all duration-300 hover:shadow-indigo-500/5 hover:shadow-2xl">
            <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/10 to-purple-600/5 rounded-xl blur-xl -z-10" />
            
            <div className="rounded-xl border border-zinc-800/40 bg-zinc-900/50 backdrop-blur-md overflow-hidden shadow-2xl">
              {/* Mockup Header Bar */}
              <div className="h-11 border-b border-zinc-800/50 bg-zinc-900/80 px-4 flex items-center justify-between">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-zinc-800" />
                  <div className="w-3 h-3 rounded-full bg-zinc-800" />
                  <div className="w-3 h-3 rounded-full bg-zinc-800" />
                </div>
                <div className="text-[11px] text-zinc-500 font-mono tracking-wider">EXAM-SLAYER-STUDY-PACK-V2</div>
                <div className="w-12" /> {/* Spacer */}
              </div>

              {/* Mockup Body Layout */}
              <div className="grid grid-cols-1 md:grid-cols-4 min-h-[360px] text-left text-xs text-zinc-400">
                {/* Left Sidebar */}
                <div className="border-r border-zinc-800/40 p-4 bg-zinc-900/30 space-y-4 col-span-1">
                  <div className="font-semibold text-zinc-300 tracking-tight uppercase text-[10px]">Source Files</div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 p-2 rounded-lg bg-zinc-800/60 border border-zinc-700/30 text-zinc-200">
                      <FileText className="h-3.5 w-3.5 text-indigo-400" />
                      <span className="truncate">Lecture_04_AI.pdf</span>
                    </div>
                    <div className="flex items-center gap-2 p-2 rounded-lg bg-zinc-900/20 border border-zinc-800/30">
                      <FileText className="h-3.5 w-3.5 text-zinc-500" />
                      <span className="truncate text-zinc-500">Reading_Material.docx</span>
                    </div>
                  </div>
                  <div className="h-px bg-zinc-800/40" />
                  <div className="space-y-1">
                    <span className="text-[10px] text-zinc-500 block">Current Status</span>
                    <span className="font-semibold text-indigo-400 flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-ping" />
                      OCR Completed
                    </span>
                  </div>
                </div>

                {/* Main Content Area */}
                <div className="p-5 md:col-span-2 space-y-4">
                  <div className="flex items-center justify-between border-b border-zinc-800/40 pb-3">
                    <div>
                      <h3 className="font-bold text-zinc-100 text-sm">Linear Algebra & AI Models</h3>
                      <p className="text-[10px] text-zinc-500">Generated Study Summary & Practice Pack</p>
                    </div>
                    <span className="text-[10px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded font-mono">
                      89% Match
                    </span>
                  </div>

                  <div className="space-y-3">
                    <div className="p-3 rounded-lg bg-zinc-800/30 border border-zinc-800/50">
                      <div className="font-bold text-zinc-300 mb-1 flex items-center gap-1">
                        <BookOpen className="h-3.5 w-3.5 text-indigo-400" /> Key Insights
                      </div>
                      <p className="leading-relaxed">
                        Backpropagation algorithm works by calculated gradients recursively of the cost function. Linear Algebra plays a vital role via tensor transformations.
                      </p>
                    </div>

                    <div className="p-3 rounded-lg bg-zinc-800/30 border border-zinc-800/50">
                      <div className="font-bold text-zinc-300 mb-1 flex items-center gap-1">
                        <Layers className="h-3.5 w-3.5 text-indigo-400" /> Auto-Generated Questions
                      </div>
                      <div className="space-y-1.5">
                        <div className="flex items-start gap-2">
                          <CheckCircle2 className="h-3.5 w-3.5 text-indigo-500 shrink-0 mt-0.5" />
                          <span>Define how gradient descent avoids local minima.</span>
                        </div>
                        <div className="flex items-start gap-2">
                          <CheckCircle2 className="h-3.5 w-3.5 text-indigo-500 shrink-0 mt-0.5" />
                          <span>Explain the difference between stochastic and batch optimization.</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Preview */}
                <div className="border-l border-zinc-800/40 p-4 bg-zinc-900/10 col-span-1 space-y-4 flex flex-col justify-between">
                  <div>
                    <div className="font-semibold text-zinc-300 tracking-tight uppercase text-[10px] mb-3">PDF Export</div>
                    <div className="aspect-[3/4] bg-zinc-950 rounded border border-zinc-800 p-2 flex flex-col justify-between shadow-inner">
                      <div className="space-y-1">
                        <div className="h-1.5 w-8/12 bg-zinc-800 rounded" />
                        <div className="h-1 w-full bg-zinc-900 rounded" />
                        <div className="h-1 w-10/12 bg-zinc-900 rounded" />
                        <div className="h-1 w-full bg-zinc-900 rounded" />
                      </div>
                      <div className="h-6 w-full bg-indigo-600/10 rounded flex items-center justify-center text-[8px] text-indigo-400 border border-indigo-500/25">
                        ExamSlayer_Pack.pdf
                      </div>
                    </div>
                  </div>
                  <Button size="sm" className="w-full text-[10px]">
                    Download Study Pack
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Grid Section */}
        <section id="features" className="container mx-auto px-4 py-24 border-t border-zinc-900/60 relative">
          <div className="max-w-2xl mx-auto text-center mb-16">
            <h2 className="text-3xl font-bold tracking-tight text-zinc-100 mb-4">
              Everything you need to master your syllabus
            </h2>
            <p className="text-zinc-400">
              Exam Slayer parses complex concepts and raw documents into clean, structured guides.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3 max-w-5xl mx-auto">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <article
                  key={feature.title}
                  className="rounded-xl border border-zinc-800/40 bg-zinc-900/50 backdrop-blur-md p-8 shadow-sm transition-all duration-300 hover:border-zinc-700/60 hover:translate-y-[-4px] hover:shadow-2xl hover:shadow-indigo-500/[0.02] group"
                >
                  <div className="mb-6 flex h-11 w-11 items-center justify-center rounded-lg bg-zinc-850 border border-zinc-800 text-indigo-400 group-hover:text-indigo-300 group-hover:border-indigo-500/30 transition-all duration-300">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-lg font-bold tracking-tight text-zinc-200 group-hover:text-zinc-100 transition-colors">
                    {feature.title}
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-zinc-400">
                    {feature.description}
                  </p>
                </article>
              );
            })}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-900/60 py-8 bg-zinc-950">
        <div className="container mx-auto px-4 flex flex-col sm:flex-row items-center justify-between text-xs text-zinc-500 gap-4">
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 rounded bg-zinc-800 flex items-center justify-center border border-zinc-750">
              <Sparkles className="h-3 w-3 text-zinc-400" />
            </div>
            <span>© 2026 Exam Slayer. All rights reserved.</span>
          </div>
          <div className="flex gap-6">
            <a href="#" className="hover:text-zinc-300 transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-zinc-300 transition-colors">Terms of Service</a>
            <a href="#" className="hover:text-zinc-300 transition-colors">Status</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
