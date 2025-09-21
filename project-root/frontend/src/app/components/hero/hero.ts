import { Component, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { FileUploadDialog } from '../../shared/file-upload-dialog/file-upload-dialog/file-upload-dialog';

@Component({
  selector: 'app-hero',
  standalone: true,
  imports: [CommonModule, MatButtonModule],
  templateUrl: './hero.html',
  styles: [`:host { display: block; width: 100%; }`]
})
export class Hero {
  private dialog = inject(MatDialog);
  private router = inject(Router);

  async startDemo() {
    const dialogRef = this.dialog.open(FileUploadDialog, {
      width: '600px',
      disableClose: true,
      data: { isDemo: true }
    });

    const result = await dialogRef.afterClosed().toPromise();
    if (result) {
      this.router.navigate(['/result-dashboard'], { 
        state: { analysis: result }
      });
    }
  }
}
