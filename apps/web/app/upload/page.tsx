import { UploadForm } from "./upload-form";

export default function UploadPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  return (
    <main>
      <p className="kicker">Placeholder</p>
      <h1>Upload</h1>
      <p className="lede">
        Queue a detection ticket against the FastAPI stub at {apiUrl}.
      </p>
      <UploadForm apiUrl={apiUrl} />
    </main>
  );
}
