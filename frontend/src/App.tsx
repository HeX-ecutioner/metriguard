import { useState } from 'react';
import ImageUpload from './components/ImageUpload';
import ResultsView from './components/ResultsView';
import DashboardView from './components/DashboardView';
import InspectionDetailView from './components/InspectionDetailView';
import type { PackageImage, Inspection } from './api/client';

type ViewMode = 'dashboard' | 'detail' | 'new_inspection';

function App() {
  const [currentView, setCurrentView] = useState<ViewMode>('dashboard');
  const [selectedInspectionId, setSelectedInspectionId] = useState<number | null>(null);
  const [activeInspection, setActiveInspection] = useState<Inspection | null>(null);
  const [uploadSessionKey, setUploadSessionKey] = useState<number>(0);

  const handleUploadSuccess = (_image: PackageImage, inspection: Inspection) => {
    setActiveInspection(inspection);
  };

  const handleInspectionCreated = (inspection: Inspection) => {
    setActiveInspection(inspection);
  };

  const handleUploadAnotherImage = () => {
    // Reset active inspection state completely so new upload gets a brand-new ID and clean UI
    setActiveInspection(null);
    setUploadSessionKey((prev) => prev + 1);
  };

  const handleOpenDetail = (id: number) => {
    setSelectedInspectionId(id);
    setCurrentView('detail');
  };

  const handleStartNewInspection = () => {
    setActiveInspection(null);
    setUploadSessionKey((prev) => prev + 1);
    setCurrentView('new_inspection');
  };

  return (
    <div className="container">
      <header className="header" style={{ marginBottom: '1.5rem', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', marginBottom: '0.25rem' }}>
          <img src="/logo.png" alt="MetriGuard Logo" style={{ width: 44, height: 44, borderRadius: 10, objectFit: 'contain' }} />
          <h1 style={{ margin: 0 }}>MetriGuard</h1>
        </div>
        <p>AI-Assisted Legal Metrology Compliance Inspection Platform</p>
      </header>

      {/* Navigation Bar */}
      <nav className="nav-bar" data-testid="app-navigation">
        <div className="nav-tabs">
          <button
            className={`nav-tab ${currentView === 'dashboard' ? 'active' : ''}`}
            onClick={() => setCurrentView('dashboard')}
            data-testid="tab-dashboard"
          >
            📊 Dashboard
          </button>
          <button
            className={`nav-tab ${currentView === 'new_inspection' ? 'active' : ''}`}
            onClick={handleStartNewInspection}
            data-testid="tab-new-inspection"
          >
            ⚡ New Inspection
          </button>
          {currentView === 'detail' && selectedInspectionId && (
            <button
              className="nav-tab active"
              data-testid="tab-inspection-detail"
            >
              📋 Inspection #{selectedInspectionId}
            </button>
          )}
        </div>

        {currentView !== 'new_inspection' && (
          <button
            className="btn"
            style={{ padding: '0.45rem 1rem', fontSize: '0.85rem' }}
            onClick={handleStartNewInspection}
          >
            + Inspect Package
          </button>
        )}
      </nav>

      {/* Main View Router */}
      <main>
        {currentView === 'dashboard' && (
          <DashboardView
            onSelectInspection={handleOpenDetail}
            onNewInspection={handleStartNewInspection}
          />
        )}

        {currentView === 'detail' && selectedInspectionId && (
          <InspectionDetailView
            inspectionId={selectedInspectionId}
            onBack={() => setCurrentView('dashboard')}
          />
        )}

        {currentView === 'new_inspection' && (
          <div className="app-grid fade-in">
            <section className="upload-column" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <ImageUpload
                key={uploadSessionKey}
                onUploadSuccess={handleUploadSuccess}
                onInspectionCreated={handleInspectionCreated}
                onUploadAnotherImage={handleUploadAnotherImage}
              />
            </section>

            <section className="results-column">
              {activeInspection && (activeInspection.result || (activeInspection.images && activeInspection.images.length > 0)) ? (
                <ResultsView
                  inspection={activeInspection}
                  onUploadAnotherImage={handleUploadAnotherImage}
                />
              ) : (
                <div
                  className="glass-card"
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100%',
                    minHeight: '320px',
                    textAlign: 'center',
                    color: 'var(--text-muted)',
                    padding: '2.5rem 1.5rem',
                  }}
                >
                  <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.7 }}>📋</div>
                  <h3 style={{ marginBottom: '0.5rem', color: 'var(--text-main)' }}>Inspection Report</h3>
                  <p style={{ maxWidth: '360px', fontSize: '0.9rem', lineHeight: '1.5' }}>
                    Select an image and click "Start Inspection" to trigger automated OCR extraction and Legal Metrology (2011) compliance verification.
                  </p>
                </div>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
