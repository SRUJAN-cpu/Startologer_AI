import { Component, inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { ApiService } from '../../../services/api.service';
import { PDFDocument } from 'pdf-lib';

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
  loadingMessage: string = '';
  error: string | null = null;
  acceptedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
  maxFiles = 5;
  maxFileSizeMB = 30; // Max file size per file (warn users early, backend will auto-compress PDFs >10MB)
  maxTotalSizeMB = 30; // Max total upload size to match Cloud Run 32MB limit with buffer

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
      // Check file type
      if (!this.acceptedTypes.includes(file.type)) {
        this.error = `Invalid file type: ${file.name}. Only PDF, Word, and TXT are allowed.`;
        return false;
      }

      // Check individual file size
      const fileSizeMB = file.size / (1024 * 1024);
      if (fileSizeMB > this.maxFileSizeMB) {
        this.error = `File "${file.name}" is too large (${fileSizeMB.toFixed(1)}MB). Maximum file size is ${this.maxFileSizeMB}MB. Note: PDFs >10MB are automatically compressed server-side.`;
        return false;
      }

      return true;
    });

    // Don't validate total size here - backend will compress large PDFs
    // Just check we don't exceed max file count
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

  /**
   * Compress a PDF file in the browser to reduce size
   * Uses pdf-lib to re-encode the PDF with optimizations
   */
  private async compressPdfInBrowser(file: File): Promise<File> {
    try {
      console.log(`[Compression] Starting compression for ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)}MB)`);

      // Read the PDF file
      const arrayBuffer = await file.arrayBuffer();

      // Load the PDF document
      const pdfDoc = await PDFDocument.load(arrayBuffer, {
        ignoreEncryption: true,
        updateMetadata: false
      });

      // Save with compression options
      const compressedPdfBytes = await pdfDoc.save({
        useObjectStreams: false, // Disable object streams for better compression
        addDefaultPage: false,
        objectsPerTick: 50
      });

      // Create a new File object with compressed content
      // Create Blob from the PDF bytes (cast to any to satisfy strict TypeScript)
      const compressedFile = new File(
        [new Blob([compressedPdfBytes as any])],
        file.name,
        { type: 'application/pdf' }
      );

      const originalSizeMB = file.size / (1024 * 1024);
      const compressedSizeMB = compressedFile.size / (1024 * 1024);
      const savings = ((originalSizeMB - compressedSizeMB) / originalSizeMB) * 100;

      console.log(`[Compression] Success: ${originalSizeMB.toFixed(1)}MB → ${compressedSizeMB.toFixed(1)}MB (saved ${savings.toFixed(1)}%)`);

      return compressedFile;
    } catch (error) {
      console.error(`[Compression] Failed for ${file.name}:`, error);
      // Return original file if compression fails
      return file;
    }
  }

  async onUpload(): Promise<void> {
    if (this.selectedFiles.length === 0) {
      return;
    }

    this.isLoading = true;
    this.error = null;
    this.loadingMessage = 'Preparing files...';

    try {
      const isDemo = !!this.data?.isDemo;

      // Compress large PDFs BEFORE uploading (client-side)
      const filesToUpload: File[] = [];

      for (let i = 0; i < this.selectedFiles.length; i++) {
        const file = this.selectedFiles[i];
        const fileSizeMB = file.size / (1024 * 1024);

        // Compress PDFs larger than 10MB
        if (file.type === 'application/pdf' && fileSizeMB > 10) {
          this.loadingMessage = `Compressing ${file.name} (${fileSizeMB.toFixed(1)}MB)... Please wait.`;
          console.log(`[Upload] Compressing PDF ${i + 1}/${this.selectedFiles.length}: ${file.name}`);

          const compressedFile = await this.compressPdfInBrowser(file);
          const compressedSizeMB = compressedFile.size / (1024 * 1024);

          // Check if still too large after compression
          if (compressedSizeMB > 30) {
            this.error = `File "${file.name}" is ${compressedSizeMB.toFixed(1)}MB even after compression. Cloud Run has a 32MB limit. Please:
1. Use https://www.ilovepdf.com/compress_pdf to compress further
2. Split the PDF into smaller files
3. Contact support for enterprise options`;
            this.isLoading = false;
            return;
          }

          filesToUpload.push(compressedFile);
        } else {
          filesToUpload.push(file);
        }
      }

      // Final size check
      const totalSizeMB = filesToUpload.reduce((sum, f) => sum + f.size, 0) / (1024 * 1024);
      if (totalSizeMB > 30) {
        this.error = `Total upload size is ${totalSizeMB.toFixed(1)}MB. Maximum is 30MB. Please remove some files or compress them further.`;
        this.isLoading = false;
        return;
      }

      this.loadingMessage = 'Uploading and analyzing...';
      const result = await this.apiService.analyzeDocument(filesToUpload, isDemo);

      console.log('[FileUploadDialog] API returned result:', result);
      console.log('[FileUploadDialog] Has benchmarks?', !!result.benchmarks, Object.keys(result.benchmarks || {}).length);
      console.log('[FileUploadDialog] Has llmBenchmark?', !!result.llmBenchmark);
      console.log('[FileUploadDialog] llmBenchmark estimates?', result.llmBenchmark?.estimates);
      this.dialogRef.close(result);
    } catch (err: any) {
      const status = err?.status;
      let message = err?.error?.error || err?.message || 'Unknown error';

      // Provide user-friendly error messages
      if (status === 413) {
        // Check if error message already has helpful details from backend
        if (err?.error?.details) {
          message = err.error.details;
        } else {
          message = `File too large (30MB limit). Our server automatically compresses PDFs >10MB, but your file exceeded the 32MB Cloud Run limit even after compression.

Solutions:
1. Pre-compress your PDF at https://www.ilovepdf.com/compress_pdf (free)
2. Split large PDFs into smaller files
3. Contact support for enterprise upload options`;
        }
      } else if (status === 0) {
        message = 'Network error. Please check your internet connection and try again.';
      }

      this.error = `Analyze failed${status ? ` (HTTP ${status})` : ''}: ${message}`;
      console.error('Analyze error:', err);
    } finally {
      this.isLoading = false;
      this.loadingMessage = '';
    }
  }
}
