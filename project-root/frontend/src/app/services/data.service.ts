import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { TrialService } from './trial.service';
import { AuthService } from '../auth/auth.service';

@Injectable({ providedIn: 'root' })
export class DataService {
  constructor(private http: HttpClient, private auth: AuthService, private trial: TrialService) {}

  submitData(formData: FormData) {
    if (!this.auth.isLoggedIn()) {
      if (!this.trial.isTrialAvailable()) {
        throw new Error('Trial limit reached. Please sign up or log in.');
      }
      this.trial.incrementUsage();
    }
    return this.http.post('/api/submit', formData);
  }

  getProcessedDetails() {
    return this.http.get('/api/get_processed_details');
  }
}
