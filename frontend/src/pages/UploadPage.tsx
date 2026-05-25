import React, { useState, useRef } from "react";
import { ArrowLeft, FileUp, Sparkles, Shield, Info, CheckCircle2, AlertCircle, Loader2, X, FileText, UploadCloud, HelpCircle } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { apiClient, UploadResponse } from "@/services/api";

export function UploadPage() {
  const navigate = useNavigate();
  
  // Refs
  const studyInputRef = useRef<HTMLInputElement>(null);
  const qbInputRef = useRef<HTMLInputElement>(null);

  // States
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
    if (!questionBank) {
      setError("College Question Bank / PYQ file is required.");
      return;
    }

    // Combined size check
    let totalSize = questionBank.size;
    studyFiles.forEach((f) => {
      totalSize += f.size;
    });

    if (totalSize > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setError(`Combined upload size exceeds the safe ${MAX_FILE_SIZE_MB}MB limit.`);
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    // Build form data
    const formData = new FormData();
    studyFiles.forEach((file) => {
      formData.append("study_files", file);
    });
    formData.append("question_bank", questionBank);

    try {
      const response = await apiClient.post<UploadResponse>("/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data"
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percent);
          }
        }
      });

      if (response.data && response.data.job_id) {
        navigate(`/processing/${response.data.job_id}`);
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
    <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-indigo-500/30 selection:text-white bg-grid-pattern relative overflow-x-hidden pb-12">
      {/* Ambient Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[400px] bg-[radial-gradient(ellipse_60%_60%_at_50%_-20%,rgba(99,102,241,0.08),rgba(255,255,255,0))] pointer-events-none z-0" />

      <div className="container mx-auto px-4 py-8 relative z-10 max-w-5xl">
        {/* Navigation & Header */}
        <header className="mb-8">
          <Button asChild variant="ghost" size="sm" className="gap-2 text-zinc-400 hover:text-zinc-200 mb-6" disabled={isUploading}>
            <Link to="/">
              <ArrowLeft className="h-4 w-4" />
              Back to home
            </Link>
          </Button>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-zinc-800 bg-zinc-900/60 text-[10px] font-semibold text-indigo-400 uppercase tracking-wider mb-2">
                <Sparkles className="h-3 w-3" />
                Solved Exam Intelligence
              </div>
              <h1 className="text-3xl font-extrabold tracking-tight text-zinc-100">Prepare solved exam answers</h1>
              <p className="mt-2 text-sm text-zinc-400 max-w-2xl">
                Upload your notes and question bank to generate solved exam answers. Our system will extract the questions, map them to your materials, and build a downloadable solved guide.
              </p>
            </div>
            
            <div className="flex items-center gap-3 bg-zinc-900/40 border border-zinc-800/40 p-2.5 rounded-lg text-xs self-start md:self-auto backdrop-blur-sm">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600 text-white font-bold font-mono text-[10px]">1</span>
              <span className="text-zinc-300 font-medium">Ingestion</span>
              <div className="h-px w-6 bg-zinc-800" />
              <span className="flex h-5 w-5 items-center justify-center rounded-full border border-zinc-800 text-zinc-500 font-bold font-mono text-[10px]">2</span>
              <span className="text-zinc-500">Generation</span>
            </div>
          </div>
        </header>

        {/* Error Alert Display */}
        {error && (
          <div className="mb-6 flex items-start gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-300 max-w-4xl mx-auto">
            <AlertCircle className="h-4.5 w-4.5 text-red-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-bold text-red-200 block">Ingestion Error</span>
              <p className="leading-relaxed">{error}</p>
            </div>
          </div>
        )}

        <form onSubmit={handleIngest} className="grid gap-6 md:grid-cols-5 max-w-5xl mx-auto">
          {/* Section A: Study Materials */}
          <div className="md:col-span-3 rounded-xl border border-zinc-800/40 bg-zinc-900/50 backdrop-blur-md p-6 shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4 border-b border-zinc-800/40 pb-3">
                <h3 className="font-bold text-zinc-200 text-sm flex items-center gap-2">
                  <span className="flex h-5.5 w-5.5 items-center justify-center rounded bg-indigo-500/10 text-indigo-400 font-bold text-xs">A</span>
                  Study Materials / Notes
                </h3>
                <span className="text-[10px] text-zinc-500 uppercase font-mono">1 to 5 files</span>
              </div>
              
              <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
                Add textbook chapters, slides, lecture transcripts, or notes. This represents the knowledge base the AI will refer to for answering exam questions.
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
                className={`flex min-h-[180px] flex-col items-center justify-center rounded-xl border border-dashed p-6 text-center transition-all duration-300 ease-in-out ${
                  isStudyDragging 
                    ? "border-indigo-500 bg-indigo-500/5 scale-[1.01]" 
                    : "border-zinc-800 bg-zinc-900/10 hover:bg-zinc-900/30 hover:border-indigo-500/30 cursor-pointer"
                }`}
              >
                <UploadCloud className="h-7 w-7 text-zinc-500 mb-2 group-hover:text-indigo-400 transition-colors" />
                <span className="text-xs font-bold text-zinc-300">Drag notes here or browse</span>
                <span className="text-[10px] text-zinc-500 mt-1">Supports PDF, DOCX, PPTX (Max 40MB total)</span>
              </div>

              {/* Study Materials List */}
              {studyFiles.length > 0 && (
                <div className="mt-4 space-y-2">
                  <span className="text-[10px] text-zinc-500 font-mono uppercase block">Selected Materials ({studyFiles.length}/5)</span>
                  <div className="flex flex-wrap gap-2">
                    {studyFiles.map((file, idx) => (
                      <div key={idx} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800/80 text-xs text-zinc-300">
                        <FileText className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                        <span className="truncate max-w-[150px] font-medium" title={file.name}>{file.name}</span>
                        <button type="button" onClick={() => removeStudyFile(idx)} className="text-zinc-500 hover:text-red-400 transition-colors shrink-0" disabled={isUploading}>
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 flex items-start gap-2.5 p-3 rounded-lg bg-zinc-950/40 border border-zinc-800/40 text-[11px] text-zinc-400">
              <Info className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
              <span>Ensure your materials cover the main topics in your question bank to get high-accuracy solutions.</span>
            </div>
          </div>

          {/* Section B: Question Bank */}
          <div className="md:col-span-2 rounded-xl border border-zinc-800/40 bg-zinc-900/50 backdrop-blur-md p-6 shadow-xl flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-zinc-800/40 pb-3">
                <h3 className="font-bold text-zinc-200 text-sm flex items-center gap-2">
                  <span className="flex h-5.5 w-5.5 items-center justify-center rounded bg-indigo-500/10 text-indigo-400 font-bold text-xs">B</span>
                  Question Bank / PYQ
                </h3>
                <span className="text-[10px] text-zinc-500 uppercase font-mono">1 required file</span>
              </div>
              
              <p className="text-xs text-zinc-400 leading-relaxed">
                Upload your college question bank, past papers, or homework sheet. The AI will isolate and solve these specific questions.
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
                  className={`flex min-h-[140px] flex-col items-center justify-center rounded-xl border border-dashed p-6 text-center transition-all duration-300 ease-in-out ${
                    isQbDragging 
                      ? "border-indigo-500 bg-indigo-500/5 scale-[1.01]" 
                      : "border-zinc-800 bg-zinc-900/10 hover:bg-zinc-900/30 hover:border-indigo-500/30 cursor-pointer"
                  }`}
                >
                  <FileUp className="h-6 w-6 text-zinc-500 mb-2" />
                  <span className="text-xs font-bold text-zinc-300">Choose exam paper</span>
                  <span className="text-[10px] text-zinc-500 mt-1">PDF, DOCX, PPTX</span>
                </div>
              ) : (
                /* Selected File Card */
                <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 relative flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/25 shrink-0">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div>
                      <span className="text-xs font-bold text-zinc-200 block truncate max-w-[140px]" title={questionBank.name}>
                        {questionBank.name}
                      </span>
                      <span className="text-[10px] text-zinc-500 font-mono">
                        {(questionBank.size / 1024 / 1024).toFixed(2)} MB
                      </span>
                    </div>
                  </div>
                  <Button type="button" variant="ghost" size="sm" onClick={() => !isUploading && setQuestionBank(null)} disabled={isUploading} className="text-zinc-400 hover:text-red-400 gap-1 text-[11px]">
                    <X className="h-3.5 w-3.5" />
                    Remove
                  </Button>
                </div>
              )}
            </div>

            {/* Upload Action buttons */}
            <div className="space-y-4 pt-6 mt-6 border-t border-zinc-800/40">
              {isUploading ? (
                <div className="space-y-2">
                  <div className="flex justify-between text-xs text-zinc-400 font-mono">
                    <span>Uploading solved pack items...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-zinc-900 border border-zinc-800/40 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-indigo-500 to-purple-600 transition-all duration-300 ease-out" 
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              ) : (
                <Button 
                  type="submit" 
                  className="w-full shadow-lg shadow-indigo-600/10 gap-2"
                  disabled={studyFiles.length === 0 || !questionBank}
                >
                  <Sparkles className="h-4 w-4" />
                  Solve Exam Pack
                </Button>
              )}
              
              <div className="flex items-center gap-1.5 justify-center text-[10px] text-zinc-500">
                <Shield className="h-3 w-3" />
                <span>Files are encrypted & secure</span>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
