import { Component, EventEmitter, inject, Output } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { ApiService } from '../../../services/api.service';

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
   selectedFiles: File[] = [];
  isDragOver = false;

  @Output() filesSelected = new EventEmitter<File[]>();

  onFileSelected(event: any) {
    const files = Array.from(event.target.files) as File[];
    this.selectedFiles = files;
    this.filesSelected.emit(this.selectedFiles);
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    if (event.dataTransfer?.files) {
      this.selectedFiles = Array.from(event.dataTransfer.files);
      this.filesSelected.emit(this.selectedFiles);
    }
    this.isDragOver = false;
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent) {
    this.isDragOver = false;
  }
}
