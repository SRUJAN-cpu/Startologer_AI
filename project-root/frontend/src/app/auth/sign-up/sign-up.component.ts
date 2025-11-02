import { Component, inject } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { AuthService } from '../auth.service';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

@Component({
  selector: 'app-sign-up',
  imports: [CommonModule, ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    MatSnackBarModule,
    RouterModule,
  ],
  standalone: true,
  templateUrl: './sign-up.component.html',
})
export class SignUp {

  private auth = inject(AuthService);
  private router = inject(Router);
  private formBuilder = inject(FormBuilder);
  private snackBar = inject(MatSnackBar);

  error = '';
  form: FormGroup = this.formBuilder.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
  });

  async signup() {
    try {
      await this.auth.signup(this.form.value.email, this.form.value.password);
      this.snackBar.open('Account created! Please login to continue.', 'Close', {
        duration: 4000,
        horizontalPosition: 'center',
        verticalPosition: 'top',
        panelClass: ['snack-success'],
      });
      // Redirect to login page after successful signup
      setTimeout(() => {
        this.router.navigate(['/login']);
      }, 500);

    } catch (err: any) {
      this.error = err.message;
    }
  }
}

