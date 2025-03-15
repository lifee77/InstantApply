import { Injectable } from '@angular/core';
import { User } from '../models/User';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class UserService {
  private user: User | null = null;
  private apiBaseUrl = '/api'; // Base URL for API requests

  constructor(private http: HttpClient) {
    this.loadUserFromStorage();
  }

  public loadUserFromStorage(): void {
    // Check if we have user in local storage
    const userData = localStorage.getItem('user');
    if (userData) {
      try {
        this.user = JSON.parse(userData);
      } catch (e) {
        console.error('Error parsing user data:', e);
        this.user = null;
      }
    }
  }

  async getCurrentUser(): Promise<User | null> {
    // Try to get user from API first, fallback to local storage
    try {
      const userData = await firstValueFrom(this.http.get<User>(`${this.apiBaseUrl}/user/current`));
      if (userData) {
        // Update local storage with latest user data
        this.user = userData;
        localStorage.setItem('user', JSON.stringify(this.user));
        return this.user;
      }
    } catch (error) {
      console.error('Error fetching current user:', error);
      // On error, just return what we have in memory/storage
    }
    
    return this.user;
  }

  isLoggedIn(): boolean {
    return this.user !== null;
  }

  async updateUserProfile(profileData: Partial<User>): Promise<User | null> {
    if (!this.user) {
      throw new Error('Cannot update profile: User not authenticated');
    }
    
    try {
      // Send update to backend
      const updatedUser = await firstValueFrom(
        this.http.post<User>(`${this.apiBaseUrl}/user/update`, profileData)
      );
      
      // Update local user data
      this.user = updatedUser;
      localStorage.setItem('user', JSON.stringify(this.user));
      return this.user;
    } catch (error) {
      console.error('Error updating profile:', error);
      throw new Error('Failed to update profile');
    }
  }

  async uploadResume(file: File): Promise<string> {
    if (!this.user) {
      throw new Error('Cannot upload resume: User not authenticated');
    }

    try {
      const formData = new FormData();
      formData.append('resume', file);
      
      const response = await firstValueFrom(
        this.http.post<{resumeUrl: string}>(`${this.apiBaseUrl}/user/upload-resume`, formData)
      );
      
      // Update user's resume URL
      await this.updateUserProfile({ resume: response.resumeUrl });
      
      return response.resumeUrl;
    } catch (error) {
      console.error('Error uploading resume:', error);
      throw new Error('Failed to upload resume');
    }
  }

  // Add other user-related methods as needed
}
