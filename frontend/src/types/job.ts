export type JobStatus =
  | "uploaded"
  | "extracting"
  | "ocr_processing"
  | "ai_processing"
  | "pdf_generating"
  | "completed"
  | "failed";

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  file_name: string;
  created_at: string;
  completed_at?: string | null;
  error_message?: string | null;
  pdf_url?: string | null;
}
