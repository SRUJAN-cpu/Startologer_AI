import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import { FileUploadDialog } from '../../shared/file-upload-dialog/file-upload-dialog/file-upload-dialog';
import { MatDialog } from '@angular/material/dialog';

@Component({
  selector: 'app-feature-card',
  imports: [],
  templateUrl: './feature-card.html',
  styles: `
    .feature-card {
      cursor: pointer;
    }
  `
})
export class FeatureCard {
  private router = inject(Router);
  private auth = inject(AuthService);
  private dialog = inject(MatDialog);

  handleNavigation() {
    if (this.auth.isLoggedIn()) {
      const dialogRef = this.dialog.open(FileUploadDialog, {
            width: '600px',
            disableClose: true,
            data: { isDemo: true }
          });
      
          const result = dialogRef.afterClosed();
          if (result) {
            this.router.navigate(['/result-dashboard'], { 
              state: { analysis: result }
            });
          }
    } else {
      // User is NOT logged in - redirect to signup
      this.router.navigate(['/signup']);
    }
  }
}
