// import { Component, inject, OnInit } from '@angular/core';
// import { FormBuilder, FormGroup, Validators } from '@angular/forms';
// import { MatDialogRef } from '@angular/material/dialog';
// import { CommonModule } from '@angular/common';
// import { ReactiveFormsModule } from '@angular/forms';
// import { MatDialogModule } from '@angular/material/dialog';
// import { MatStepperModule } from '@angular/material/stepper';
// import { MatFormFieldModule } from '@angular/material/form-field';
// import { MatInputModule } from '@angular/material/input';
// import { FileUploadDialog } from '../../file-upload-dialog/file-upload-dialog/file-upload-dialog';
// import { MatButtonModule } from '@angular/material/button';
// import { ApiService } from '../../../services/api.service';
// import { Router } from '@angular/router';

// @Component({
//   selector: 'app-pitch-stepper-dialog',
//   standalone: true,
//   imports: [
//     CommonModule,
//     ReactiveFormsModule,
//     MatDialogModule,
//     MatStepperModule,
//     MatFormFieldModule,
//     MatInputModule,
//     FileUploadDialog,
//     MatButtonModule,
//   ],
//   templateUrl: './pitch-stepper-dialog.html',
// })
// export class PitchStepperDialog implements OnInit {
//   private formBuilder = inject(FormBuilder);
//   private apiService = inject(ApiService);
//   private router = inject(Router);
//   dialogRef = inject(MatDialogRef<PitchStepperDialog>);

//   pitchDeckForm!: FormGroup;
//   callTranscriptForm!: FormGroup;
//   founderUpdateForm!: FormGroup;
//   emailDataForm!: FormGroup;

//   loading = false;
//   error: string | null = null;

//   ngOnInit(): void {
//     this.pitchDeckForm = this.formBuilder.group({
//       pitchDeck: [null, Validators.required]
//     });
//     this.callTranscriptForm = this.formBuilder.group({
//       callTranscript: ['', Validators.required]
//     });
//     this.founderUpdateForm = this.formBuilder.group({
//       founderUpdate: ['']
//     });
//     this.emailDataForm = this.formBuilder.group({
//       emailData: ['']
//     });
//   }

//   onPitchFilesSelected(files: File[]) {
//     this.pitchDeckForm.patchValue({ pitchDeck: files });
//   }

//   async onSubmit() {
//     if (
//       this.pitchDeckForm.valid &&
//       this.callTranscriptForm.valid &&
//       this.founderUpdateForm.valid &&
//       this.emailDataForm.valid
//     ) {
//       const formFields = {
//         idea: this.founderUpdateForm.value.founderUpdate || '',
//         target_audience: this.emailDataForm.value.emailData || '',
//         meeting_transcript: this.callTranscriptForm.value.callTranscript || ''
//       };
//       const pitchDeckFile = this.pitchDeckForm.value.pitchDeck?.[0];
//       if (!pitchDeckFile) return;

//       this.loading = true;
//       try {
//         const observable = await this.apiService.submitFile(pitchDeckFile, formFields);
//         observable.subscribe({
//           next: (res) => {
//             this.loading = false;
//             this.dialogRef.close();  // close the dialog
//             // navigate to result page
//             this.router.navigate(['/result-dashboard'], { state: { analysis: res.body } });
//           },
//           error: (err) => {
//             this.loading = false;
//             this.error = err.error?.message || 'Submission failed.';
//           }
//         });
//       } catch (err: any) {
//         this.loading = false;
//         this.error = err.message || 'Submission failed.';
//       }
//     }
//   }

// }
