import { Component, inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';

export interface FileUploadDialogData {
  title?: string;
  description?: string;
  accept?: string; // ".pdf,.csv,.xlsx"
  multiple?: boolean;
}

@Component({
  selector: 'app-file-upload-dialog',
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule
  ],
  templateUrl: './file-upload-dialog.html',
})
export class FileUploadDialog {
  public dialogRef = inject(MatDialogRef<FileUploadDialog>);
  public data: FileUploadDialogData = inject(MAT_DIALOG_DATA);

  selectedFiles: File[] = [];
  isDragOver = false;

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      this.selectedFiles = Array.from(input.files);
    }
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.isDragOver = false;

    if (event.dataTransfer?.files) {
      this.selectedFiles = Array.from(event.dataTransfer.files);
    }
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.isDragOver = false;
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onUpload(): void {
    this.dialogRef.close(this.selectedFiles);
  }
}
