import { Component, signal, inject } from '@angular/core';
import { Router, RouterOutlet, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Navbar } from './components/navbar/navbar';
import { Hero } from './components/hero/hero';
import { Footer } from './components/footer/footer';
import { FeatureCard } from './components/feature-card/feature-card';

@Component({
  selector: 'app-root',
  imports: [CommonModule, RouterOutlet, Navbar, Hero, FeatureCard, Footer],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class App {
  protected readonly title = signal('frontend');

  private router = inject(Router);
  currentUrl = '/';

  ngOnInit() {
    // Initialize current URL and keep it updated on navigation
    this.currentUrl = this.router.url;
    this.router.events.subscribe(evt => {
      if (evt instanceof NavigationEnd) {
        this.currentUrl = evt.urlAfterRedirects || evt.url;
      }
    });
  }

  get isHomeRoute(): boolean {
    // Treat root path as the home page
    return this.currentUrl === '/' || this.currentUrl === '';
  }
}
