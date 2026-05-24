import { FileUp } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function UploadPage() {
  return (
    <main className="min-h-screen bg-background">
      <div className="container py-10">
        <Button asChild variant="ghost" className="mb-8">
          <Link to="/">Back to home</Link>
        </Button>

        <section className="mx-auto max-w-3xl rounded-lg border bg-card p-8 shadow-sm">
          <div className="mb-6">
            <p className="text-sm font-semibold uppercase tracking-wide text-primary">Upload</p>
            <h1 className="mt-2 text-3xl font-bold">Prepare a new study pack</h1>
            <p className="mt-3 text-muted-foreground">
              Drag-and-drop upload, validation, and backend submission will be wired in the next step.
            </p>
          </div>

          <div className="flex min-h-64 flex-col items-center justify-center rounded-lg border border-dashed bg-muted/40 p-8 text-center">
            <FileUp className="h-12 w-12 text-primary" />
            <h2 className="mt-4 text-lg font-semibold">PDF, DOCX, and PPTX files</h2>
            <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
              The upload surface is ready for the MVP interaction layer.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
