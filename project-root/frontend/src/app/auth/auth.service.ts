import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { initializeApp } from 'firebase/app';
import {
    getAuth,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signOut,
    GoogleAuthProvider,
    signInWithPopup
} from 'firebase/auth';
import { environment } from '../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {
    private app = initializeApp(environment.firebaseConfig);
    private auth = getAuth(this.app);

    constructor(private router: Router) { }

    async signup(email: string, password: string) {
        return createUserWithEmailAndPassword(this.auth, email, password);
    }

    async login(email: string, password: string) {
        return signInWithEmailAndPassword(this.auth, email, password);
    }

    async loginWithGoogle() {
        const provider = new GoogleAuthProvider();
        return signInWithPopup(this.auth, provider);
    }

    async logout() {
        await signOut(this.auth);
        this.router.navigate(['/']);
    }

    get currentUser() {
        return this.auth.currentUser;
    }

    async getIdToken(): Promise<string | null> {
        return this.auth.currentUser ? this.auth.currentUser.getIdToken() : null;
    }

    isLoggedIn(): boolean {
        return !!this.auth.currentUser;
    }
}
