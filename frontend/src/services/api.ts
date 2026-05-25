import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL
});

export type ProductMode = "STUDY_PACK" | "ANSWER_PACK";

export interface UploadResponse {
  job_id: string;
  message: string;
  status: string;
  mode: ProductMode;
}

// STUDY_PACK schema models
export interface StudyPackSection {
  heading: string;
  summary: string;
  summary_html?: string | null;
  simple_explanation: string;
  simple_explanation_html?: string | null;
  key_points: string[];
  key_points_html?: string[];
  exam_tip?: string | null;
  exam_tip_html?: string | null;
  likely_questions_2_marks: string[];
  likely_questions_2_marks_html?: string[];
  likely_questions_5_marks: string[];
  likely_questions_5_marks_html?: string[];
  likely_questions_10_marks: string[];
  likely_questions_10_marks_html?: string[];
  common_mistakes: string[];
  common_mistakes_html?: string[];
  memory_trick?: string | null;
  memory_trick_html?: string | null;
  revision_cheatsheet: string[];
  revision_cheatsheet_html?: string[];
  embedded_assets: string[];
}

export interface StudyPack {
  title: string;
  sections: StudyPackSection[];
}

// ANSWER_PACK schema models
export interface SolvedQuestion {
  question_number: string;
  question_text: string;
  marks_category?: string | null;
  answer: string;
  answer_html?: string | null;
  simple_explanation: string;
  simple_explanation_html?: string | null;
  quick_revision_points: string[];
  quick_revision_points_html?: string[];
  memory_trick?: string | null;
  memory_trick_html?: string | null;
  related_assets: string[];
}

export interface AnswerPack {
  title: string;
  questions: SolvedQuestion[];
}

export interface JobResponse {
  job_id: string;
  status: string;
  mode: ProductMode;
  file_name: string;
  study_file_names?: string[];
  question_bank_name?: string | null;
  study_file_count?: number;
  created_at: string;
  completed_at?: string | null;
  error_message?: string | null;
  study_pack?: StudyPack | null;
  answer_pack?: AnswerPack | null;
  pdf_url?: string | null;
  filename?: string | null;
  extracted_text_length?: number | null;
  extracted_asset_count?: number | null;
  assets?: string[] | null;
  pdf_file?: string | null;
  ocr_used?: boolean;
}

/**
 * Uploads study files and an optional question bank to the backend
 * @param mode The generation mode: STUDY_PACK or ANSWER_PACK
 * @param studyFiles Array of study notes/materials files
 * @param questionBank The exam question bank file (optional, only for ANSWER_PACK)
 * @param onUploadProgress Callback to track the upload percentage progress
 */
export async function uploadFiles(
  mode: ProductMode,
  studyFiles: File[],
  questionBank?: File | null,
  onUploadProgress?: (progressEvent: any) => void
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("mode", mode);
  studyFiles.forEach((file) => {
    formData.append("study_files", file);
  });
  
  if (mode === "ANSWER_PACK" && questionBank) {
    formData.append("question_bank", questionBank);
  }

  const response = await apiClient.post<UploadResponse>("/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data"
    },
    onUploadProgress
  });
  return response.data;
}

/**
 * Retrieves the current status of a generation job
 * @param jobId The unique ID of the job
 */
export async function getJobStatus(jobId: string): Promise<JobResponse> {
  const response = await apiClient.get<JobResponse>(`/jobs/${jobId}`);
  return response.data;
}
