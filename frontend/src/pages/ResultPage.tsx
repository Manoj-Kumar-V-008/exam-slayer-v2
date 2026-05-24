import { CheckCircle2, Download } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function ResultPage() {
  const { jobId } = useParams();

  return (
    <main className="min-h-screen bg-background">
      <div className="container flex min-h-screen items-center justify-center py-10">
        <section className="w-full max-w-2xl rounded-lg border bg-card p-8 text-center shadow-sm">
          <CheckCircle2 className="mx-auto h-12 w-12 text-primary" />
          <p className="mt-6 text-sm font-semibold uppercase tracking-wide text-primary">Result</p>
          <h1 className="mt-2 text-3xl font-bold">Study pack ready</h1>
          <p className="mt-3 text-muted-foreground">
            Download and restart actions will connect to the backend result data in the next step.
          </p>
          <p className="mt-4 rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">
            Job ID: {jobId ?? "pending"}
          </p>
          <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
            <Button disabled>
              <Download className="mr-2 h-4 w-4" />
              Download PDF
            </Button>
            <Button asChild variant="outline">
              <Link to="/upload">Create another</Link>
            </Button>
          </div>
        </section>
      </div>
    </main>
  );
}
