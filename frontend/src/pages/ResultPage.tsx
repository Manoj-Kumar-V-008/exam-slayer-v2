import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { 
  CheckCircle2, Download, AlertTriangle, ArrowLeft, Sparkles, 
  FileText, Clock, HelpCircle, ChevronDown, ChevronUp, 
  Copy, Check, Lightbulb, Brain, Bookmark, Search, Eye, Loader2,
  BookOpen, AlertCircle, RefreshCw
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { getJobStatus, JobResponse, API_BASE_URL, SolvedQuestion, StudyPackSection } from "@/services/api";
import { Navbar } from "@/components/Navbar";

export function ResultPage() {
  const { jobId } = useParams<{ jobId: string }>();

  // States
  const [jobData, setJobData] = useState<JobResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Solved Answer Pack States
  const [expandedQuestions, setExpandedQuestions] = useState<Record<number, boolean>>({});
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedMarks, setSelectedMarks] = useState<string>("All");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // Study Pack States
  const [activeSectionIndex, setActiveSectionIndex] = useState<number>(0);
  const [expandedSections, setExpandedSections] = useState<Record<number, boolean>>({});

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
        
        // Auto-expand the first item if available
        if (data.mode === "ANSWER_PACK" && data.answer_pack?.questions && data.answer_pack.questions.length > 0) {
          setExpandedQuestions({ 0: true });
        } else if (data.mode === "STUDY_PACK" && data.study_pack?.sections && data.study_pack.sections.length > 0) {
          setExpandedSections({ 0: true });
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

  const toggleExpandAllQuestions = (questionsCount: number) => {
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

  const toggleSection = (index: number) => {
    setExpandedSections(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
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
        <p key={i} className="mb-3 last:mb-0 leading-relaxed text-muted-foreground text-sm select-text">
          {parts.map((part, j) => {
            if (part.startsWith("**") && part.endsWith("**")) {
              return <strong key={j} className="font-semibold text-foreground">{part.slice(2, -2)}</strong>;
            }
            return part;
          })}
        </p>
      );
    });
  };

  const getMarksBadgeClass = (marks: string | null | undefined) => {
    const m = (marks || "").toLowerCase();
    if (m.includes("2")) {
      return "bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400";
    } else if (m.includes("5")) {
      return "bg-indigo-500/10 border-indigo-500/30 text-indigo-600 dark:text-indigo-400";
    } else if (m.includes("10")) {
      return "bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400";
    }
    return "bg-muted border-border text-muted-foreground";
  };

  // 1. Loading State
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background text-foreground selection:bg-primary/20 bg-grid-pattern flex flex-col transition-colors duration-300">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center py-12 bg-card/30 border border-border p-8 rounded-xl backdrop-blur-sm shadow-sm max-w-sm w-full">
            <Loader2 className="mx-auto h-9 w-9 animate-spin text-primary mb-4" />
            <p className="text-sm text-muted-foreground font-medium">Fetching compiler outputs...</p>
          </div>
        </div>
      </div>
    );
  }

  // 2. Job Not Found / Error state
  if (error || !jobData) {
    return (
      <div className="min-h-screen bg-background text-foreground selection:bg-primary/20 bg-grid-pattern flex flex-col transition-colors duration-300">
        <Navbar />
        <div className="flex-1 flex flex-col justify-center py-12 relative z-10">
          <div className="container mx-auto px-4 flex flex-col items-center justify-center">
            <section className="w-full max-w-md rounded-xl border border-border bg-card/45 backdrop-blur-md p-8 text-center shadow-xl relative">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-muted border border-border text-muted-foreground mb-6">
                <HelpCircle className="h-6 w-6" />
              </div>
              <h1 className="text-xl font-bold tracking-tight">Job Not Found</h1>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                {error || "We couldn't retrieve the compilation records associated with this Job ID."}
              </p>
              <div className="mt-8 flex flex-col gap-3 justify-center">
                <Button asChild className="font-semibold">
                  <Link to="/upload">Create New Pack</Link>
                </Button>
                <Button asChild variant="outline" className="border-border/80 font-semibold">
                  <Link to="/">Back to Home</Link>
                </Button>
              </div>
            </section>
          </div>
        </div>
      </div>
    );
  }

  // 3. Still Processing State (Redirect Guide)
  if (jobData.status !== "completed" && jobData.status !== "failed") {
    return (
      <div className="min-h-screen bg-background text-foreground selection:bg-primary/20 bg-grid-pattern flex flex-col transition-colors duration-300">
        <Navbar />
        <div className="flex-1 flex flex-col justify-center py-12 relative z-10">
          <div className="container mx-auto px-4 flex flex-col items-center justify-center">
            <section className="w-full max-w-md rounded-xl border border-border bg-card/45 backdrop-blur-md p-8 text-center shadow-xl relative">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 border border-primary/20 text-primary mb-6 animate-pulse">
                <Clock className="h-6 w-6" />
              </div>
              <h1 className="text-xl font-bold tracking-tight">Generation in Progress</h1>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                This compiler pack is currently still being processed by our AI pipeline. Let's return to the progress tracker.
              </p>
              <div className="mt-8 flex flex-col gap-3 justify-center">
                <Button asChild className="font-semibold">
                  <Link to={`/processing/${jobId}`}>
                    View Progress Tracker
                  </Link>
                </Button>
                <Button asChild variant="outline" className="border-border/80 font-semibold">
                  <Link to="/upload">Upload Another File</Link>
                </Button>
              </div>
            </section>
          </div>
        </div>
      </div>
    );
  }

  // 4. Job Failed State
  if (jobData.status === "failed") {
    return (
      <div className="min-h-screen bg-background text-foreground selection:bg-primary/20 bg-grid-pattern flex flex-col transition-colors duration-300">
        <Navbar />
        <div className="flex-1 flex flex-col justify-center py-12 relative z-10">
          <div className="container mx-auto px-4 flex flex-col items-center justify-center">
            <section className="w-full max-w-xl rounded-xl border border-destructive/25 bg-card/45 backdrop-blur-md p-8 text-center shadow-xl relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1 bg-destructive" />
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10 border border-destructive/20 text-destructive mb-6">
                <AlertTriangle className="h-6 w-6" />
              </div>
              <span className="text-[10px] font-semibold text-destructive bg-destructive/10 border border-destructive/25 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                Job Failed
              </span>
              <h1 className="mt-4 text-2xl font-bold tracking-tight">Could not generate pack</h1>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed max-w-md mx-auto">
                The compiler pipeline encountered an error. Technical summary:
              </p>
              <div className="mt-4 p-4 rounded-lg bg-destructive/5 border border-destructive/20 text-left">
                <span className="text-[10px] text-destructive/80 font-mono block mb-1">Backend Error Message</span>
                <p className="text-xs text-destructive font-mono leading-relaxed break-all">
                  {jobData.error_message || "An unexpected error occurred during generation."}
                </p>
              </div>
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
          </div>
        </div>
      </div>
    );
  }

  // 5. Success State (COMPLETED)
  const isPdfAvailable = !!jobData.pdf_url;
  const isStudyMode = jobData.mode === "STUDY_PACK";
  const questions = jobData.answer_pack?.questions || [];

  // Branch layouts: STUDY_PACK vs ANSWER_PACK
  const renderStudyPackLayout = () => {
    const studyPack = jobData.study_pack;
    if (!studyPack || !studyPack.sections || studyPack.sections.length === 0) {
      return (
        <div className="text-center py-12 rounded-xl border border-border bg-card/20">
          <HelpCircle className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
          <h3 className="text-sm font-bold text-muted-foreground">No sections generated</h3>
          <p className="text-xs text-muted-foreground mt-1">Please try uploading again with more detailed materials.</p>
        </div>
      );
    }

    const sections = studyPack.sections;
    const activeSection = sections[activeSectionIndex] || sections[0];

    return (
      <div className="grid gap-6 md:grid-cols-4 items-start">
        {/* Desktop Left Sidebar Sections Navigation */}
        <aside className="hidden md:flex flex-col gap-2 col-span-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 px-2 font-mono">Sections Index</span>
          <div className="flex flex-col gap-1">
            {sections.map((sec, idx) => (
              <button
                key={idx}
                onClick={() => setActiveSectionIndex(idx)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer select-none truncate ${
                  activeSectionIndex === idx
                    ? "bg-primary border-primary/20 text-primary-foreground shadow-sm shadow-primary/10"
                    : "bg-card/25 border-border/40 text-muted-foreground hover:text-foreground hover:bg-card/60"
                }`}
                title={sec.heading}
              >
                {idx + 1}. {sec.heading}
              </button>
            ))}
          </div>
        </aside>

        {/* Mobile Accordion / Desktop Content Pane */}
        <div className="md:col-span-3 space-y-6">
          {/* Mobile Layout: Accordion for all sections */}
          <div className="md:hidden space-y-3">
            {sections.map((sec, idx) => {
              const isExpanded = !!expandedSections[idx];
              return (
                <div 
                  key={idx} 
                  className={`rounded-xl border transition-all overflow-hidden ${
                    isExpanded 
                      ? "border-primary/40 bg-card/40 shadow-md" 
                      : "border-border/60 bg-card/20 hover:border-border"
                  }`}
                >
                  <header 
                    onClick={() => toggleSection(idx)}
                    className="flex justify-between items-center p-4 cursor-pointer select-none gap-3"
                  >
                    <span className="text-xs font-bold text-foreground truncate">
                      {idx + 1}. {sec.heading}
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    )}
                  </header>

                  {isExpanded && (
                    <div className="p-4 border-t border-border/40 space-y-5 animate-in fade-in-20 duration-200">
                      {renderSectionDetails(sec)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Desktop Content Pane */}
          <div className="hidden md:block space-y-6 animate-in fade-in duration-300">
            <div className="rounded-xl border border-border bg-card/20 p-6 md:p-8 space-y-6 shadow-md relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 blur-3xl rounded-full pointer-events-none" />
              {renderSectionDetails(activeSection)}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderSectionDetails = (sec: StudyPackSection) => {
    return (
      <div className="space-y-6 text-left">
        {/* Heading & Summary */}
        <div>
          <h3 className="text-lg font-bold text-foreground border-b border-border/40 pb-2 mb-3">{sec.heading}</h3>
          <div className="p-4 rounded-lg bg-card/50 border border-border/80 shadow-sm leading-relaxed text-sm select-text">
            <span className="text-[9px] font-bold text-primary uppercase font-mono block mb-1">Executive Summary</span>
            {sec.summary}
          </div>
        </div>

        {/* Intuitive concept breakdown */}
        <div className="space-y-2">
          <h4 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono flex items-center gap-1.5">
            <Lightbulb className="h-4 w-4 text-amber-500 dark:text-amber-400" />
            Plain-English Analogy / Concept Breakdown
          </h4>
          <div className="p-4 rounded-lg bg-muted/20 border border-border select-text">
            {renderSimpleMarkdown(sec.simple_explanation)}
          </div>
        </div>

        {/* Memory Aid */}
        {sec.memory_trick && (
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono flex items-center gap-1.5">
              <Brain className="h-4 w-4 text-purple-500" />
              Memory Aid / Mnemonic
            </h4>
            <div className="p-4 rounded-lg bg-purple-500/[0.02] border border-purple-500/10 flex items-start gap-3 shadow-sm select-text">
              <div className="h-7 w-7 rounded bg-purple-500/10 border border-purple-500/20 text-purple-500 flex items-center justify-center shrink-0">
                <Brain className="h-4 w-4" />
              </div>
              <div>
                <span className="text-xs font-bold text-purple-600 dark:text-purple-300 block">Acronym or Mnemonic Hack:</span>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{sec.memory_trick}</p>
              </div>
            </div>
          </div>
        )}

        {/* Key Points */}
        {sec.key_points && sec.key_points.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono flex items-center gap-1.5">
              <Bookmark className="h-4 w-4 text-primary" />
              Key Concept Highlights
            </h4>
            <ul className="space-y-2 pl-1 select-text">
              {sec.key_points.map((pt, pidx) => (
                <li key={pidx} className="flex items-start gap-2.5 text-xs text-muted-foreground leading-relaxed">
                  <span className="flex h-1.5 w-1.5 shrink-0 rounded-full bg-primary mt-2" />
                  <span>{pt}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Exam Tip */}
        {sec.exam_tip && (
          <div className="p-3.5 rounded-lg bg-amber-500/[0.02] border border-amber-500/25 flex items-start gap-2.5 text-xs select-text">
            <AlertCircle className="h-4.5 w-4.5 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-amber-600 dark:text-amber-400 block font-mono uppercase text-[9px] tracking-wider">Exam Trap Alert</span>
              <p className="mt-0.5 text-muted-foreground leading-relaxed">{sec.exam_tip}</p>
            </div>
          </div>
        )}

        {/* Likely exam questions */}
        {((sec.likely_questions_2_marks && sec.likely_questions_2_marks.length > 0) ||
          (sec.likely_questions_5_marks && sec.likely_questions_5_marks.length > 0) ||
          (sec.likely_questions_10_marks && sec.likely_questions_10_marks.length > 0)) && (
          <div className="space-y-3 pt-2 border-t border-border/40">
            <h4 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
              Likely Exam Questions
            </h4>
            
            <div className="space-y-2.5">
              {sec.likely_questions_2_marks && sec.likely_questions_2_marks.length > 0 && (
                <div>
                  <span className="text-[9px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded font-mono uppercase tracking-wider">2 Marks (Short)</span>
                  <ul className="mt-1.5 space-y-1.5 pl-1.5 text-xs text-muted-foreground select-text">
                    {sec.likely_questions_2_marks.map((q, i) => <li key={i} className="flex gap-2"><span>•</span><span>{q}</span></li>)}
                  </ul>
                </div>
              )}

              {sec.likely_questions_5_marks && sec.likely_questions_5_marks.length > 0 && (
                <div className="pt-1">
                  <span className="text-[9px] font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded font-mono uppercase tracking-wider">5 Marks (Medium)</span>
                  <ul className="mt-1.5 space-y-1.5 pl-1.5 text-xs text-muted-foreground select-text">
                    {sec.likely_questions_5_marks.map((q, i) => <li key={i} className="flex gap-2"><span>•</span><span>{q}</span></li>)}
                  </ul>
                </div>
              )}

              {sec.likely_questions_10_marks && sec.likely_questions_10_marks.length > 0 && (
                <div className="pt-1">
                  <span className="text-[9px] font-bold text-amber-600 dark:text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded font-mono uppercase tracking-wider">10 Marks (Essay)</span>
                  <ul className="mt-1.5 space-y-1.5 pl-1.5 text-xs text-muted-foreground select-text">
                    {sec.likely_questions_10_marks.map((q, i) => <li key={i} className="flex gap-2"><span>•</span><span>{q}</span></li>)}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Common Mistakes */}
        {sec.common_mistakes && sec.common_mistakes.length > 0 && (
          <div className="space-y-2 pt-2 border-t border-border/40 select-text">
            <h4 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
              Common Student Pitfalls
            </h4>
            <ul className="space-y-1.5">
              {sec.common_mistakes.map((pt, i) => (
                <li key={i} className="flex items-start gap-2.5 text-xs text-muted-foreground">
                  <span className="text-red-500 shrink-0 font-bold font-mono">✗</span>
                  <span>{pt}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Revision Cheatsheet */}
        {sec.revision_cheatsheet && sec.revision_cheatsheet.length > 0 && (
          <div className="space-y-2 pt-2 border-t border-border/40 select-text">
            <h4 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono flex items-center gap-1.5">
              <Bookmark className="h-4 w-4 text-primary" />
              Quick Revision Cheatsheet
            </h4>
            <div className="p-4 rounded-lg bg-card border border-border/80 shadow-inner grid gap-2 sm:grid-cols-2">
              {sec.revision_cheatsheet.map((pt, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                  <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0 mt-0.5" />
                  <span>{pt}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderAnswerPackLayout = () => {
    const answerPack = jobData.answer_pack;
    if (!answerPack || !answerPack.questions || answerPack.questions.length === 0) {
      return (
        <div className="text-center py-12 rounded-xl border border-border bg-card/20">
          <HelpCircle className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
          <h3 className="text-sm font-bold text-muted-foreground">No questions solved</h3>
          <p className="text-xs text-muted-foreground mt-1">Please try uploading again with different materials.</p>
        </div>
      );
    }

    const questions = answerPack.questions;

    // Filter questions based on search query and selected marks
    const filteredQuestions = questions.filter(q => {
      const matchesSearch = 
        q.question_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
        q.question_text.toLowerCase().includes(searchQuery.toLowerCase()) ||
        q.answer.toLowerCase().includes(searchQuery.toLowerCase());
        
      if (selectedMarks === "All") return matchesSearch;
      
      const qMarks = q.marks_category || "";
      return matchesSearch && qMarks.toLowerCase().includes(selectedMarks.toLowerCase().replace(" marks", ""));
    });

    return (
      <div className="space-y-6">
        {/* Search & Filter Bar */}
        <div className="flex flex-col md:flex-row gap-3">
          {/* Search box */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search solved questions or keywords..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-card border border-border/80 rounded-lg pl-9 pr-4 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 transition-colors shadow-sm"
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
                    ? "bg-primary border-primary/20 text-primary-foreground shadow-sm shadow-primary/10"
                    : "bg-card/30 border-border/40 text-muted-foreground hover:text-foreground hover:border-border"
                }`}
              >
                {marksOption}
              </button>
            ))}
          </div>
        </div>

        {/* Questions Listing Accordion */}
        {filteredQuestions.length === 0 ? (
          <div className="text-center py-16 rounded-xl border border-border bg-card/15 shadow-sm">
            <HelpCircle className="h-10 w-10 text-muted-foreground/60 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-muted-foreground">No matching questions found</h3>
            <p className="text-xs text-muted-foreground mt-1">Try adjusting your search criteria or marks filter chips.</p>
          </div>
        ) : (
          <div className="space-y-4 text-left">
            {filteredQuestions.map((q, idx) => {
              const originalIndex = questions.indexOf(q);
              const isExpanded = !!expandedQuestions[originalIndex];

              return (
                <div 
                  key={originalIndex}
                  className={`rounded-xl border transition-all duration-300 overflow-hidden shadow-sm ${
                    isExpanded 
                      ? "border-primary bg-card/35 shadow-md" 
                      : "border-border bg-card/15 hover:border-border/80 hover:bg-card/25"
                  }`}
                >
                  {/* Card Header (Click to toggle expansion) */}
                  <header 
                    onClick={() => toggleQuestion(originalIndex)}
                    className="flex justify-between items-center p-4 cursor-pointer select-none gap-4"
                  >
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs font-mono font-bold text-primary">
                        {q.question_number}
                      </span>
                      {q.marks_category && (
                        <span className={`text-[9px] px-2 py-0.5 rounded-full border uppercase tracking-wider font-bold ${getMarksBadgeClass(q.marks_category)}`}>
                          {q.marks_category}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <span className="text-xs font-semibold text-foreground truncate block">
                        {q.question_text}
                      </span>
                    </div>

                    <div className="text-muted-foreground hover:text-foreground transition-colors shrink-0">
                      {isExpanded ? (
                        <ChevronUp className="h-4.5 w-4.5" />
                      ) : (
                        <ChevronDown className="h-4.5 w-4.5" />
                      )}
                    </div>
                  </header>

                  {/* Card Body (Visible when expanded) */}
                  {isExpanded && (
                    <div className="px-5 pb-6 pt-2 border-t border-border/40 space-y-5 animate-in fade-in-20 duration-200">
                      
                      {/* Question Text Box */}
                      <div className="p-3.5 rounded-lg bg-muted/30 border border-border/50 text-xs text-muted-foreground font-sans italic leading-relaxed">
                        <strong className="block text-[10px] text-muted-foreground/60 uppercase tracking-wide font-mono not-italic mb-1">Question Wording</strong>
                        "{q.question_text}"
                      </div>

                      {/* Ideal Answer Section */}
                      <div className="space-y-2">
                        <div className="flex justify-between items-center">
                          <h4 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono flex items-center gap-1.5">
                            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                            Ideal Exam Answer
                          </h4>
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCopyAnswer(q.answer, originalIndex);
                            }}
                            className="text-[10px] text-muted-foreground hover:text-primary gap-1.5 h-7 px-2.5 rounded-md hover:bg-muted"
                          >
                            {copiedIndex === originalIndex ? (
                              <>
                                <Check className="h-3 w-3 text-emerald-500" />
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
                        <div className="p-4 rounded-lg bg-card border border-border select-text">
                          {renderSimpleMarkdown(q.answer)}
                        </div>
                      </div>

                      {/* Intuitive Explanation */}
                      <div className="space-y-2">
                        <h4 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono flex items-center gap-1.5">
                          <Lightbulb className="h-4 w-4 text-amber-500 dark:text-amber-400" />
                          Intuitive Concept breakdown
                        </h4>
                        <div className="p-4 rounded-lg bg-muted/20 border border-border select-text">
                          {renderSimpleMarkdown(q.simple_explanation)}
                        </div>
                      </div>

                      {/* Memory Trick (If present) */}
                      {q.memory_trick && (
                        <div className="space-y-2">
                          <h4 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono flex items-center gap-1.5">
                            <Brain className="h-4 w-4 text-purple-500" />
                            Memory Aid / Mnemonic
                          </h4>
                          <div className="p-4 rounded-lg bg-purple-500/[0.02] border border-purple-500/10 flex items-start gap-3 shadow-sm select-text">
                            <div className="h-7 w-7 rounded bg-purple-500/10 border border-purple-500/20 text-purple-500 flex items-center justify-center shrink-0">
                              <Brain className="h-4 w-4" />
                            </div>
                            <div className="flex-1">
                              <p className="text-xs font-bold text-purple-600 dark:text-purple-300">Trick:</p>
                              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                                {q.memory_trick}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Revision Points */}
                      {q.quick_revision_points && q.quick_revision_points.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono flex items-center gap-1.5">
                            <Bookmark className="h-4 w-4 text-primary" />
                            Key Revision Points
                          </h4>
                          <ul className="space-y-2 pl-1 select-text">
                            {q.quick_revision_points.map((pt, pidx) => (
                              <li key={pidx} className="flex items-start gap-2.5 text-xs text-muted-foreground leading-relaxed">
                                <span className="flex h-1.5 w-1.5 shrink-0 rounded-full bg-primary mt-2" />
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
    );
  };

  // Get total count of items for header display
  const itemsCount = isStudyMode 
    ? (jobData.study_pack?.sections?.length || 0)
    : (jobData.answer_pack?.questions?.length || 0);

  const packTitle = isStudyMode 
    ? (jobData.study_pack?.title || "Exam Study Guide Pack") 
    : (jobData.answer_pack?.title || "Exam Solved Answer Pack");

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/20 bg-grid-pattern relative overflow-x-hidden pb-20 transition-colors duration-300">
      {/* Shared Navigation Header */}
      <Navbar />

      {/* Ambient Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[400px] bg-[radial-gradient(ellipse_60%_60%_at_50%_-20%,rgba(99,102,241,0.08),transparent)] pointer-events-none z-0 dark:opacity-70 opacity-40" />

      <div className="container mx-auto px-4 py-8 relative z-10 max-w-4xl">
        {/* Navigation & Header */}
        <header className="mb-8 flex justify-between items-center">
          <Button asChild variant="ghost" size="sm" className="gap-2 text-muted-foreground hover:text-foreground">
            <Link to="/upload">
              <ArrowLeft className="h-4 w-4" />
              Upload Another
            </Link>
          </Button>
          <span className="text-xs text-muted-foreground font-mono">Job ID: {jobId}</span>
        </header>

        {/* Main Solved Alert & Actions Card */}
        <section className="rounded-xl border border-border bg-card/45 backdrop-blur-md p-6 md:p-8 shadow-md relative mb-10 overflow-hidden text-left">
          <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 blur-2xl rounded-full" />
          
          <div className="flex flex-col md:flex-row gap-6 items-start md:items-center justify-between">
            <div className="flex gap-4 items-center">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary/10 border border-primary/20 text-primary">
                <CheckCircle2 className="h-7 w-7" />
              </div>
              <div>
                <span className="text-[10px] font-semibold text-primary bg-primary/10 border border-primary/25 px-2.5 py-0.5 rounded-full uppercase tracking-wider flex items-center gap-1.5 w-max mb-1.5">
                  <Sparkles className="h-3 w-3" />
                  {isStudyMode ? "Study Pack Compiled" : "Answer Pack Compiled"}
                </span>
                <h1 className="text-2xl font-bold tracking-tight">
                  {packTitle}
                </h1>
                <p className="text-xs text-muted-foreground mt-1 max-w-md">
                  {isStudyMode 
                    ? "Your study material has been summarized into chapters, key points, memory tricks, and predictive questions."
                    : "All identified questions from your question bank have been solved using your uploaded study materials."
                  }
                </p>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto shrink-0">
              <Button 
                onClick={handleDownload}
                disabled={!isPdfAvailable}
                className="gap-2 font-semibold shadow-md w-full sm:w-auto"
              >
                <Download className="h-4 w-4" />
                Download PDF
              </Button>
            </div>
          </div>

          {/* Conditional Metadata Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mt-6 pt-6 border-t border-border/40">
            {jobData.question_bank_name ? (
              <div className="bg-background/40 border border-border/50 p-3 rounded-lg">
                <span className="text-[9px] text-muted-foreground font-mono block uppercase mb-0.5">Question Paper</span>
                <span className="text-xs text-foreground font-semibold truncate block" title={jobData.question_bank_name}>
                  {jobData.question_bank_name}
                </span>
              </div>
            ) : (
              <div className="bg-background/40 border border-border/50 p-3 rounded-lg">
                <span className="text-[9px] text-muted-foreground font-mono block uppercase mb-0.5">Product Mode</span>
                <span className="text-xs text-foreground font-semibold block">
                  Study Guide Pack
                </span>
              </div>
            )}
            {jobData.study_file_count !== undefined && jobData.study_file_count > 0 && (
              <div className="bg-background/40 border border-border/50 p-3 rounded-lg">
                <span className="text-[9px] text-muted-foreground font-mono block uppercase mb-0.5">Knowledge Base</span>
                <span className="text-xs text-foreground font-semibold block">
                  {jobData.study_file_count} Study File{jobData.study_file_count > 1 ? "s" : ""}
                </span>
              </div>
            )}
            {jobData.completed_at && (
              <div className="bg-background/40 border border-border/50 p-3 rounded-lg">
                <span className="text-[9px] text-muted-foreground font-mono block uppercase mb-0.5">Completed At</span>
                <span className="text-xs text-foreground font-semibold block">
                  {formatTimestamp(jobData.completed_at)}
                </span>
              </div>
            )}
            {itemsCount > 0 && (
              <div className="bg-background/40 border border-border/50 p-3 rounded-lg">
                <span className="text-[9px] text-muted-foreground font-mono block uppercase mb-0.5">
                  {isStudyMode ? "Total Chapters" : "Total Solved"}
                </span>
                <span className="text-xs text-foreground font-semibold block">
                  {itemsCount} {isStudyMode ? "Sections" : "Questions"}
                </span>
              </div>
            )}
          </div>

          {!isPdfAvailable && (
            <div className="mt-4 flex items-start gap-2.5 p-3 rounded-lg bg-amber-500/10 border border-amber-500/25 text-xs text-amber-600 dark:text-amber-400 font-sans">
              <AlertTriangle className="h-4.5 w-4.5 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold block">PDF Unavailable</span>
                <p className="leading-relaxed mt-0.5">The job completed but the PDF is missing from the output directory. You can preview details in browser below.</p>
              </div>
            </div>
          )}
        </section>

        {/* Content Section Headers */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div className="text-left">
            <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
              <Eye className="h-5 w-5 text-primary" />
              In-Browser Preview
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">Review explanations, cheat sheets, and solved contents.</p>
          </div>

          {!isStudyMode && questions.length > 0 && (
            <button
              onClick={() => toggleExpandAllQuestions(questions.length)}
              className="text-xs text-primary hover:underline transition-colors font-semibold self-start sm:self-auto select-none cursor-pointer"
            >
              {Object.keys(expandedQuestions).length === questions.length ? "Collapse All" : "Expand All"}
            </button>
          )}
        </div>

        {/* Dynamic Layout Rendering */}
        {isStudyMode ? renderStudyPackLayout() : renderAnswerPackLayout()}
      </div>
    </div>
  );
}
