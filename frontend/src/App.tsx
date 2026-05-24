import { Navigate, Route, Routes } from "react-router-dom";
import { LandingPage } from "@/pages/LandingPage";
import { ProcessingPage } from "@/pages/ProcessingPage";
import { ResultPage } from "@/pages/ResultPage";
import { UploadPage } from "@/pages/UploadPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/upload" element={<UploadPage />} />
      <Route path="/processing/:jobId" element={<ProcessingPage />} />
      <Route path="/result/:jobId" element={<ResultPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
