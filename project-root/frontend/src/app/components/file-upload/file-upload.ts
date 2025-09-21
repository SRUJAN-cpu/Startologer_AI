import { Component, EventEmitter, Output } from '@angular/core';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-file-upload',
  templateUrl: './file-upload.html',
  styles: [`
    :host {
      display: block;
      width: 100%;
    }
  `]
})
export class FileUpload {
  @Output() filesSelected = new EventEmitter<File[]>();

  selectedFile: File | null = null;
  selectedFiles: File[] = [];
  maxFiles = 5;
  acceptedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
  errorMessage = '';
  loading = false;

  constructor(private apiService: ApiService) {}

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length) {
      if (this.selectedFiles.length + input.files.length > this.maxFiles) {
        this.errorMessage = `Maximum ${this.maxFiles} files allowed`;
        return;
      }

      Array.from(input.files).forEach(file => {
        if (this.acceptedTypes.includes(file.type)) {
          this.selectedFiles.push(file);
        } else {
          this.errorMessage = 'Only PDF and Word documents are allowed';
        }
      });

      // Emit selected files
      this.filesSelected.emit(this.selectedFiles);
    }
  }

  removeFile(index: number) {
    this.selectedFiles.splice(index, 1);
    this.filesSelected.emit(this.selectedFiles);
    this.errorMessage = '';
  }

  clearFiles() {
    this.selectedFiles = [];
    this.selectedFile = null;
    this.filesSelected.emit(this.selectedFiles);
    this.errorMessage = '';
  }

  async onUpload() {
    if (!this.selectedFile) return;

    this.loading = true;
    this.errorMessage = '';

    try {
      // const result = await this.apiService.analyzeDocument(this.selectedFile, true);
      this.loading = false;
      // Emit the result if needed
      this.filesSelected.emit([this.selectedFile]);
    } catch (err: any) {
      this.errorMessage = err.message || 'Failed to analyze document';
      this.loading = false;
    }
  }
}
