import { useState, useCallback } from 'react';
import ImageUpload from './components/ImageUpload';
import ResultsView from './components/ResultsView';

export interface Violation {
  rule_id: string;
  explanation: string;
  confidence: number;
}

export interface InspectionResult {
  status: 'COMPLIANT' | 'NON_COMPLIANT' | 'MANUAL_REVIEW';
  violations: Violation[];
  extracted_texts: string[];
  confidence_score: number;
}

function App() {
  const [result, setResult] = useState<InspectionResult | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = useCallback(async (file: File) => {
    setIsProcessing(true);
    setError(null);
    setResult(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const apiBase = import.meta.env.VITE_API_URL || '';
      const apiUrl = apiBase ? `${apiBase.replace(/\/$/, '')}/api/v1/inspect` : '/api/v1/inspect';
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Inspection failed (HTTP ${response.status})`);
      }
      
      const data: InspectionResult = await response.json();
      setResult(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred during inspection.');
      }
    } finally {
      setIsProcessing(false);
    }
  }, []);

  return (
    <div className="container">
      <header className="header">
        <h1>MetriGuard</h1>
        <p>AI-Assisted Legal Metrology Compliance Inspection Platform</p>
      </header>
      
      <main className="app-grid fade-in">
        <section className="upload-section">
          <ImageUpload onUpload={handleUpload} isProcessing={isProcessing} />
          {error && (
            <div className="glass-card" style={{ marginTop: '1rem', borderColor: 'var(--error-color)' }}>
              <p style={{ color: 'var(--error-color)' }}>{error}</p>
            </div>
          )}
        </section>
        
        <section className="results-section">
          {result && <ResultsView result={result} />}
        </section>
      </main>
    </div>
  );
}

export default App;
