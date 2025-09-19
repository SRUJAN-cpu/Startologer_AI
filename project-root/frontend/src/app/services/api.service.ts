import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private apiUrl = 'http://127.0.0.1:5000';  // Flask server URL

  constructor(private http: HttpClient) { }

  submitFile(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    
    const headers = new HttpHeaders()
      .set('Accept', 'application/json')
      .set('Access-Control-Allow-Origin', 'http://localhost:4200');

    return this.http.post(`${this.apiUrl}/submit`, formData, {
      headers,
      withCredentials: false,
      observe: 'response'
    });
  }

  getProcessedDetails(): Observable<any> {
    const headers = new HttpHeaders().set('Accept', 'application/json');
    return this.http.get(`${this.apiUrl}/get_processed_details`, {
      headers,
      withCredentials: false // Important for CORS
    });
  }
}