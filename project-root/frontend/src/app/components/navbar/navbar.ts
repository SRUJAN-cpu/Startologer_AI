import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { MatMenuModule } from '@angular/material/menu';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../auth/auth.service';
import { Router, RouterModule } from '@angular/router';
import { getAuth, onAuthStateChanged, User } from 'firebase/auth';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, MatMenuModule, MatButtonModule, MatIconModule, RouterModule],
  templateUrl: './navbar.html',
})
export class Navbar implements OnInit, OnDestroy {
  private auth = inject(AuthService);
  private router = inject(Router);

  currentUser: User | null = null;
  isLoggedIn = false;
  private unsubscribe?: () => void;

  ngOnInit() {
    // Listen to auth state changes
    const fireAuth = getAuth();
    this.unsubscribe = onAuthStateChanged(fireAuth, (user) => {
      this.currentUser = user;
      this.isLoggedIn = !!user;
    });
  }

  ngOnDestroy() {
    if (this.unsubscribe) {
      this.unsubscribe();
    }
  }

  get userDisplayName(): string {
    if (this.currentUser?.displayName) {
      return this.currentUser.displayName;
    }
    if (this.currentUser?.email) {
      // Extract name from email (before @)
      return this.currentUser.email.split('@')[0];
    }
    return 'User';
  }

  get userEmail(): string {
    return this.currentUser?.email || '';
  }

  async logout() {
    try {
      await this.auth.logout();
      this.router.navigate(['/']);
    } catch (error) {
      console.error('Logout error:', error);
    }
  }
}
