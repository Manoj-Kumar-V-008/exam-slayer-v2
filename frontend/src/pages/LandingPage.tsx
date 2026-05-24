import { ArrowRight, BrainCircuit, FileText, ShieldCheck } from "lucide-react";
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
    <main className="min-h-screen">
      <section className="border-b bg-white">
        <div className="container flex min-h-[76vh] flex-col justify-center py-12">
          <div className="max-w-3xl">
            <p className="mb-4 text-sm font-semibold uppercase tracking-wide text-primary">Exam Slayer V2</p>
            <h1 className="text-4xl font-bold leading-tight text-foreground sm:text-5xl lg:text-6xl">
              Turn study files into exam-ready PDFs.
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-muted-foreground">
              Upload your notes, slides, and PDFs. Exam Slayer prepares a premium study pack with OCR recovery,
              structured explanations, exam questions, and a polished downloadable PDF.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button asChild size="lg">
                <Link to="/upload">
                  Upload materials
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link to="/processing/demo">View processing flow</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      <section className="container py-10">
        <div className="grid gap-4 md:grid-cols-3">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <article key={feature.title} className="rounded-lg border bg-card p-6 shadow-sm">
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <h2 className="text-lg font-semibold">{feature.title}</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{feature.description}</p>
              </article>
            );
          })}
        </div>
      </section>
    </main>
  );
}
