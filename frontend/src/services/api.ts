import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL
});

export interface UploadResponse {
  job_id: string;
  message: string;
  status: string;
}

export interface SolvedQuestion {
  question_number: string;
  question_text: string;
  ideal_answer: string;
  simple_explanation: string;
  revision_points: string[];
  memory_trick?: string | null;
  likely_marks?: string | null;
  embedded_assets: string[];
}

export interface AnswerPack {
  title: string;
  questions: SolvedQuestion[];
}

export interface JobResponse {
  job_id: string;
  status: string;
  file_name: string;
  study_file_names?: string[];
  question_bank_name?: string | null;
  study_file_count?: number;
  created_at: string;
  completed_at?: string | null;
  error_message?: string | null;
  study_pack?: AnswerPack | null;
  pdf_url?: string | null;
  filename?: string | null;
  extracted_text_length?: number | null;
  extracted_asset_count?: number | null;
  assets?: string[] | null;
  pdf_file?: string | null;
  ocr_used?: boolean;
}

/**
 * Uploads study files and a question bank to the backend
 * @param studyFiles Array of study notes/materials files
 * @param questionBank The exam question bank file
 * @param onUploadProgress Callback to track the upload percentage progress
 */
export async function uploadFiles(
  studyFiles: File[],
  questionBank: File,
  onUploadProgress?: (progressEvent: any) => void
): Promise<UploadResponse> {
  const formData = new FormData();
  studyFiles.forEach((file) => {
    formData.append("study_files", file);
  });
  formData.append("question_bank", questionBank);

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
