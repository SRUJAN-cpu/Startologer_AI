import { Component, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { FileUploadDialog, FileUploadDialogData } from '../../shared/file-upload-dialog/file-upload-dialog/file-upload-dialog';

@Component({
  selector: 'app-navbar',
  imports: [],
  templateUrl: './navbar.html',
})
export class Navbar {

  private dialog = inject(MatDialog);

  openFileUploadDialog() {
    const dialogRef = this.dialog.open<FileUploadDialog, FileUploadDialogData, File[]>(
      FileUploadDialog,
      {
        width: '800px',
        data: {
          title: 'Upload Startup Data',
          description: 'Upload pitch decks, financials, or CSV files.',
          accept: '.pdf,.csv,.xlsx',
          multiple: true,
        },
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
