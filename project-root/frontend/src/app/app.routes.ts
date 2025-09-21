import { Routes } from '@angular/router';
import { App } from './app';
import { AuthGuard } from './auth/auth.guard';
import { ResultDashboard } from './components/result-dashboard/result-dashboard';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./auth/login/login').then(m => m.Login) },
  { path: 'signup', loadComponent: () => import('./auth/sign-up/sing-up').then(m => m.SingUp) },
  { path: 'result-dashboard', component: ResultDashboard },
  { path: 'dashboard', component: App, canActivate: [AuthGuard] },
  { path: '', component: App }
];
