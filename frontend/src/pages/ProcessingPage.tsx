import { Loader2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function ProcessingPage() {
  const { jobId } = useParams();

  return (
    <main className="min-h-screen bg-background">
      <div className="container flex min-h-screen items-center justify-center py-10">
        <section className="w-full max-w-2xl rounded-lg border bg-card p-8 text-center shadow-sm">
          <Loader2 className="mx-auto h-12 w-12 animate-spin text-primary" />
          <p className="mt-6 text-sm font-semibold uppercase tracking-wide text-primary">Processing</p>
          <h1 className="mt-2 text-3xl font-bold">Job status tracker</h1>
          <p className="mt-3 text-muted-foreground">
            Polling and animated status steps will be connected in the next implementation step.
          </p>
          <p className="mt-4 rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">
            Job ID: {jobId ?? "pending"}
          </p>
          <Button asChild className="mt-6" variant="outline">
            <Link to="/upload">Start another upload</Link>
          </Button>
        </section>
      </div>
    </main>
  );
}
