/**
 * Centralized API Client for MetriGuard
 * Reads configuration from environment variables without Docker hostnames.
 */

export interface RuleViolation {
  rule_id: string;
  explanation: string;
  confidence: number;
}

export interface PackageImage {
  id: number;
  inspection_id: number;
  file_path: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  width: number | null;
  height: number | null;
  created_at: string;
  status?: string | null;
  confidence_score?: number | null;
  extracted_texts?: string[] | null;
  violations?: RuleViolation[] | null;
  image_url?: string | null;
}

export interface DeclarationItem {
  id: number;
  declaration_type: string;
  extracted_value: string;
  confidence?: number | null;
  bounding_box?: string | null;
}

export interface ViolationItem {
  id: number;
  rule_id: string;
  rule_version: string;
  title: string;
  explanation: string;
  severity: string;
  confidence?: number | null;
  evidence_image_id?: number | null;
  evidence_bounding_box?: string | null;
  measured_value?: string | null;
  expected_value?: string | null;
}

export interface InspectionResultItem {
  final_status: string;
  summary: string;
}

export interface Inspection {
  id: number;
  status: string;
  product_name: string | null;
  overall_confidence: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  images: PackageImage[];
  declarations?: DeclarationItem[];
  violations?: ViolationItem[];
  result?: InspectionResultItem | null;
}

export interface ApiError {
  detail: string;
  error_code?: string;
  status_code: number;
}

class ApiClient {
  private baseUrl: string;

  constructor() {
    // Read from Vite environment or default to local proxy/localhost
    const envUrl = import.meta.env.VITE_API_URL;
    if (envUrl) {
      this.baseUrl = envUrl.replace(/\/$/, '');
    } else {
      // In development Vite proxies /api to http://127.0.0.1:8000
      this.baseUrl = '';
    }
  }

  private getUrl(endpoint: string): string {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    return `${this.baseUrl}${cleanEndpoint}`;
  }

  /**
   * Creates a new inspection session.
   */
  async createInspection(data?: { product_name?: string; notes?: string }): Promise<Inspection> {
    const url = this.getUrl('/api/v1/inspections');
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data || {}),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => null);
      throw {
        detail: err?.detail || `Failed to create inspection (HTTP ${response.status})`,
        error_code: err?.error_code,
        status_code: response.status,
      } as ApiError;
    }

    return response.json();
  }

  /**
   * Uploads an image to an existing inspection with real upload progress tracking.
   */
  uploadInspectionImage(
    inspectionId: number,
    file: File,
    onProgress?: (percentage: number) => void
  ): Promise<PackageImage> {
    return new Promise((resolve, reject) => {
      const url = this.getUrl(`/api/v1/inspections/${inspectionId}/images`);
      const formData = new FormData();
      formData.append('file', file);

      const xhr = new XMLHttpRequest();
      xhr.open('POST', url);

      if (xhr.upload && onProgress) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            onProgress(percent);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data: PackageImage = JSON.parse(xhr.responseText);
            resolve(data);
          } catch {
            reject({
              detail: 'Invalid response from server.',
              status_code: xhr.status,
            } as ApiError);
          }
        } else {
          try {
            const errData = JSON.parse(xhr.responseText);
            reject({
              detail: errData?.detail || `Upload failed with status ${xhr.status}`,
              error_code: errData?.error_code,
              status_code: xhr.status,
            } as ApiError);
          } catch {
            reject({
              detail: xhr.statusText || `Upload failed with status ${xhr.status}`,
              status_code: xhr.status,
            } as ApiError);
          }
        }
      };

      xhr.onerror = () => {
        reject({
          detail: 'Network error occurred during image upload.',
          status_code: 0,
        } as ApiError);
      };

      xhr.send(formData);
    });
  }

  /**
   * Retrieves inspection details and its attached images.
   */
  async getInspection(inspectionId: number): Promise<Inspection> {
    const url = this.getUrl(`/api/v1/inspections/${inspectionId}`);
    const response = await fetch(url);

    if (!response.ok) {
      const err = await response.json().catch(() => null);
      throw {
        detail: err?.detail || `Inspection not found (HTTP ${response.status})`,
        error_code: err?.error_code,
        status_code: response.status,
      } as ApiError;
    }

    return response.json();
  }

  /**
   * Returns direct URL to download/view the original uploaded package image.
   */
  getImageFileUrl(inspectionId: number, imageId: number): string {
    return this.getUrl(`/api/v1/inspections/${inspectionId}/images/${imageId}/file`);
  }
}

export const apiClient = new ApiClient();
