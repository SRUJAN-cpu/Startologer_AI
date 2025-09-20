import { Component, inject } from '@angular/core';
import { AuthService } from '../auth.service';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { R } from '@angular/cdk/keycodes';
import { MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-login',
  imports: [CommonModule, ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    RouterModule
  ],
  standalone: true,
  templateUrl: './login.html',
})
export class Login {
  private auth = inject(AuthService);
  private router = inject(Router);
  private fb = inject(FormBuilder);
  private dialogRef = inject(MatDialogRef<Login>);
  private snackBar = inject(MatSnackBar);

  form: FormGroup = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  error = '';

  async login() {
    const { email, password } = this.form.value;
    try {
      await this.auth.login(email, password);
      this.dialogRef.close();
      this.router.navigate(['/dashboard']);
      this.snackBar.open('Login successful!', 'Close', {
        duration: 3000, // 3 seconds
        horizontalPosition: 'center',
        verticalPosition: 'top',
        panelClass: ['snack-success']
      });

    } catch (err: any) {
      if (err.code === 'auth/user-not-found') {
        // Redirect to signup if user doesn't exist
        this.router.navigate(['/signup']);
      } else if (err.code === 'auth/wrong-password') {
        this.error = 'Incorrect password';
      } 
      else if (err.code === 'auth/invalid-credential'){
        this.error = 'Invalid credentials provided';
      }
        else {
        this.error = err.message || 'Login failed';
      }
    }
  }

}
