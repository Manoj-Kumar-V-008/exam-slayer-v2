import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { 
  CheckCircle2, Download, AlertTriangle, ArrowLeft, RefreshCw, Sparkles, 
  FileText, Calendar, Clock, Database, HelpCircle, ChevronDown, ChevronUp, 
  Copy, Check, Lightbulb, Brain, Bookmark, Search, SlidersHorizontal, Eye, Loader2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { getJobStatus, JobResponse, API_BASE_URL } from "@/services/api";

export function ResultPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  // States
  const [jobData, setJobData] = useState<JobResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedQuestions, setExpandedQuestions] = useState<Record<number, boolean>>({});
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedMarks, setSelectedMarks] = useState<string>("All");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  useEffect(() => {
    if (!jobId) {
      setError("No job identifier provided.");
      setIsLoading(false);
      return;
    }

    const fetchResult = async () => {
      try {
        setIsLoading(true);
        const data = await getJobStatus(jobId);
        setJobData(data);
        
        // Auto-expand the first question if available
        if (data.study_pack?.questions && data.study_pack.questions.length > 0) {
          setExpandedQuestions({ 0: true });
        }
        
        setIsLoading(false);
      } catch (err: any) {
        console.error("Error fetching job details:", err);
        setError("Could not communicate with the backend services. Please check your connection.");
        setIsLoading(false);
      }
    };

    fetchResult();
  }, [jobId]);

  // Safe URL Construction for downloading PDF
  const getPdfDownloadUrl = (pdfUrlPath: string | null | undefined): string => {
    if (!pdfUrlPath) return "";
    
    if (pdfUrlPath.startsWith("http://") || pdfUrlPath.startsWith("https://")) {
      return pdfUrlPath;
    }

    try {
      const baseUrlObj = new URL(API_BASE_URL);
      return `${baseUrlObj.origin}${pdfUrlPath}`;
    } catch (e) {
      const match = API_BASE_URL.match(/^https?:\/\/[^\/]+/);
      const host = match ? match[0] : "http://localhost:8000";
      return `${host}${pdfUrlPath.startsWith("/") ? "" : "/"}${pdfUrlPath}`;
    }
  };

  const handleDownload = () => {
    if (!jobData?.pdf_url) return;
    const downloadUrl = getPdfDownloadUrl(jobData.pdf_url);
    if (downloadUrl) {
      window.open(downloadUrl, "_blank", "noopener,noreferrer");
    }
  };

  const handleCopyAnswer = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const toggleQuestion = (index: number) => {
    setExpandedQuestions(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const toggleExpandAll = (questionsCount: number) => {
    const allExpanded = Object.keys(expandedQuestions).length === questionsCount;
    if (allExpanded) {
      setExpandedQuestions({});
    } else {
      const newState: Record<number, boolean> = {};
      for (let i = 0; i < questionsCount; i++) {
        newState[i] = true;
      }
      setExpandedQuestions(newState);
    }
  };

  // Helper formatting for timestamps
  const formatTimestamp = (isoString: string | null | undefined) => {
    if (!isoString) return "";
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } catch (e) {
      return isoString;
    }
  };

  // Simple Markdown formatter helper
  const renderSimpleMarkdown = (text: string) => {
    if (!text) return null;
    return text.split(/\n\n+/).map((para, i) => {
      const parts = para.split(/(\*\*.*?\*\*)/g);
      return (
        <p key={i} className="mb-3 last:mb-0 leading-relaxed text-zinc-300 text-sm select-text">
          {parts.map((part, j) => {
            if (part.startsWith("**") && part.endsWith("**")) {
              return <strong key={j} className="font-semibold text-zinc-100">{part.slice(2, -2)}</strong>;
            }
            return part;
          })}
        </p>
      );
    });
  };

  // 1. Loading State
  if (isLoading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-indigo-500/30 bg-grid-pattern flex items-center justify-center">
        <div className="text-center py-12">
          <Loader2 className="mx-auto h-10 w-10 animate-spin text-indigo-500 mb-4" />
          <p className="text-sm text-zinc-400 font-medium">Fetching compiler outputs...</p>
        </div>
      </div>
    );
  }

  // 2. Job Not Found / Missing response error state
  if (error || !jobData) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-indigo-500/30 bg-grid-pattern flex flex-col justify-center py-12">
        <div className="container mx-auto px-4 flex flex-col items-center justify-center">
          <section className="w-full max-w-md rounded-xl border border-zinc-800/40 bg-zinc-900/50 backdrop-blur-md p-8 text-center shadow-2xl relative">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-zinc-900 border border-zinc-800 text-zinc-400 mb-6">
              <HelpCircle className="h-6 w-6" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">Job Not Found</h1>
            <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
              {error || "We couldn't retrieve the compilation records associated with this Job ID."}
            </p>
            <div className="mt-8 flex flex-col gap-3 justify-center">
              <Button asChild>
                <Link to="/upload">Create New Solved Pack</Link>
              </Button>
              <Button asChild variant="outline">
                <Link to="/">Back to Home</Link>
              </Button>
            </div>
          </section>
        </div>
      </div>
    );
  }

  // 3. Still Processing State (Redirect Guide)
  if (jobData.status !== "completed" && jobData.status !== "failed") {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-indigo-500/30 bg-grid-pattern flex flex-col justify-center py-12">
        <div className="container mx-auto px-4 flex flex-col items-center justify-center">
          <section className="w-full max-w-md rounded-xl border border-zinc-800/40 bg-zinc-900/50 backdrop-blur-md p-8 text-center shadow-2xl relative">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 mb-6 animate-pulse">
              <Clock className="h-6 w-6" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">Generation in Progress</h1>
            <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
              This solved answer pack is currently still being processed by our AI agents. Let's return to the status tracker.
            </p>
            <div className="mt-8 flex flex-col gap-3 justify-center">
              <Button asChild>
                <Link to={`/processing/${jobId}`}>
                  View Progress Tracker
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link to="/upload">Upload Another File</Link>
              </Button>
            </div>
          </section>
        </div>
      </div>
    );
  }

  // 4. Job Failed State
  if (jobData.status === "failed") {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-indigo-500/30 bg-grid-pattern flex flex-col justify-center py-12">
        <div className="container mx-auto px-4 flex flex-col items-center justify-center">
          <section className="w-full max-w-xl rounded-xl border border-red-500/20 bg-zinc-900/50 backdrop-blur-md p-8 text-center shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-red-500/50" />
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-red-500/10 border border-red-500/20 text-red-500 mb-6">
              <AlertTriangle className="h-6 w-6" />
            </div>
            <span className="text-[10px] font-semibold text-red-400 bg-red-500/10 border border-red-500/25 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
              Job Status Failed
            </span>
            <h1 className="mt-4 text-2xl font-bold tracking-tight text-zinc-100">Could not generate solved pack</h1>
            <p className="mt-2 text-sm text-zinc-400 leading-relaxed max-w-md mx-auto">
              The AI compilation pipeline encountered an error. Technical summary:
            </p>
            <div className="mt-4 p-4 rounded-lg bg-red-950/20 border border-red-950/40 text-left">
              <span className="text-[10px] text-red-400/80 font-mono block mb-1">Backend Error Message</span>
              <p className="text-xs text-red-300 font-mono leading-relaxed break-words">
                {jobData.error_message || "An unexpected error occurred during generation."}
              </p>
            </div>
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
        </div>
      </div>
    );
  }

  // 5. Success State (COMPLETED)
  const isPdfAvailable = !!jobData.pdf_url;
  const questions = jobData.study_pack?.questions || [];

  // Filter questions based on search query and selected marks
  const filteredQuestions = questions.filter(q => {
    const matchesSearch = 
      q.question_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      q.question_text.toLowerCase().includes(searchQuery.toLowerCase()) ||
      q.ideal_answer.toLowerCase().includes(searchQuery.toLowerCase());
      
    if (selectedMarks === "All") return matchesSearch;
    
    // Normalize string likely_marks
    const qMarks = q.likely_marks || "";
    return matchesSearch && qMarks.toLowerCase().includes(selectedMarks.toLowerCase().replace(" marks", ""));
  });

  const getMarksBadgeClass = (marks: string | null | undefined) => {
    const m = (marks || "").toLowerCase();
    if (m.includes("2")) {
      return "bg-emerald-500/10 border-emerald-500/30 text-emerald-400";
    } else if (m.includes("5")) {
      return "bg-indigo-500/10 border-indigo-500/30 text-indigo-400";
    } else if (m.includes("10")) {
      return "bg-amber-500/10 border-amber-500/30 text-amber-400";
    }
    return "bg-zinc-500/10 border-zinc-500/30 text-zinc-400";
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-indigo-500/30 bg-grid-pattern relative overflow-x-hidden pb-20">
      {/* Ambient Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[400px] bg-[radial-gradient(ellipse_60%_60%_at_50%_-20%,rgba(99,102,241,0.08),rgba(255,255,255,0))] pointer-events-none z-0" />

      <div className="container mx-auto px-4 py-8 relative z-10 max-w-4xl">
        {/* Navigation & Header */}
        <header className="mb-8 flex justify-between items-center">
          <Button asChild variant="ghost" size="sm" className="gap-2 text-zinc-400 hover:text-zinc-200" disabled={isLoading}>
            <Link to="/upload">
              <ArrowLeft className="h-4 w-4" />
              Upload Another
            </Link>
          </Button>
          <span className="text-xs text-zinc-500 font-mono">Job ID: {jobId}</span>
        </header>

        {/* Main Solved Alert & Actions Card */}
        <section className="rounded-xl border border-zinc-800/40 bg-zinc-900/50 backdrop-blur-md p-6 md:p-8 shadow-2xl relative mb-10 overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 blur-2xl rounded-full" />
          
          <div className="flex flex-col md:flex-row gap-6 items-start md:items-center justify-between">
            <div className="flex gap-4 items-center">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                <CheckCircle2 className="h-7 w-7" />
              </div>
              <div>
                <span className="text-[10px] font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/25 px-2.5 py-0.5 rounded-full uppercase tracking-wider flex items-center gap-1.5 w-max mb-1.5">
                  <Sparkles className="h-3 w-3" />
                  Answer Pack Ready
                </span>
                <h1 className="text-2xl font-bold tracking-tight text-zinc-100">
                  {jobData.study_pack?.title || "Exam Solved Answer Pack"}
                </h1>
                <p className="text-xs text-zinc-400 mt-1 max-w-md">
                  All identified questions from your question bank have been solved using your uploaded study materials.
                </p>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto shrink-0">
              <Button 
                onClick={handleDownload}
                disabled={!isPdfAvailable}
                className="gap-2 font-semibold shadow-lg shadow-indigo-600/15 w-full sm:w-auto"
              >
                <Download className="h-4 w-4" />
                Download Solved PDF
              </Button>
            </div>
          </div>

          {/* Conditional Metadata Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mt-6 pt-6 border-t border-zinc-800/40">
            {jobData.question_bank_name && (
              <div className="bg-zinc-950/40 border border-zinc-800/40 p-3 rounded-lg">
                <span className="text-[9px] text-zinc-500 font-mono block uppercase mb-0.5">Question Bank</span>
                <span className="text-xs text-zinc-300 font-medium truncate block" title={jobData.question_bank_name}>
                  {jobData.question_bank_name}
                </span>
              </div>
            )}
            {jobData.study_file_count !== undefined && jobData.study_file_count > 0 && (
              <div className="bg-zinc-950/40 border border-zinc-800/40 p-3 rounded-lg">
                <span className="text-[9px] text-zinc-500 font-mono block uppercase mb-0.5">Source Notes</span>
                <span className="text-xs text-zinc-300 font-medium block">
                  {jobData.study_file_count} Study Files
                </span>
              </div>
            )}
            {jobData.completed_at && (
              <div className="bg-zinc-950/40 border border-zinc-800/40 p-3 rounded-lg">
                <span className="text-[9px] text-zinc-500 font-mono block uppercase mb-0.5">Completed At</span>
                <span className="text-xs text-zinc-300 font-medium block">
                  {formatTimestamp(jobData.completed_at)}
                </span>
              </div>
            )}
            {questions.length > 0 && (
              <div className="bg-zinc-950/40 border border-zinc-800/40 p-3 rounded-lg">
                <span className="text-[9px] text-zinc-500 font-mono block uppercase mb-0.5">Total Solved</span>
                <span className="text-xs text-zinc-300 font-medium block">
                  {questions.length} Questions
                </span>
              </div>
            )}
          </div>

          {!isPdfAvailable && (
            <div className="mt-4 flex items-start gap-2.5 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-xs text-yellow-300 font-sans">
              <AlertTriangle className="h-4.5 w-4.5 text-yellow-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-yellow-200 block">PDF Unavailable</span>
                <p className="leading-relaxed mt-0.5">The job completed but the PDF is missing from the output directory. You can preview answers below.</p>
              </div>
            </div>
          )}
        </section>

        {/* Solved Answers Preview Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-zinc-200 flex items-center gap-2">
              <Eye className="h-5 w-5 text-indigo-400" />
              Solved Answer Preview
            </h2>
            <p className="text-xs text-zinc-500 mt-0.5 font-sans">Review answers, memory tips, and explanations in-browser.</p>
          </div>

          {questions.length > 0 && (
            <button
              onClick={() => toggleExpandAll(questions.length)}
              className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors font-medium self-start sm:self-auto select-none cursor-pointer"
            >
              {Object.keys(expandedQuestions).length === questions.length ? "Collapse All" : "Expand All"}
            </button>
          )}
        </div>

        {/* Search & Filter Bar */}
        <div className="flex flex-col md:flex-row gap-3 mb-6">
          {/* Search box */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
            <input
              type="text"
              placeholder="Search solved questions or keywords..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-zinc-900/60 border border-zinc-800/80 rounded-lg pl-9 pr-4 py-2 text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500/50 transition-colors"
            />
          </div>

          {/* Filters */}
          <div className="flex gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none shrink-0">
            {["All", "2 Marks", "5 Marks", "10 Marks"].map((marksOption) => (
              <button
                key={marksOption}
                onClick={() => setSelectedMarks(marksOption)}
                className={`px-3 py-2 text-xs font-semibold rounded-lg border transition-all duration-200 whitespace-nowrap cursor-pointer select-none ${
                  selectedMarks === marksOption
                    ? "bg-indigo-600 border-indigo-500 text-white shadow-md shadow-indigo-600/10"
                    : "bg-zinc-900/30 border-zinc-800/40 text-zinc-400 hover:text-zinc-200 hover:border-zinc-700/60"
                }`}
              >
                {marksOption}
              </button>
            ))}
          </div>
        </div>

        {/* Questions Listing */}
        {filteredQuestions.length === 0 ? (
          <div className="text-center py-16 rounded-xl border border-zinc-800/40 bg-zinc-900/10">
            <HelpCircle className="h-10 w-10 text-zinc-600 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-zinc-400 font-sans">No matching questions found</h3>
            <p className="text-xs text-zinc-500 mt-1 font-sans">Try adjusting your search criteria or marks filter chips.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredQuestions.map((q, idx) => {
              // Map back the original index of the question in the questions array
              const originalIndex = questions.indexOf(q);
              const isExpanded = !!expandedQuestions[originalIndex];

              return (
                <div 
                  key={originalIndex}
                  className={`rounded-xl border transition-all duration-300 overflow-hidden ${
                    isExpanded 
                      ? "border-zinc-800 bg-zinc-900/30 shadow-xl" 
                      : "border-zinc-900 bg-zinc-900/15 hover:border-zinc-800/60 hover:bg-zinc-900/25"
                  }`}
                >
                  {/* Card Header (Click to toggle expansion) */}
                  <header 
                    onClick={() => toggleQuestion(originalIndex)}
                    className="flex justify-between items-center p-4 cursor-pointer select-none gap-4"
                  >
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs font-mono font-bold text-indigo-400">
                        {q.question_number}
                      </span>
                      {q.likely_marks && (
                        <span className={`text-[9px] px-2 py-0.5 rounded-full border uppercase tracking-wider font-bold ${getMarksBadgeClass(q.likely_marks)}`}>
                          {q.likely_marks}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <span className="text-xs font-semibold text-zinc-300 truncate block font-sans">
                        {q.question_text}
                      </span>
                    </div>

                    <div className="text-zinc-500 hover:text-zinc-300 transition-colors shrink-0">
                      {isExpanded ? (
                        <ChevronUp className="h-4.5 w-4.5" />
                      ) : (
                        <ChevronDown className="h-4.5 w-4.5" />
                      )}
                    </div>
                  </header>

                  {/* Card Body (Visible when expanded) */}
                  {isExpanded && (
                    <div className="px-5 pb-6 pt-2 border-t border-zinc-900/60 space-y-5 animate-in fade-in-20 duration-200">
                      
                      {/* Question Text Box */}
                      <div className="p-3.5 rounded-lg bg-zinc-950/60 border border-zinc-900/60 text-xs text-zinc-400 font-sans italic leading-relaxed">
                        <strong className="block text-[10px] text-zinc-500 uppercase tracking-wide font-mono not-italic mb-1">Question Wording</strong>
                        "{q.question_text}"
                      </div>

                      {/* Ideal Answer Section */}
                      <div className="space-y-2">
                        <div className="flex justify-between items-center">
                          <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider font-mono flex items-center gap-1.5">
                            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                            Ideal Exam Answer
                          </h4>
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCopyAnswer(q.ideal_answer, originalIndex);
                            }}
                            className="text-[10px] text-zinc-500 hover:text-indigo-400 gap-1.5 h-7 px-2.5 rounded-md hover:bg-zinc-900/40"
                          >
                            {copiedIndex === originalIndex ? (
                              <>
                                <Check className="h-3 w-3 text-emerald-400" />
                                Copied!
                              </>
                            ) : (
                              <>
                                <Copy className="h-3 w-3" />
                                Copy text
                              </>
                            )}
                          </Button>
                        </div>
                        <div className="p-4 rounded-lg bg-indigo-500/[0.02] border border-indigo-500/10 font-sans select-text">
                          {renderSimpleMarkdown(q.ideal_answer)}
                        </div>
                      </div>

                      {/* Intuitive Explanation */}
                      <div className="space-y-2">
                        <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider font-mono flex items-center gap-1.5">
                          <Lightbulb className="h-4 w-4 text-amber-400" />
                          Intuitive Concept breakdown
                        </h4>
                        <div className="p-4 rounded-lg bg-zinc-950/30 border border-zinc-800/40 backdrop-blur-sm">
                          {renderSimpleMarkdown(q.simple_explanation)}
                        </div>
                      </div>

                      {/* Memory Trick (If present) */}
                      {q.memory_trick && (
                        <div className="space-y-2">
                          <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider font-mono flex items-center gap-1.5">
                            <Brain className="h-4 w-4 text-purple-400" />
                            Memory Aid / Mnemonic
                          </h4>
                          <div className="p-4 rounded-lg bg-purple-500/[0.02] border border-purple-500/10 flex items-start gap-3">
                            <div className="h-7 w-7 rounded bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center shrink-0">
                              <Brain className="h-4 w-4" />
                            </div>
                            <div className="flex-1">
                              <p className="text-sm font-semibold text-purple-200">Trick:</p>
                              <p className="text-xs text-zinc-400 mt-1 leading-relaxed font-sans select-text">
                                {q.memory_trick}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Revision Points */}
                      {q.revision_points && q.revision_points.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider font-mono flex items-center gap-1.5">
                            <Bookmark className="h-4 w-4 text-indigo-400" />
                            Key Revision Points
                          </h4>
                          <ul className="space-y-2 pl-1 select-text">
                            {q.revision_points.map((pt, pidx) => (
                              <li key={pidx} className="flex items-start gap-2.5 text-xs text-zinc-400 leading-relaxed font-sans">
                                <span className="flex h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-500 mt-2" />
                                <span>{pt}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
