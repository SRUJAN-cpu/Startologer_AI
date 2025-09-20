import { Component, inject } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { SingUp } from '../../auth/sign-up/sing-up';
import { CommonModule } from '@angular/common';
import { Login } from '../../auth/login/login';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, MatDialogModule],
  templateUrl: './navbar.html',
})
export class Navbar {
  private dialog = inject(MatDialog);

  openLoginDialog() {
    this.dialog.open(Login, {
      width: '800px',
      disableClose: false
    });
  }

  openSignUpDialog() {
    this.dialog.open(SingUp, {
      width: '800px',
      disableClose: false
    });
  }
}
