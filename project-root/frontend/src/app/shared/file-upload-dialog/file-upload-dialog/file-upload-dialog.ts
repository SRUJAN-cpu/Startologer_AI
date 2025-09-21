import { Component, inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { ApiService } from '../../../services/api.service';

export interface FileUploadDialogData {
  isDemo?: boolean;
  title?: string;
  description?: string;
  accept?: string; // e.g., ".pdf,.csv,.xlsx"
  multiple?: boolean;
}

@Component({
  selector: 'app-file-upload-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatProgressBarModule
  ],
  templateUrl: './file-upload-dialog.html',
})
export class FileUploadDialog {
  private apiService = inject(ApiService);
  dialogRef = inject(MatDialogRef<FileUploadDialog>);
  data = inject(MAT_DIALOG_DATA) as FileUploadDialogData;

  selectedFiles: File[] = [];
  isDragOver = false;
  isLoading = false;
  error: string | null = null;
  acceptedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
  maxFiles = 5;

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      this.addFiles(Array.from(input.files));
    }
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.isDragOver = true;
  }

  onDragLeave() {
    this.isDragOver = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.isDragOver = false;
    if (event.dataTransfer?.files) {
      this.addFiles(Array.from(event.dataTransfer.files));
    }
  }

  addFiles(files: File[]) {
    this.error = null;
    const remainingSlots = this.maxFiles - this.selectedFiles.length;

    if (files.length > remainingSlots) {
      this.error = `You can only upload up to ${this.maxFiles} files in total.`;
      files = files.slice(0, remainingSlots);
    }

    const validFiles = files.filter(file => {
      if (this.acceptedTypes.includes(file.type)) {
        return true;
      } else {
        this.error = `Invalid file type: ${file.name}. Only PDF, Word, and TXT are allowed.`;
        return false;
      }
    });

    if (this.selectedFiles.length + validFiles.length > this.maxFiles) {
        this.error = `You can only upload up to ${this.maxFiles} files.`;
        return;
    }

    this.selectedFiles.push(...validFiles);
  }

  removeFile(index: number) {
    if (index > -1) {
      this.selectedFiles.splice(index, 1);
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  async onUpload(): Promise<void> {
    if (this.selectedFiles.length === 0) {
      return;
    }

    this.isLoading = true;
    this.error = null;

    try {
      const isDemo = !!this.data?.isDemo;
      const result = await this.apiService.analyzeDocument(this.selectedFiles, isDemo);
      this.dialogRef.close(result);
    } catch (err: any) {
      const status = err?.status;
      const message = err?.error?.error || err?.message || 'Unknown error';
      this.error = `Analyze failed${status ? ` (HTTP ${status})` : ''}: ${message}`;
      console.error('Analyze error:', err);
    } finally {
      this.isLoading = false;
    }
  }
}
