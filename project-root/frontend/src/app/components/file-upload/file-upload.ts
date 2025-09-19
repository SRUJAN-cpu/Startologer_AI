import { Component, Inject, inject } from '@angular/core';

@Component({
  selector: 'app-file-upload',
  imports: [],
  templateUrl: './file-upload.html',
  styles: ``
})
export class FileUpload {
  selectedFile?: File;

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length) {
      this.selectedFile = input.files[0];
      console.log('Selected file:', this.selectedFile.name);
    }
  }

  onUpload() {
    if (this.selectedFile) {
      alert(`Uploading: ${this.selectedFile.name}`);
      // integrate upload logic
    }
  }
}
