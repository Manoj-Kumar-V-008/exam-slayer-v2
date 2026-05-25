import { useEffect, useState } from "react";
import { Loader2, CheckCircle2, AlertCircle, Sparkles, ArrowLeft, RefreshCw } from "lucide-react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { getJobStatus, JobResponse } from "@/services/api";

const PIPELINE_STEPS = [
  { id: "uploaded", label: "Files uploaded successfully" },
  { id: "extracting", label: "Processing study materials" },
  { id: "ocr_processing", label: "Reading question bank" },
  { id: "ai_processing", label: "Solving exam questions" },
  { id: "pdf_generating", label: "Building answer pack PDF" }
];

const STATUS_ORDER = ["uploaded", "extracting", "ocr_processing", "ai_processing", "pdf_generating"];

export function ProcessingPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  // States
  const [jobData, setJobData] = useState<JobResponse | null>(null);
  const [status, setStatus] = useState<string>("uploaded");
  const [lastActiveStatus, setLastActiveStatus] = useState<string>("uploaded");
  const [error, setError] = useState<string | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);
  const [showTechDetails, setShowTechDetails] = useState(false);

  // Helper: Detect rate-limit / quota backend errors
  const isQuotaError = (errMsg: string | null): boolean => {
    if (!errMsg) return false;
    const msg = errMsg.toLowerCase();
    return (
      msg.includes("429") ||
      msg.includes("resource_exhausted") ||
      msg.includes("quota exceeded") ||
      msg.includes("rate limit")
    );
  };

  // Helper: Get user-friendly message
  const getDisplayErrorMessage = () => {
    if (isQuotaError(error)) {
      return "AI processing capacity is temporarily busy. Please retry in about a minute.";
    }
    return "The AI engine encountered an issue while processing your document content.";
  };

  useEffect(() => {
    if (!jobId) return;

    let isMounted = true;
    let timeoutId: any = null;

    const pollStatus = async () => {
      try {
        const data = await getJobStatus(jobId);
        
        if (!isMounted) return;
        
        setIsLoadingStatus(false);
        setJobData(data);
        setStatus(data.status);

        if (data.status !== "failed") {
          // Track the last valid status prior to a potential failure
          if (STATUS_ORDER.includes(data.status)) {
            setLastActiveStatus(data.status);
          }
        }

        if (data.status === "completed") {
          // Success redirection
          navigate(`/result/${jobId}`);
          return;
        }

        if (data.status === "failed") {
          setError(data.error_message || "An unexpected error occurred during document compilation.");
          return;
        }

        // Wait 3 seconds and poll again
        timeoutId = setTimeout(pollStatus, 3000);
      } catch (err: any) {
        if (!isMounted) return;
        console.error("Error polling job status:", err);
        
        // Even on network failure, try again after 3 seconds to handle transient disconnects
        timeoutId = setTimeout(pollStatus, 3000);
      }
    };

    pollStatus();

    return () => {
      isMounted = false;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [jobId, navigate]);

  // Helper: Determine state of each UI step
  const getStepState = (stepId: string, index: number) => {
    if (status === "failed") {
      const failedIndex = STATUS_ORDER.indexOf(lastActiveStatus);
      if (index < failedIndex) return "completed";
      if (index === failedIndex) return "failed";
      return "pending";
    }

    if (status === "completed") {
      return "completed";
    }

    const currentIndex = STATUS_ORDER.indexOf(status);
    if (index < currentIndex) return "completed";
    if (index === currentIndex) return "running";
    return "pending";
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-indigo-500/30 selection:text-white bg-grid-pattern relative overflow-x-hidden flex flex-col justify-center py-12">
      {/* Soft Radial Ambient Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[400px] bg-[radial-gradient(ellipse_60%_60%_at_50%_-20%,rgba(99,102,241,0.08),rgba(255,255,255,0))] pointer-events-none z-0" />

      <div className="container mx-auto px-4 relative z-10 flex flex-col items-center justify-center">
        {/* Loading status wrapper */}
        {isLoadingStatus && !error ? (
          <div className="text-center py-12">
            <Loader2 className="mx-auto h-10 w-10 animate-spin text-indigo-500 mb-4" />
            <p className="text-sm text-zinc-400 font-medium">Connecting to status board...</p>
          </div>
        ) : error ? (
          /* Error State Card */
          <section className="w-full max-w-xl rounded-xl border border-red-500/20 bg-zinc-900/50 backdrop-blur-md p-8 text-center shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-red-500/50" />
            
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-red-500/10 border border-red-500/20 text-red-500 mb-6">
              <AlertCircle className="h-6 w-6" />
            </div>

            <span className="text-[10px] font-semibold text-red-400 bg-red-500/10 border border-red-500/25 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
              Compilation Failed
            </span>
            
            <h1 className="mt-4 text-2xl font-bold tracking-tight text-zinc-100">
              Could not generate study pack
            </h1>
            
             <p className="mt-2 text-sm text-zinc-400 px-4">
              {getDisplayErrorMessage()}
            </p>

            {/* Technical details collapse */}
            <div className="mt-6 text-left max-w-md mx-auto">
              <button 
                onClick={() => setShowTechDetails(!showTechDetails)}
                className="text-[11px] text-zinc-500 hover:text-zinc-300 cursor-pointer select-none font-medium flex items-center gap-1.5 transition-colors focus:outline-none"
              >
                <span className={`inline-block transition-transform duration-200 ${showTechDetails ? "rotate-90" : ""}`}>
                  ▶
                </span>
                {showTechDetails ? "Hide technical details" : "Show technical details"}
              </button>
              {showTechDetails && (
                <div className="mt-2.5 p-3.5 rounded-lg bg-red-950/20 border border-red-950/40 animate-in fade-in slide-in-from-top-1 duration-200">
                  <span className="text-[10px] text-red-400/80 font-mono block mb-1">Raw Exception Dump</span>
                  <p className="text-xs text-red-300 font-mono leading-relaxed break-words">
                    {error}
                  </p>
                </div>
              )}
            </div>

            <p className="mt-4 text-xs text-zinc-500">
              Job ID: <span className="font-mono">{jobId}</span>
            </p>

            <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
              <Button asChild className="gap-2">
                <Link to="/upload">
                  <RefreshCw className="h-4 w-4" />
                  Retry Upload
                </Link>
              </Button>
              <Button asChild variant="outline" className="gap-2">
                <Link to="/upload">
                  <ArrowLeft className="h-4 w-4" />
                  Back to Upload
                </Link>
              </Button>
            </div>
          </section>
        ) : (
          /* Processing Flow Card */
          <section className="w-full max-w-xl rounded-xl border border-zinc-800/40 bg-zinc-900/50 backdrop-blur-md p-8 shadow-xl relative">
            <div className="flex items-center justify-between border-b border-zinc-800/40 pb-4 mb-6">
              <div>
                <span className="text-[10px] font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/25 px-2 py-0.5 rounded-full uppercase tracking-wider flex items-center gap-1.5 w-max">
                  <Sparkles className="h-3 w-3" />
                  Processing Pack
                </span>
                <h1 className="text-xl font-bold tracking-tight text-zinc-100 mt-2">
                  Analyzing & Generating
                </h1>
              </div>
              <Loader2 className="h-5 w-5 animate-spin text-indigo-500" />
            </div>

            <p className="text-xs text-zinc-400 leading-relaxed mb-8">
              Our AI pipelines are extracting text, executing OCR recovery (if required), structuring explanations, and compiling your study materials. This may take up to a minute.
            </p>

            {/* Stepper Pipeline */}
            <div className="space-y-1">
              {PIPELINE_STEPS.map((step, idx) => {
                const stepState = getStepState(step.id, idx);
                
                return (
                  <div key={step.id}>
                    <div className="flex items-center gap-3 py-1.5">
                      {/* Step Status Icon */}
                      <div className="flex h-6 w-6 shrink-0 items-center justify-center">
                        {stepState === "completed" && (
                          <CheckCircle2 className="h-5.5 w-5.5 text-indigo-400" />
                        )}
                        {stepState === "running" && (
                          <Loader2 className="h-5 w-5 animate-spin text-indigo-500" />
                        )}
                        {stepState === "failed" && (
                          <AlertCircle className="h-5.5 w-5.5 text-red-500 animate-pulse" />
                        )}
                        {stepState === "pending" && (
                          <div className="h-4 w-4 rounded-full border border-zinc-800 bg-zinc-900" />
                        )}
                      </div>

                      {/* Step Text Label */}
                      <span className={`text-xs font-medium transition-colors duration-300 ${
                        stepState === "completed" 
                          ? "text-zinc-400 line-through decoration-zinc-800/50" 
                          : stepState === "running"
                            ? "text-zinc-200 font-semibold"
                            : stepState === "failed"
                              ? "text-red-400 font-semibold"
                              : "text-zinc-600"
                      }`}>
                        {step.label}
                      </span>
                    </div>

                    {/* Stepper Connector Line */}
                    {idx < PIPELINE_STEPS.length - 1 && (
                      <div className="h-5 w-0.5 bg-zinc-800/50 ml-3" />
                    )}
                  </div>
                );
              })}
            </div>

            <div className="mt-8 pt-4 border-t border-zinc-800/40 flex items-center justify-between text-[11px] text-zinc-500 font-mono">
              <span>JOB ID: {jobId}</span>
              <span>FILE: {jobData?.file_name || "loading..."}</span>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
