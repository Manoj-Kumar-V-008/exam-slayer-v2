import React, { useState, useRef, useEffect } from "react";
import { ArrowLeft, FileUp, Sparkles, Shield, Info, CheckCircle2, AlertCircle, Loader2, Trash2, FileText, UploadCloud, BookOpen, BrainCircuit } from "lucide-react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { uploadFiles, ProductMode } from "@/services/api";
import { Navbar } from "@/components/Navbar";

export function UploadPage() {
  const navigate = useNavigate();
  const location = useLocation();

  // Refs
  const studyInputRef = useRef<HTMLInputElement>(null);
  const qbInputRef = useRef<HTMLInputElement>(null);

  // States
  const [mode, setMode] = useState<ProductMode>(() => {
    const passedMode = location.state?.initialMode;
    return passedMode === "STUDY_PACK" || passedMode === "ANSWER_PACK" ? passedMode : "ANSWER_PACK";
  });
  const [studyFiles, setStudyFiles] = useState<File[]>([]);
  const [questionBank, setQuestionBank] = useState<File | null>(null);
  const [isStudyDragging, setIsStudyDragging] = useState(false);
  const [isQbDragging, setIsQbDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Constants
  const MAX_FILE_SIZE_MB = 40;
  const ALLOWED_EXTENSIONS = ["pdf", "docx", "pptx"];

  // Read initialMode if changed in routing state
  useEffect(() => {
    if (location.state?.initialMode) {
      const initMode = location.state.initialMode;
      if (initMode === "STUDY_PACK" || initMode === "ANSWER_PACK") {
        setMode(initMode);
      }
    }
  }, [location.state]);

  // Reset question bank if mode is switched to STUDY_PACK
  useEffect(() => {
    if (mode === "STUDY_PACK") {
      setQuestionBank(null);
    }
  }, [mode]);

  // Helper: check extension
  const isValidExtension = (fileName: string) => {
    const ext = fileName.split(".").pop()?.toLowerCase() || "";
    return ALLOWED_EXTENSIONS.includes(ext);
  };

  // Handlers for Study Materials (Multi-file)
  const addStudyFiles = (files: FileList) => {
    setError(null);
    const newFiles: File[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (!isValidExtension(file.name)) {
        setError(`Unsupported format in study files. Only PDF, DOCX, and PPTX are allowed.`);
        return;
      }
      newFiles.push(file);
    }

    setStudyFiles((prev) => {
      const combined = [...prev, ...newFiles];
      if (combined.length > 5) {
        setError("You can upload at most 5 study material files.");
        return prev;
      }
      return combined;
    });
  };

  const removeStudyFile = (index: number) => {
    setStudyFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // Handlers for Question Bank (Single-file)
  const handleQbSelect = (file: File) => {
    setError(null);
    if (!isValidExtension(file.name)) {
      setError(`Unsupported format for Question Bank. Only PDF, DOCX, and PPTX are allowed.`);
      return;
    }
    setQuestionBank(file);
  };

  // Ingestion submission trigger
  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validations
    if (studyFiles.length === 0) {
      setError("Please select at least one Study Material file.");
      return;
    }
    if (mode === "ANSWER_PACK" && !questionBank) {
      setError("Question Bank / PYQ file is required for Answer Pack Mode.");
      return;
    }

    // Combined size check
    let totalSize = 0;
    studyFiles.forEach((f) => {
      totalSize += f.size;
    });
    if (questionBank) {
      totalSize += questionBank.size;
    }

    if (totalSize > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setError(`Combined upload size exceeds the safe ${MAX_FILE_SIZE_MB}MB limit.`);
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const response = await uploadFiles(
        mode,
        studyFiles,
        questionBank,
        (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percent);
          }
        }
      );

      if (response && response.job_id) {
        // Pass mode through navigation state to ProcessingPage immediately to prevent flicker
        navigate(`/processing/${response.job_id}`, { state: { mode } });
      } else {
        throw new Error("Failed to receive Job ID from server.");
      }
    } catch (err: any) {
      console.error("Ingestion failed:", err);
      const msg = err.response?.data?.detail || err.message || "An unexpected error occurred during submission.";
      setError(msg);
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/20 selection:text-primary bg-grid-pattern relative overflow-x-hidden pb-16 transition-colors duration-300">
      {/* Shared Navigation Header */}
      <Navbar />

      {/* Ambient Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[400px] bg-[radial-gradient(ellipse_60%_60%_at_50%_-20%,rgba(99,102,241,0.08),transparent)] pointer-events-none z-0 dark:opacity-70 opacity-40" />

      <div className="container mx-auto px-4 py-8 relative z-10 max-w-5xl">
        <header className="mb-10">
          <Button asChild variant="ghost" size="sm" className="gap-2 text-muted-foreground hover:text-foreground mb-6" disabled={isUploading}>
            <Link to="/">
              <ArrowLeft className="h-4 w-4" />
              Back to home
            </Link>
          </Button>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-border bg-card/60 text-[10px] font-semibold text-primary uppercase tracking-wider mb-2.5">
                <Sparkles className="h-3 w-3" />
                V2 Dual Mode Compiler
              </div>
              <h1 className="text-3xl font-extrabold tracking-tight">Create Academic Pack</h1>
              <p className="mt-2 text-sm text-muted-foreground max-w-2xl">
                Select your preparation mode, upload notes or textbook files, and let the AI generate customized study materials or solved exam answer packs.
              </p>
            </div>
            
            <div className="flex items-center gap-3 bg-card/40 border border-border/60 p-2.5 rounded-lg text-xs self-start md:self-auto backdrop-blur-sm shadow-sm">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold font-mono text-[10px]">1</span>
              <span className="text-foreground font-medium">Upload</span>
              <div className="h-px w-6 bg-border" />
              <span className="flex h-5 w-5 items-center justify-center rounded-full border border-border text-muted-foreground font-bold font-mono text-[10px]">2</span>
              <span className="text-muted-foreground">Compiler</span>
            </div>
          </div>
        </header>

        {/* Error Alert Display */}
        {error && (
          <div className="mb-8 flex items-start gap-3 p-4 rounded-xl bg-destructive/10 border border-destructive/25 text-xs text-destructive max-w-4xl mx-auto shadow-sm">
            <AlertCircle className="h-4.5 w-4.5 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-bold block">Submission Blocked</span>
              <p className="leading-relaxed">{error}</p>
            </div>
          </div>
        )}

        {/* Mode Selector Cards */}
        <section className="mb-10 max-w-4xl mx-auto">
          <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4 font-mono">1. Select Mode</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {/* STUDY_PACK Card */}
            <div
              onClick={() => !isUploading && setMode("STUDY_PACK")}
              className={`rounded-xl border p-5 cursor-pointer transition-all duration-300 relative flex items-start gap-4 ${
                mode === "STUDY_PACK"
                  ? "border-primary bg-primary/[0.03] ring-1 ring-primary shadow-md"
                  : "border-border bg-card/30 hover:border-border/80 hover:bg-card/50"
              } ${isUploading ? "opacity-60 cursor-not-allowed" : ""}`}
            >
              <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border transition-colors ${
                mode === "STUDY_PACK"
                  ? "bg-primary/10 border-primary/20 text-primary"
                  : "bg-muted border-border text-muted-foreground"
              }`}>
                <BookOpen className="h-5 w-5" />
              </div>
              <div className="flex-1 text-left">
                <span className="text-xs font-bold text-foreground block">Study Pack Mode</span>
                <span className="text-[11px] text-muted-foreground mt-1 block leading-normal">
                  Generates summaries, concepts, memory tricks, and predictive mark questions. Needs notes only.
                </span>
              </div>
              {mode === "STUDY_PACK" && (
                <div className="absolute top-3 right-3 h-2 w-2 rounded-full bg-primary" />
              )}
            </div>

            {/* ANSWER_PACK Card */}
            <div
              onClick={() => !isUploading && setMode("ANSWER_PACK")}
              className={`rounded-xl border p-5 cursor-pointer transition-all duration-300 relative flex items-start gap-4 ${
                mode === "ANSWER_PACK"
                  ? "border-primary bg-primary/[0.03] ring-1 ring-primary shadow-md"
                  : "border-border bg-card/30 hover:border-border/80 hover:bg-card/50"
              } ${isUploading ? "opacity-60 cursor-not-allowed" : ""}`}
            >
              <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border transition-colors ${
                mode === "ANSWER_PACK"
                  ? "bg-primary/10 border-primary/20 text-primary"
                  : "bg-muted border-border text-muted-foreground"
              }`}>
                <BrainCircuit className="h-5 w-5" />
              </div>
              <div className="flex-1 text-left">
                <span className="text-xs font-bold text-foreground block">Answer Pack Mode</span>
                <span className="text-[11px] text-muted-foreground mt-1 block leading-normal">
                  Generates target-length answers solved directly from your question bank. Needs notes + question bank.
                </span>
              </div>
              {mode === "ANSWER_PACK" && (
                <div className="absolute top-3 right-3 h-2 w-2 rounded-full bg-primary" />
              )}
            </div>
          </div>
        </section>

        {/* Upload Form Zone */}
        <form onSubmit={handleIngest} className={`grid gap-6 ${mode === "ANSWER_PACK" ? "md:grid-cols-5" : "max-w-3xl mx-auto"} transition-all duration-500`}>
          {/* Section A: Study Materials */}
          <div className={`${
            mode === "ANSWER_PACK" ? "md:col-span-3" : "w-full"
          } rounded-xl border border-border bg-card/45 backdrop-blur-md p-6 shadow-md flex flex-col justify-between`}>
            <div>
              <div className="flex items-center justify-between mb-4 border-b border-border/40 pb-3">
                <h3 className="font-bold text-foreground text-sm flex items-center gap-2">
                  <span className="flex h-5.5 w-5.5 items-center justify-center rounded bg-primary/10 text-primary font-bold text-xs">A</span>
                  Study Materials / Syllabus Notes
                </h3>
                <span className="text-[10px] text-muted-foreground uppercase font-mono">1 to 5 files</span>
              </div>
              
              <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
                Add lecture notes, slides (PPTX), course readings, or PDF chapters. The compiler uses these as the local fact sheet.
              </p>

              {/* Hidden file input */}
              <input 
                type="file" 
                ref={studyInputRef} 
                className="hidden" 
                onChange={(e) => e.target.files && addStudyFiles(e.target.files)}
                accept=".pdf,.docx,.pptx"
                multiple
                disabled={isUploading}
              />

              {/* Drag/Drop Zone */}
              <div 
                onDragOver={(e) => { e.preventDefault(); if (!isUploading) setIsStudyDragging(true); }}
                onDragLeave={() => setIsStudyDragging(false)}
                onDrop={(e) => { e.preventDefault(); setIsStudyDragging(false); if (!isUploading && e.dataTransfer.files) addStudyFiles(e.dataTransfer.files); }}
                onClick={() => !isUploading && studyInputRef.current?.click()}
                className={`flex min-h-[170px] flex-col items-center justify-center rounded-xl border border-dashed p-6 text-center transition-all duration-300 ease-in-out ${
                  isStudyDragging 
                    ? "border-primary bg-primary/[0.04] scale-[1.01]" 
                    : "border-border bg-muted/10 hover:bg-muted/30 hover:border-primary/40 cursor-pointer"
                }`}
              >
                <UploadCloud className="h-7 w-7 text-muted-foreground/60 mb-2 transition-colors" />
                <span className="text-xs font-bold text-foreground">Drag study notes here or browse</span>
                <span className="text-[10px] text-muted-foreground/60 mt-1">Supports PDF, DOCX, PPTX (Max 40MB total)</span>
              </div>

              {/* Study Materials List */}
              {studyFiles.length > 0 && (
                <div className="mt-5 space-y-2">
                  <span className="text-[10px] text-muted-foreground font-mono uppercase block">Selected Materials ({studyFiles.length}/5)</span>
                  <div className="flex flex-col gap-2">
                    {studyFiles.map((file, idx) => (
                      <div key={idx} className="flex items-center justify-between px-3 py-2 rounded-lg bg-background border border-border/80 text-xs text-foreground group shadow-sm">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <FileText className="h-4 w-4 text-primary shrink-0" />
                          <div className="truncate">
                            <span className="font-medium block truncate" title={file.name}>{file.name}</span>
                            <span className="text-[9px] text-muted-foreground font-mono">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                          </div>
                        </div>
                        <button 
                          type="button" 
                          onClick={() => removeStudyFile(idx)} 
                          className="text-muted-foreground hover:text-destructive transition-colors shrink-0 p-1 hover:bg-muted rounded-md" 
                          disabled={isUploading}
                          aria-label="Remove file"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {mode === "STUDY_PACK" && (
              <div className="mt-8 pt-6 border-t border-border/40">
                {isUploading ? (
                  <div className="space-y-2.5">
                    <div className="flex justify-between text-xs text-muted-foreground font-mono">
                      <span>Uploading study files...</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden border border-border/40">
                      <div 
                        className="h-full bg-gradient-to-r from-indigo-500 to-purple-600 transition-all duration-300 ease-out" 
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                ) : (
                  <Button 
                    type="submit" 
                    className="w-full shadow-md font-semibold gap-2"
                    disabled={studyFiles.length === 0}
                  >
                    <Sparkles className="h-4 w-4" />
                    Create Study Pack
                  </Button>
                )}
              </div>
            )}

            <div className="mt-6 flex items-start gap-2.5 p-3 rounded-lg bg-muted/40 border border-border/40 text-[11px] text-muted-foreground">
              <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
              <span>Ensure your materials cover the main syllabus concepts to yield high-quality compilations.</span>
            </div>
          </div>

          {/* Section B: Question Bank (Only visible for ANSWER_PACK) */}
          {mode === "ANSWER_PACK" && (
            <div className="md:col-span-2 rounded-xl border border-border bg-card/45 backdrop-blur-md p-6 shadow-md flex flex-col justify-between animate-in fade-in slide-in-from-right-4 duration-300">
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-border/40 pb-3">
                  <h3 className="font-bold text-foreground text-sm flex items-center gap-2">
                    <span className="flex h-5.5 w-5.5 items-center justify-center rounded bg-primary/10 text-primary font-bold text-xs">B</span>
                    Question Bank / PYQ
                  </h3>
                  <span className="text-[10px] text-muted-foreground uppercase font-mono">1 required file</span>
                </div>
                
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Upload your previous year questions, assignment questions, or test paper. The solver parses and answers each question one by one.
                </p>

                {/* Hidden file input */}
                <input 
                  type="file" 
                  ref={qbInputRef} 
                  className="hidden" 
                  onChange={(e) => e.target.files && handleQbSelect(e.target.files[0])}
                  accept=".pdf,.docx,.pptx"
                  disabled={isUploading}
                />

                {/* Single File Dropzone */}
                {!questionBank ? (
                  <div 
                    onDragOver={(e) => { e.preventDefault(); if (!isUploading) setIsQbDragging(true); }}
                    onDragLeave={() => setIsQbDragging(false)}
                    onDrop={(e) => { e.preventDefault(); setIsQbDragging(false); if (!isUploading && e.dataTransfer.files) handleQbSelect(e.dataTransfer.files[0]); }}
                    onClick={() => !isUploading && qbInputRef.current?.click()}
                    className={`flex min-h-[130px] flex-col items-center justify-center rounded-xl border border-dashed p-6 text-center transition-all duration-300 ease-in-out ${
                      isQbDragging 
                        ? "border-primary bg-primary/[0.04] scale-[1.01]" 
                        : "border-border bg-muted/10 hover:bg-muted/30 hover:border-primary/40 cursor-pointer"
                    }`}
                  >
                    <FileUp className="h-6 w-6 text-muted-foreground/60 mb-2" />
                    <span className="text-xs font-bold text-foreground">Choose question paper</span>
                    <span className="text-[10px] text-muted-foreground/60 mt-1">PDF, DOCX, PPTX</span>
                  </div>
                ) : (
                  /* Selected File Card */
                  <div className="p-4 rounded-xl bg-background border border-border relative flex items-center justify-between shadow-sm">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center border border-primary/20 shrink-0">
                        <FileText className="h-4.5 w-4.5" />
                      </div>
                      <div className="min-w-0">
                        <span className="text-xs font-bold text-foreground block truncate max-w-[130px]" title={questionBank.name}>
                          {questionBank.name}
                        </span>
                        <span className="text-[9px] text-muted-foreground font-mono block">
                          {(questionBank.size / 1024 / 1024).toFixed(2)} MB
                        </span>
                      </div>
                    </div>
                    <Button 
                      type="button" 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => !isUploading && setQuestionBank(null)} 
                      disabled={isUploading} 
                      className="text-muted-foreground hover:text-destructive gap-1 text-[11px] h-8 px-2 hover:bg-muted"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Remove
                    </Button>
                  </div>
                )}
              </div>

              {/* Upload Action buttons */}
              <div className="space-y-4 pt-6 mt-6 border-t border-border/40">
                {isUploading ? (
                  <div className="space-y-2.5">
                    <div className="flex justify-between text-xs text-muted-foreground font-mono">
                      <span>Uploading solved pack items...</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden border border-border/40">
                      <div 
                        className="h-full bg-gradient-to-r from-indigo-500 to-purple-600 transition-all duration-300 ease-out" 
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                ) : (
                  <Button 
                    type="submit" 
                    className="w-full font-semibold shadow-md gap-2"
                    disabled={studyFiles.length === 0 || !questionBank}
                  >
                    <Sparkles className="h-4 w-4" />
                    Solve Exam Pack
                  </Button>
                )}
                
                <div className="flex items-center gap-1.5 justify-center text-[10px] text-muted-foreground font-mono">
                  <Shield className="h-3 w-3" />
                  <span>Files are processed securely</span>
                </div>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
