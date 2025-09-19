import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogActions, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormField, MatFormFieldModule, MatLabel } from '@angular/material/form-field';
import { MatStep, MatStepperModule } from '@angular/material/stepper';
import { FileUploadDialog } from '../../file-upload-dialog/file-upload-dialog/file-upload-dialog';
import { CommonModule } from '@angular/common';
import { MatInputModule } from '@angular/material/input';
import { MatButton } from '@angular/material/button';

@Component({
  selector: 'app-pitch-stepper-dialog',
  imports: [ CommonModule,
    ReactiveFormsModule,   
    MatDialogModule,
    MatStepperModule,   
    MatFormFieldModule,
    MatInputModule,
    FileUploadDialog,
    MatButton,
  ],
  standalone: true,
  templateUrl: './pitch-stepper-dialog.html',
})
export class PitchStepperDialog implements OnInit {
  private formBuilder = inject(FormBuilder);
  dialogRef = inject(MatDialogRef<PitchStepperDialog>);

  pitchDeckForm!: FormGroup;
  callTranscriptForm!: FormGroup;
  founderUpdateForm!: FormGroup;
  emailDataForm!: FormGroup;

  ngOnInit(): void {
    this.pitchDeckForm = this.formBuilder.group({
      pitchDeck: [null, Validators.required]
    });

    this.callTranscriptForm = this.formBuilder.group({
      callTranscript: ['', Validators.required]
    });

    this.founderUpdateForm = this.formBuilder.group({
      founderUpdate: ['']
    });

    this.emailDataForm = this.formBuilder.group({
      emailData: ['']
    });
  }

  onPitchFilesSelected(files: File[]) {
    this.pitchDeckForm.patchValue({ pitchDeck: files });
  }

  onSubmit() {
    if (
      this.pitchDeckForm.valid &&
      this.callTranscriptForm.valid &&
      this.founderUpdateForm.valid &&
      this.emailDataForm.valid
    ) {
      const result = {
        pitchDeck: this.pitchDeckForm.value.pitchDeck,
        callTranscript: this.callTranscriptForm.value.callTranscript,
        founderUpdate: this.founderUpdateForm.value.founderUpdate,
        emailData: this.emailDataForm.value.emailData
      };
      this.dialogRef.close(result);
    }
  }
}
