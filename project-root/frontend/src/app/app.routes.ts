import { Routes } from '@angular/router';
import { App } from './app';
import { AuthGuard } from './auth/auth.guard';

export const routes: Routes = [
//   { path: 'login', component: Login },
//   { path: 'signup', component: SingUp },
{ path: 'login', loadComponent: () => import('./auth/login/login').then(m => m.Login) },
{ path: 'signup', loadComponent: () => import('./auth/sign-up/sing-up').then(m => m.SingUp) },
//   { path: 'dashboard', component: DashboardComponent, canActivate: [AuthGuard] },
  { path: 'dashboard', component: App, canActivate: [AuthGuard] },
  { path: '', redirectTo: 'app', pathMatch: 'full' }
];
