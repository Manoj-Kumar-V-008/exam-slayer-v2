import { ArrowRight, BrainCircuit, FileText, Sparkles, BookOpen, Layers, CheckCircle2, ChevronRight } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Navbar } from "@/components/Navbar";

export function LandingPage() {
  const navigate = useNavigate();

  const handleSelectMode = (mode: "STUDY_PACK" | "ANSWER_PACK") => {
    navigate("/upload", { state: { initialMode: mode } });
  };

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/20 selection:text-primary bg-grid-pattern relative overflow-x-hidden transition-colors duration-300">
      {/* Soft Radial Ambient Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[600px] bg-[radial-gradient(ellipse_60%_60%_at_50%_-20%,rgba(99,102,241,0.15),transparent)] pointer-events-none z-0 dark:opacity-70 opacity-40" />

      {/* Shared Navigation Header */}
      <Navbar />

      <main className="relative z-10">
        {/* Hero Section */}
        <section className="container mx-auto px-4 pt-20 pb-16 text-center max-w-5xl">
          {/* Announcement Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border bg-card/50 text-xs text-muted-foreground mb-8 backdrop-blur-sm shadow-sm">
            <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
            <span>Dual-Mode AI Engine V2.0 Active</span>
          </div>

          {/* Title */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight max-w-4xl mx-auto leading-[1.1] mb-6">
            Conquer your syllabus with{" "}
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 dark:from-indigo-400 dark:via-purple-400 dark:to-indigo-300">
              Exam Slayer
            </span>
          </h1>

          {/* Description */}
          <p className="text-muted-foreground text-base sm:text-lg md:text-xl max-w-2xl mx-auto leading-relaxed mb-10">
            Transform messy lecture notes, slides, and textbooks into structured, conceptual study guides, or upload a question bank to get immediate, exam-ready solved answer keys.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-20">
            <Button asChild size="lg" className="w-full sm:w-auto font-semibold px-8 shadow-lg shadow-indigo-600/10">
              <Link to="/upload">
                Get Started Free
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="w-full sm:w-auto font-semibold px-8 border-border/80">
              <a href="#modes">Explore Product Modes</a>
            </Button>
          </div>

          {/* Dual Product Modes Selector Section */}
          <div id="modes" className="py-8 scroll-mt-20">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight mb-3">Select Your Preparation Pathway</h2>
            <p className="text-muted-foreground text-sm max-w-lg mx-auto mb-10">
              Choose the mode that fits your immediate study needs.
            </p>

            <div className="grid gap-6 md:grid-cols-2 max-w-4xl mx-auto text-left">
              {/* STUDY_PACK Card */}
              <div 
                onClick={() => handleSelectMode("STUDY_PACK")}
                className="group relative rounded-2xl border border-border bg-card/30 hover:bg-card/75 p-8 transition-all duration-300 hover:border-primary/50 cursor-pointer shadow-sm hover:shadow-xl hover:shadow-indigo-500/[0.02] hover:-translate-y-1 backdrop-blur-sm overflow-hidden"
              >
                <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/5 group-hover:bg-indigo-500/10 blur-xl rounded-full transition-colors" />
                
                <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-500 dark:text-indigo-400 group-hover:scale-110 transition-transform duration-300">
                  <BookOpen className="h-6 w-6" />
                </div>
                
                <span className="text-[10px] font-bold tracking-widest text-indigo-500 dark:text-indigo-400 uppercase">MODE 01</span>
                <h3 className="text-xl font-bold mt-2 text-foreground group-hover:text-primary transition-colors flex items-center gap-2">
                  Study Guide Pack
                  <ChevronRight className="h-4 w-4 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                </h3>
                
                <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                  Transform raw textbooks, transcripts, and presentation decks into a master study guide. Perfect for understanding concepts and early-stage revision.
                </p>

                <ul className="mt-6 space-y-2.5 text-xs text-muted-foreground border-t border-border/40 pt-5">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-indigo-500 shrink-0" />
                    <span>Intuitive conceptual summaries & analogies</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-indigo-500 shrink-0" />
                    <span>Mnemonic devices & memory tricks</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-indigo-500 shrink-0" />
                    <span>Predictive 2, 5, and 10 mark exam questions</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-indigo-500 shrink-0" />
                    <span>Clean study sheets & common pitfalls list</span>
                  </li>
                </ul>

                <div className="mt-8 pt-4">
                  <span className="text-xs font-semibold text-primary group-hover:underline">
                    Create Study Pack →
                  </span>
                </div>
              </div>

              {/* ANSWER_PACK Card */}
              <div 
                onClick={() => handleSelectMode("ANSWER_PACK")}
                className="group relative rounded-2xl border border-border bg-card/30 hover:bg-card/75 p-8 transition-all duration-300 hover:border-purple-500/50 cursor-pointer shadow-sm hover:shadow-xl hover:shadow-purple-500/[0.02] hover:-translate-y-1 backdrop-blur-sm overflow-hidden"
              >
                <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 group-hover:bg-purple-500/10 blur-xl rounded-full transition-colors" />
                
                <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-500 dark:text-purple-400 group-hover:scale-110 transition-transform duration-300">
                  <BrainCircuit className="h-6 w-6" />
                </div>
                
                <span className="text-[10px] font-bold tracking-widest text-purple-500 dark:text-purple-400 uppercase">MODE 02</span>
                <h3 className="text-xl font-bold mt-2 text-foreground group-hover:text-purple-500 dark:group-hover:text-purple-400 transition-colors flex items-center gap-2">
                  Solved Answer Pack
                  <ChevronRight className="h-4 w-4 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                </h3>
                
                <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                  Provide your study materials plus a specific question bank or PYQ paper. Get customized, exam-ready answers mapped directly to your questions.
                </p>

                <ul className="mt-6 space-y-2.5 text-xs text-muted-foreground border-t border-border/40 pt-5">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-purple-500 shrink-0" />
                    <span>Exact answer solutions tailored to your syllabus</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-purple-500 shrink-0" />
                    <span>Brevity controls for 2, 5, and 10 mark constraints</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-purple-500 shrink-0" />
                    <span>Concept breakdowns & mnemonics per question</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-purple-500 shrink-0" />
                    <span>Integrated diagrams & formula sheets</span>
                  </li>
                </ul>

                <div className="mt-8 pt-4">
                  <span className="text-xs font-semibold text-purple-500 dark:text-purple-400 group-hover:underline">
                    Solve Exam Paper →
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* AI Product Preview / Mockup Container */}
          <div className="relative max-w-4xl mx-auto mt-24 transition-all duration-500 hover:shadow-indigo-500/5 hover:shadow-2xl">
            <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/10 to-purple-600/5 rounded-2xl blur-xl -z-10" />
            
            <div className="rounded-xl border border-border bg-card/60 backdrop-blur-md overflow-hidden shadow-2xl">
              {/* Mockup Header Bar */}
              <div className="h-11 border-b border-border/60 bg-muted/40 px-4 flex items-center justify-between">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-border" />
                  <div className="w-3 h-3 rounded-full bg-border" />
                  <div className="w-3 h-3 rounded-full bg-border" />
                </div>
                <div className="text-[11px] text-muted-foreground font-mono tracking-wider">EXAM-SLAYER-DASHBOARD</div>
                <div className="w-12" />
              </div>

              {/* Mockup Body Layout */}
              <div className="grid grid-cols-1 md:grid-cols-4 min-h-[360px] text-left text-xs text-muted-foreground">
                {/* Left Sidebar */}
                <div className="border-r border-border/40 p-4 bg-muted/10 space-y-4 col-span-1">
                  <div className="font-semibold text-foreground/80 tracking-tight uppercase text-[10px]">Ingested Sources</div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 p-2 rounded-lg bg-card border border-border text-foreground">
                      <FileText className="h-3.5 w-3.5 text-indigo-500" />
                      <span className="truncate">Lecture_04_AI.pdf</span>
                    </div>
                    <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/20 border border-border/30">
                      <FileText className="h-3.5 w-3.5 text-muted-foreground/60" />
                      <span className="truncate text-muted-foreground/60">Syllabus_Overview.docx</span>
                    </div>
                  </div>
                  <div className="h-px bg-border/40" />
                  <div className="space-y-1">
                    <span className="text-[10px] text-muted-foreground/60 block">Status</span>
                    <span className="font-semibold text-indigo-500 flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-ping" />
                      OCR Completed
                    </span>
                  </div>
                </div>

                {/* Main Content Area */}
                <div className="p-5 md:col-span-2 space-y-4">
                  <div className="flex items-center justify-between border-b border-border/40 pb-3">
                    <div>
                      <h3 className="font-bold text-foreground text-sm">Deep Learning Optimization</h3>
                      <p className="text-[10px] text-muted-foreground">Solved Answer Pack</p>
                    </div>
                    <span className="text-[10px] bg-indigo-500/10 text-indigo-600 dark:text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded font-mono">
                      Solved 8/8
                    </span>
                  </div>

                  <div className="space-y-3">
                    <div className="p-3 rounded-lg bg-card/40 border border-border/60">
                      <div className="font-bold text-foreground mb-1 flex items-center gap-1">
                        <BookOpen className="h-3.5 w-3.5 text-indigo-500" /> Question 1: Describe gradient descent.
                      </div>
                      <p className="leading-relaxed text-xs">
                        Gradient descent is an optimization algorithm used to minimize a cost function by iteratively moving in the direction of steepest descent, defined by the negative of the gradient.
                      </p>
                    </div>

                    <div className="p-3 rounded-lg bg-card/40 border border-border/60">
                      <div className="font-bold text-foreground mb-1 flex items-center gap-1">
                        <Sparkles className="h-3.5 w-3.5 text-purple-500" /> Memory Trick: SGD vs Batch
                      </div>
                      <p className="leading-relaxed text-xs">
                        <strong>SGD</strong> = <strong>S</strong>ingle sample steps (fast, noisy). <strong>Batch</strong> = <strong>B</strong>ig calculations (slow, smooth).
                      </p>
                    </div>
                  </div>
                </div>

                {/* Right Preview */}
                <div className="border-l border-border/40 p-4 bg-muted/10 col-span-1 space-y-4 flex flex-col justify-between">
                  <div>
                    <div className="font-semibold text-foreground/80 tracking-tight uppercase text-[10px] mb-3">Download Solved PDF</div>
                    <div className="aspect-[3/4] bg-background rounded border border-border p-2 flex flex-col justify-between shadow-inner">
                      <div className="space-y-1">
                        <div className="h-1.5 w-8/12 bg-muted rounded" />
                        <div className="h-1 w-full bg-muted/40 rounded" />
                        <div className="h-1 w-10/12 bg-muted/40 rounded" />
                        <div className="h-1 w-full bg-muted/40 rounded" />
                      </div>
                      <div className="h-6 w-full bg-indigo-600/10 rounded flex items-center justify-center text-[8px] text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
                        solved_answers.pdf
                      </div>
                    </div>
                  </div>
                  <Button size="sm" className="w-full text-[10px]" asChild>
                    <Link to="/upload">Upload Now</Link>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Section */}
        <section className="container mx-auto px-4 py-24 border-t border-border/40 max-w-5xl">
          <div className="max-w-2xl mx-auto text-center mb-16">
            <h2 className="text-3xl font-bold tracking-tight mb-4">
              Engineered for Academic Excellence
            </h2>
            <p className="text-muted-foreground text-sm">
              Exam Slayer parses complex concepts and raw documents into clean, structured guides.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            <article className="rounded-xl border border-border bg-card/20 p-8 shadow-sm transition-all duration-300 hover:border-primary/40 hover:-translate-y-1 hover:shadow-md group">
              <div className="mb-6 flex h-11 w-11 items-center justify-center rounded-lg bg-muted border border-border text-indigo-500 group-hover:scale-110 transition-transform">
                <FileText className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-bold tracking-tight text-foreground">
                Multi-File Ingestion
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                Upload up to 5 study documents (PDFs, presentations, slides, Word documents) simultaneously to feed the knowledge base.
              </p>
            </article>

            <article className="rounded-xl border border-border bg-card/20 p-8 shadow-sm transition-all duration-300 hover:border-primary/40 hover:-translate-y-1 hover:shadow-md group">
              <div className="mb-6 flex h-11 w-11 items-center justify-center rounded-lg bg-muted border border-border text-indigo-500 group-hover:scale-110 transition-transform">
                <BrainCircuit className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-bold tracking-tight text-foreground">
                Advanced OCR Recovery
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                Scanned lectures or image-only documents are automatically processed through advanced OCR pipelines to recover mathematical formulas.
              </p>
            </article>

            <article className="rounded-xl border border-border bg-card/20 p-8 shadow-sm transition-all duration-300 hover:border-primary/40 hover:-translate-y-1 hover:shadow-md group">
              <div className="mb-6 flex h-11 w-11 items-center justify-center rounded-lg bg-muted border border-border text-indigo-500 group-hover:scale-110 transition-transform">
                <Sparkles className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-bold tracking-tight text-foreground">
                Paginated PDF Export
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                Receive a print-ready, beautifully designed PDF of your study pack or solved answer bank, fully structured and styled.
              </p>
            </article>
          </div>
        </section>

        {/* Call to action */}
        <section className="container mx-auto px-4 py-20 border-t border-border/40 text-center max-w-3xl">
          <h2 className="text-3xl font-bold tracking-tight mb-4">Ready to crush your next exam?</h2>
          <p className="text-muted-foreground text-sm max-w-lg mx-auto mb-8">
            Upload your materials today. Get study packs or exam answer keys generated by Gemini AI in less than a minute.
          </p>
          <Button asChild size="lg" className="px-10">
            <Link to="/upload">Get Started Now</Link>
          </Button>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/40 py-8 bg-muted/20">
        <div className="container mx-auto px-4 flex flex-col sm:flex-row items-center justify-between text-xs text-muted-foreground gap-4 max-w-5xl">
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 rounded bg-muted flex items-center justify-center border border-border">
              <Sparkles className="h-3 w-3 text-indigo-500" />
            </div>
            <span>© 2026 Exam Slayer. All rights reserved.</span>
          </div>
          <div className="flex gap-6">
            <a href="#" className="hover:text-foreground transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-foreground transition-colors">Terms of Service</a>
            <a href="#" className="hover:text-foreground transition-colors">Status</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
