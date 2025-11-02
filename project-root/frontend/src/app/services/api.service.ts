import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, firstValueFrom } from 'rxjs';
import { getAuth } from 'firebase/auth';
import { TrialService } from './trial.service';

export interface AnalysisResult {
  executiveSummary: string;
  marketAnalysis: {
    marketSize: string;
    growthRate: string;
    competition: string;
    entryBarriers: string;
    regulation: string;
  };
  cohort?: { sector?: string; stage?: string; source?: string };
  risks: Array<{
    factor: string;
    impact: 'low' | 'medium' | 'high';
    description: string;
  }>;
  recommendations: Array<{
    title: string;
    description: string;
  }>;
  extractedMetrics?: {
    arr?: number; mrr?: number; cac?: number; ltv?: number; churnRate?: number;
    growthYoY?: number; growthMoM?: number; headcount?: number; runwayMonths?: number; grossMargin?: number;
    sector?: string; stage?: string;
  };
  benchmarks?: Record<string, {
    companyValue: number; median: number; p25: number; p75: number; percentile: number; status: 'above'|'below';
  }>;
  score?: { composite: number|null; verdict?: string; weights?: Record<string, number>; metricScores?: Record<string, number> };
  llmBenchmark?: {
    cohort?: { sector?: string; stage?: string };
    estimates?: Record<string, { median: number; unit?: string }>;
    relative?: Record<string, 'above'|'near'|'below'>;
    notes?: string;
  };
}

export interface ProcessedDocument {
  id: string;
  status: string;
  summary?: string;
  error?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly apiUrl = this.detectApiBase();
  private readonly http = inject(HttpClient);
  private readonly trial = inject(TrialService);

  constructor() {
    console.log('[ApiService] Backend API URL:', this.apiUrl);
  }

  private detectApiBase(): string {
    // 1) If a meta tag sets API base, use it (lets you point to Render/ngrok without code changes):
    //    <meta name="api-base" content="https://your-backend.example.com">
    if (typeof document !== 'undefined') {
      const meta = document.querySelector('meta[name="api-base"]') as HTMLMetaElement | null;
      const v = meta?.content?.trim();
      if (v) return v;
    }
    // 2) If served from Firebase Hosting with rewrites, use relative /api
    if (typeof window !== 'undefined') {
      const host = window.location.host || '';
      const isProdHosting = host.endsWith('.web.app') || host.endsWith('.firebaseapp.com');
      if (isProdHosting) return '';
    }
    // 3) Local dev: point to Flask
    return 'http://127.0.0.1:5000';
  }

  processDocuments(files: File[], metadata: Record<string, string>): Observable<AnalysisResult> {
    const formData = new FormData();
    
    // Add metadata
    Object.entries(metadata).forEach(([key, value]) => {
      formData.append(key, value);
    });
    
    // Add files
    files.forEach((file, index) => {
      formData.append(`file${index}`, file);
    });

    const headers = new HttpHeaders().set('Accept', 'application/json');
    return this.http.post<AnalysisResult>(
      `${this.apiUrl}/api/process-documents`,
      formData,
      { headers }
    );
  }

  async analyzeDocument(files: File[], isDemo: boolean = false): Promise<AnalysisResult> {
    console.log('[ApiService] analyzeDocument called with', files.length, 'files, isDemo:', isDemo);
    console.log('[ApiService] Uploading to:', `${this.apiUrl}/api/analyze`);

    const formData = new FormData();
    files.forEach((file, index) => {
      console.log('[ApiService] Adding file:', file.name, 'size:', file.size);
      formData.append(`file${index}`, file, file.name);
    });
    formData.append('isDemo', String(isDemo));

    let headers = new HttpHeaders().set('Accept', 'application/json');
    if (isDemo) {
      headers = headers.set('X-Trial', 'true');
    } else {
      const authHeaders = await this.getAuthHeaders();
      headers = authHeaders.headers;
    }

    console.log('[ApiService] Sending HTTP POST request...');
    const response = await firstValueFrom(
      this.http.post<AnalysisResult>(`${this.apiUrl}/api/analyze`, formData, { headers })
    );
    console.log('[ApiService] Received response:', response);
    
    // If this is a demo, mark one trial credit as used
    if (isDemo) {
      // this.trial.useTrialCredit();
    }
    
    return response;
  }

  private async getAuthHeaders(): Promise<{headers: HttpHeaders}> {
    const user = getAuth().currentUser;
    if (!user && !this.trial.isTrialAvailable()) {
      throw new Error('User not logged in and trial limit reached');
    }

    let headers = new HttpHeaders().set('Accept', 'application/json');

    if (user) {
      const token = await user.getIdToken();
      headers = headers.set('Authorization', `Bearer ${token}`);
    }

    return { headers };
  }

  getAnalysisStatus(analysisId: string): Observable<ProcessedDocument> {
    return this.http.get<ProcessedDocument>(
      `${this.apiUrl}/api/analysis-status/${analysisId}`
    );
  }

  async getProcessedDetails(): Promise<ProcessedDocument[]> {
    const { headers } = await this.getAuthHeaders();
    return await firstValueFrom(
      this.http.get<ProcessedDocument[]>(
        `${this.apiUrl}/api/processed-documents`,
        { headers }
      )
    );
  }
}
