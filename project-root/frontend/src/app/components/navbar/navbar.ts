import { Component, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { FileUploadDialog, FileUploadDialogData } from '../../shared/file-upload-dialog/file-upload-dialog/file-upload-dialog';
import { PitchStepperDialog } from '../../shared/pitch-stepper-dialog/pitch-stepper-dialog/pitch-stepper-dialog';

@Component({
  selector: 'app-navbar',
  imports: [],
  templateUrl: './navbar.html',
})
export class Navbar {

  private dialog = inject(MatDialog);

  openFileUploadDialog() {
      const dialogRef = this.dialog.open<PitchStepperDialog>(
        PitchStepperDialog,
        {
          width: '800px',
          disableClose: true
        }
      );
  
      dialogRef.afterClosed().subscribe((files) => {
        if (files && files.length > 0) {
          console.log('Selected files:', files);
          // TODO: send files to backend
        }
      });
    }
}
