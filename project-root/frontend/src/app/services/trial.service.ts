import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class TrialService {
  private maxTrials = 3;
  private trialKey = 'trial_usage';

  getUsage(): number {
    return parseInt(localStorage.getItem(this.trialKey) || '0', 10);
  }

  incrementUsage(): void {
    let current = this.getUsage();
    localStorage.setItem(this.trialKey, (current + 1).toString());
  }

  isTrialAvailable(): boolean {
    return this.getUsage() < this.maxTrials;
  }

  reset(): void {
    localStorage.removeItem(this.trialKey);
  }
}
