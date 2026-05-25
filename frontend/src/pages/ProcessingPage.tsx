import { useEffect, useState } from "react";
import { Loader2, CheckCircle2, AlertCircle, Sparkles, ArrowLeft, RefreshCw } from "lucide-react";
import { Link, useParams, useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { getJobStatus, JobResponse, ProductMode } from "@/services/api";
import { Navbar } from "@/components/Navbar";

interface Step {
  id: string;
  label: string;
}

const STUDY_PACK_STEPS: Step[] = [
  { id: "uploaded", label: "Files uploaded successfully" },
  { id: "extracting", label: "Processing study materials" },
  { id: "ai_processing", label: "Structuring core concepts & summaries" },
  { id: "pdf_generating", label: "Building study pack PDF" }
];

const ANSWER_PACK_STEPS: Step[] = [
  { id: "uploaded", label: "Files uploaded successfully" },
  { id: "extracting", label: "Processing study materials" },
  { id: "ocr_processing", label: "Reading question bank" },
  { id: "ai_processing", label: "Solving exam questions" },
  { id: "pdf_generating", label: "Building answer pack PDF" }
];

const STUDY_PACK_STATUS_ORDER = ["uploaded", "extracting", "ai_processing", "pdf_generating"];
const ANSWER_PACK_STATUS_ORDER = ["uploaded", "extracting", "ocr_processing", "ai_processing", "pdf_generating"];

export function ProcessingPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  // Read mode from location state immediately to prevent flicker, default to ANSWER_PACK
  const [mode, setMode] = useState<ProductMode>(() => {
    const stateMode = location.state?.mode;
    return stateMode === "STUDY_PACK" || stateMode === "ANSWER_PACK" ? stateMode : "ANSWER_PACK";
  });

  // States
  const [jobData, setJobData] = useState<JobResponse | null>(null);
  const [status, setStatus] = useState<string>("uploaded");
  const [lastActiveStatus, setLastActiveStatus] = useState<string>("uploaded");
  const [error, setError] = useState<string | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);
  const [showTechDetails, setShowTechDetails] = useState(false);

  // Determine current steps and status order based on detected mode
  const currentSteps = mode === "STUDY_PACK" ? STUDY_PACK_STEPS : ANSWER_PACK_STEPS;
  const statusOrder = mode === "STUDY_PACK" ? STUDY_PACK_STATUS_ORDER : ANSWER_PACK_STATUS_ORDER;

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
        
        // Update mode if backend lists it differently
        if (data.mode && data.mode !== mode) {
          setMode(data.mode);
        }

        if (data.status !== "failed") {
          // Track the last valid status prior to a potential failure
          const order = data.mode === "STUDY_PACK" ? STUDY_PACK_STATUS_ORDER : ANSWER_PACK_STATUS_ORDER;
          if (order.includes(data.status)) {
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
  }, [jobId, navigate, mode]);

  // Helper: Determine state of each UI step
  const getStepState = (stepId: string, index: number) => {
    if (status === "failed") {
      const failedIndex = statusOrder.indexOf(lastActiveStatus);
      if (index < failedIndex) return "completed";
      if (index === failedIndex) return "failed";
      return "pending";
    }

    if (status === "completed") {
      return "completed";
    }

    const currentIndex = statusOrder.indexOf(status);
    if (index < currentIndex) return "completed";
    if (index === currentIndex) return "running";
    return "pending";
  };

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/20 selection:text-primary bg-grid-pattern relative overflow-x-hidden flex flex-col transition-colors duration-300">
      {/* Shared Navigation Header */}
      <Navbar />

      {/* Main Content */}
      <div className="flex-1 flex flex-col justify-center py-12 relative z-10">
        {/* Soft Radial Ambient Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[400px] bg-[radial-gradient(ellipse_60%_60%_at_50%_-20%,rgba(99,102,241,0.08),transparent)] pointer-events-none z-0 dark:opacity-70 opacity-40" />

        <div className="container mx-auto px-4 flex flex-col items-center justify-center">
          {/* Loading status wrapper */}
          {isLoadingStatus && !error ? (
            <div className="text-center py-12 bg-card/30 border border-border p-8 rounded-xl backdrop-blur-sm shadow-sm max-w-md w-full">
              <Loader2 className="mx-auto h-9 w-9 animate-spin text-primary mb-4" />
              <p className="text-sm text-muted-foreground font-medium">Connecting to status board...</p>
            </div>
          ) : error ? (
            /* Error State Card */
            <section className="w-full max-w-xl rounded-xl border border-destructive/25 bg-card/40 backdrop-blur-md p-8 text-center shadow-xl relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1 bg-destructive" />
              
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10 border border-destructive/20 text-destructive mb-6">
                <AlertCircle className="h-6 w-6" />
              </div>

              <span className="text-[10px] font-semibold text-destructive bg-destructive/10 border border-destructive/25 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                Compilation Failed
              </span>
              
              <h1 className="mt-4 text-2xl font-bold tracking-tight">
                Could not compile pack
              </h1>
              
              <p className="mt-2 text-sm text-muted-foreground px-4">
                {getDisplayErrorMessage()}
              </p>

              {/* Technical details collapse */}
              <div className="mt-6 text-left max-w-md mx-auto">
                <button 
                  onClick={() => setShowTechDetails(!showTechDetails)}
                  className="text-[11px] text-muted-foreground hover:text-foreground cursor-pointer select-none font-medium flex items-center gap-1.5 transition-colors focus:outline-none"
                >
                  <span className={`inline-block transition-transform duration-200 ${showTechDetails ? "rotate-90" : ""}`}>
                    ▶
                  </span>
                  {showTechDetails ? "Hide technical details" : "Show technical details"}
                </button>
                {showTechDetails && (
                  <div className="mt-2.5 p-3.5 rounded-lg bg-destructive/5 border border-destructive/20 animate-in fade-in slide-in-from-top-1 duration-200">
                    <span className="text-[10px] text-destructive/80 font-mono block mb-1">Raw Exception Dump</span>
                    <p className="text-xs text-destructive font-mono leading-relaxed break-all">
                      {error}
                    </p>
                  </div>
                )}
              </div>

              <p className="mt-4 text-[10px] text-muted-foreground/60 font-mono">
                Job ID: {jobId}
              </p>

              <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
                <Button asChild className="gap-2 font-semibold">
                  <Link to="/upload">
                    <RefreshCw className="h-4 w-4" />
                    Retry Upload
                  </Link>
                </Button>
                <Button asChild variant="outline" className="gap-2 border-border/80 font-semibold">
                  <Link to="/upload">
                    <ArrowLeft className="h-4 w-4" />
                    Back to Upload
                  </Link>
                </Button>
              </div>
            </section>
          ) : (
            /* Processing Flow Card */
            <section className="w-full max-w-xl rounded-xl border border-border bg-card/45 backdrop-blur-md p-8 shadow-xl relative">
              <div className="flex items-center justify-between border-b border-border/40 pb-4 mb-6">
                <div>
                  <span className="text-[10px] font-semibold text-primary bg-primary/10 border border-primary/25 px-2 py-0.5 rounded-full uppercase tracking-wider flex items-center gap-1.5 w-max">
                    <Sparkles className="h-3 w-3" />
                    Processing {mode === "STUDY_PACK" ? "Study Pack" : "Answer Pack"}
                  </span>
                  <h1 className="text-xl font-bold tracking-tight mt-2">
                    Analyzing & Generating
                  </h1>
                </div>
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              </div>

              <p className="text-xs text-muted-foreground leading-relaxed mb-8">
                Our AI pipelines are extracting text, executing OCR recovery, structuring explanations, and compiling your study materials. This may take up to a minute.
              </p>

              {/* Stepper Pipeline */}
              <div className="space-y-1">
                {currentSteps.map((step, idx) => {
                  const stepState = getStepState(step.id, idx);
                  
                  return (
                    <div key={step.id}>
                      <div className="flex items-center gap-3 py-1.5">
                        {/* Step Status Icon */}
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center">
                          {stepState === "completed" && (
                            <CheckCircle2 className="h-5.5 w-5.5 text-primary" />
                          )}
                          {stepState === "running" && (
                            <Loader2 className="h-5 w-5 animate-spin text-primary" />
                          )}
                          {stepState === "failed" && (
                            <AlertCircle className="h-5.5 w-5.5 text-destructive animate-pulse" />
                          )}
                          {stepState === "pending" && (
                            <div className="h-3.5 w-3.5 rounded-full border border-border bg-background" />
                          )}
                        </div>

                        {/* Step Text Label */}
                        <span className={`text-xs font-medium transition-colors duration-300 ${
                          stepState === "completed" 
                            ? "text-muted-foreground/60 line-through decoration-border" 
                            : stepState === "running"
                              ? "text-foreground font-semibold"
                              : stepState === "failed"
                                ? "text-destructive font-semibold"
                                : "text-muted-foreground/40"
                        }`}>
                          {step.label}
                        </span>
                      </div>

                      {/* Stepper Connector Line */}
                      {idx < currentSteps.length - 1 && (
                        <div className="h-5 w-0.5 bg-border ml-3" />
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="mt-8 pt-4 border-t border-border/40 flex items-center justify-between text-[10px] text-muted-foreground font-mono">
                <span>JOB ID: {jobId}</span>
                <span>FILE: {jobData?.file_name || "loading..."}</span>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
