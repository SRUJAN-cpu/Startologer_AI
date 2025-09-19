import { Component, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { PitchStepperDialog } from '../../shared/pitch-stepper-dialog/pitch-stepper-dialog/pitch-stepper-dialog';

@Component({
  selector: 'app-hero',
  imports: [],
  templateUrl: './hero.html',
  styles: ``
})
export class Hero {

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
