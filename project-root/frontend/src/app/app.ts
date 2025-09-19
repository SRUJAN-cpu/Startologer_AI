import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Navbar } from './components/navbar/navbar';
import { Hero } from './components/hero/hero';
import { Footer } from './components/footer/footer';
import { FeatureCard } from './components/feature-card/feature-card';
import { FileUpload } from './components/file-upload/file-upload';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, Navbar, Hero, FeatureCard, FileUpload, Footer],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class App {
  protected readonly title = signal('frontend');
}
