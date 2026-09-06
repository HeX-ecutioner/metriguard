# MetriGuard SIH26034 Demonstration Guide

## 1. Demonstration Objective
This guide provides a step-by-step presentation script and operational playbook for team members demonstrating **MetriGuard** to SIH26034 hackathon judges.

## 2. Mandatory Prototype & Non-Legal Authority Disclaimer
> [!IMPORTANT]
> **Always state this disclaimer clearly at the start of your presentation:**
> *"MetriGuard is an AI-assisted decision-support prototype designed for hackathon demonstration by team AlgoForge. It automates packaging declaration extraction and evaluates compliance against versioned rules under the Legal Metrology (Packaged Commodities) Rules, 2011. It is not a legally certified compliance authority. All outputs are designed to assist human inspectors who perform final verification."*

## 3. What the System Does vs. What It Does Not Claim to Do

### What System Does:
- Accepts package label images (JPG, PNG, WEBP $\le$ 10MB).
- Extracts text, bounding box coordinates, and confidence scores via OCR.
- Parses mandatory declarations (MRP, Net Qty, Dates, Entity details, Consumer Care, USP) using deterministic regex patterns.
- Evaluates compliance against 6 codified LMR 2011 rules.
- Highlights bounding box evidence overlays on package images.
- Routes missing or low-confidence extractions safely to `MANUAL_REVIEW`.
- Provides an inspector declaration editor and status override interface (`PATCH /api/v1/inspections/{id}/status`).
- Tracks historical inspections and summary analytics on a dashboard.

### What System Does NOT Claim to Do:
- Issue legally binding court summonses or penalties.
- Measure physical font height in millimeters (uncalibrated 2D photos lack physical scale).
- Support multi-image combined sessions (strictly 1 package image per inspection).
- Claim 100% OCR accuracy on blurry, reflective, or stylized typography.

## 4. Demo Prerequisites
- **Operating System:** Windows 10/11 x64 or Linux.
- **Runtime:** Python 3.10+ and Node.js v18+.
- **Pre-demonstration Preparation Checklist for Test Images:**
  - [ ] **Sample A (Compliant Case):** High-resolution photo of a standard retail package label where all 6 mandatory declarations are clearly visible in English (MRP, Net Qty, Mfg Date, Entity, Consumer Care, USP).
  - [ ] **Sample B (Non-Compliant Case):** Photo of a package label missing a mandatory declaration (e.g. missing MRP or missing Consumer Care contact).
  - [ ] **Sample C (Manual Review Case):** Photo taken at an angle, with minor reflection, or partial blur that triggers low extraction confidence (< 0.70).
  - [ ] **Sample D (Invalid File Case):** A non-image text file or corrupt file to demonstrate error handling.

## 5. How to Start the Application

1. **Open PowerShell from workspace root:**
   ```ps
   .\start.ps1
   ```
2. **Verify Backend Availability:**
   Open browser to `http://127.0.0.1:8000/health` (should return `{"status": "ok"}`).
3. **Open Frontend Interface:**
   Open browser to `http://localhost:5173`.

## 6. Recommended 5-Minute Demo Sequence

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Introduction & Disclaimer (30s)                                      │
│    - Problem Statement SIH26034 introduction                            │
│    - Explainable AI & Human-in-the-Loop philosophy                      │
├─────────────────────────────────────────────────────────────────────────┤
│ 2. Compliant Package Walkthrough (90s)                                  │
│    - Drag-and-drop Sample A image                                       │
│    - Show real-time extraction progress bar                             │
│    - Highlight interactive bounding boxes & 6 LMR 2011 rule findings    │
├─────────────────────────────────────────────────────────────────────────┤
│ 3. Non-Compliant & Manual Review Cases (90s)                            │
│    - Click "Upload another image" (demonstrate state reset)             │
│    - Upload Sample B / Sample C                                         │
│    - Show missing declaration detection and MANUAL_REVIEW status        │
│    - Demonstrate inspector status override control                      │
├─────────────────────────────────────────────────────────────────────────┤
│ 4. Dashboard Analytics & History (60s)                                  │
│    - Switch to Dashboard tab                                            │
│    - Show real-time summary cards, top violation meters, and search     │
├─────────────────────────────────────────────────────────────────────────┤
│ 5. Conclusion & Q&A (30s)                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## 7. Step-by-Step Feature Demonstrations

### 7.1 Demonstrating a Compliant Case
1. Drag and drop **Sample A** into the dropzone on the Upload screen.
2. Click **Start Inspection**.
3. Point out the processing progress states (Validation -> Storage -> OCR -> Extraction -> Rule Evaluation).
4. Review the completed report: badge displays `COMPLIANT`, overall confidence score is high, and 6 rule checks display `PASSED`.

### 7.2 Demonstrating Evidence Bounding Boxes
1. On the inspection results view, click an extracted declaration field (e.g. `Maximum Retail Price`).
2. Show judges how the system highlights the corresponding bounding box `[x_min, y_min, x_max, y_max]` overlay on the package image.
3. Explain: *"Every compliance finding is backed by verifiable optical evidence, preventing black-box AI decisions."*

### 7.3 Demonstrating MANUAL_REVIEW & Inspector Override
1. Upload **Sample C** (blurry/ambiguous label).
2. Show judges that the system assigns `MANUAL_REVIEW` due to low confidence or missing evidence.
3. Click **Verify & Edit Declarations** to show the manual review editor.
4. Manually fill in the missing declaration value, select **Update Status**, and save the record.
5. Explain: *"The system never guesses missing evidence. Low-confidence extractions safely route to human inspectors for verification."*

### 7.4 Demonstrating Starting a New Inspection (Lifecycle Reset)
1. From the results screen, click **Upload another image**.
2. Show judges that all previous results, bounding boxes, and image previews are cleared, and the active session ID resets to `null`.
3. Explain: *"Each inspection session is strictly 1:1 with a single package image, preventing cross-session result desynchronization."*

### 7.5 Demonstrating Error Handling
1. Drag an invalid non-image file into the dropzone.
2. Show that the backend returns HTTP 400 Bad Request and displays a clear error alert without crashing.

## 8. What to Say When OCR Fails or Is Ambiguous
- **Say:** *"Notice how the system detected low OCR confidence on this packaging font. Instead of hallucinating a false pass or fail, AlgoForge automatically routed the inspection to MANUAL_REVIEW. This safeguards against false enforcement notices."*

## 9. What NOT to Claim to Judges
- **DO NOT claim:** *"Our system is 100% accurate and can replace human inspectors."*
- **DO NOT claim:** *"Our AI measures physical font height in millimeters."*
- **DO NOT claim:** *"This system is legally certified and ready for court summonses."*
- **DO NOT claim:** *"We support multi-image scans in one session."*

## 10. Backup Plan If Demo Environment Fails
If local dev servers fail or network binding errors occur:
1. Open PowerShell and run live smoke test:
   ```powershell
   backend\.venv\Scripts\python backend\smoke_test.py
   ```
2. Or run the environment verification script to prove setup integrity:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\verify_setup.ps1
   ```
3. Show static production build in `frontend/dist/` or present pre-recorded inspection runs in the Dashboard history table.

## 11. Final Presentation Checklist
- [ ] Laptop charger and mouse ready.
- [ ] Backend running (`http://127.0.0.1:8000/health` verified).
- [ ] Frontend running (`http://localhost:5173` open).
- [ ] 4 prepared sample packaging images (Compliant, Non-Compliant, Manual Review, Invalid) saved in a dedicated demo folder.
- [ ] Browser zoom level set to 100%.