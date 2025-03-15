import { Injectable } from '@angular/core';
import { UserService } from './UserService';
import { User } from '../models/User';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class InstantApplyService {
  private currentUser: User | null = null;
  private apiBaseUrl = '/api';

  constructor(
    private userService: UserService,
    private http: HttpClient
  ) {
    this.initializeUserData();
  }

  private async initializeUserData(): Promise<void> {
    this.currentUser = await this.userService.getCurrentUser();
  }

  private async refreshUserData(): Promise<void> {
    try {
      this.currentUser = await this.userService.getCurrentUser();
      if (!this.currentUser) {
        throw new Error('User not authenticated');
      }
    } catch (error) {
      console.error('Failed to refresh user data:', error);
      throw new Error('Failed to load user profile. Please log in again.');
    }
  }

  async applyToJob(jobId: string, customMessage?: string): Promise<boolean> {
    try {
      await this.refreshUserData();
      
      if (!this.currentUser) {
        throw new Error('User must be logged in to apply for jobs');
      }

      // Call the Python backend to process the application
      const response = await firstValueFrom(
        this.http.post<{success: boolean}>(`${this.apiBaseUrl}/job/apply`, {
          jobId,
          userId: this.currentUser.id,
          name: this.currentUser.name,
          email: this.currentUser.email,
          phone: this.currentUser.phone,
          resume: this.currentUser.resume,
          customMessage,
          appliedAt: new Date().toISOString()
        })
      );
      
      return response.success;
    } catch (error) {
      console.error('Error applying to job:', error);
      throw error;
    }
  }

  async isProfileReadyForApplications(): Promise<{ready: boolean, missingFields: string[]}> {
    await this.refreshUserData();
    
    const missingFields: string[] = [];
    if (!this.currentUser?.resume) missingFields.push('resume');
    if (!this.currentUser?.phone) missingFields.push('phone number');
    if (!this.currentUser?.skills || this.currentUser.skills.length === 0) 
      missingFields.push('skills');
    
    return {
      ready: missingFields.length === 0,
      missingFields
    };
  }

  async getUserApplications(): Promise<any[]> {
    if (!this.currentUser) {
      await this.refreshUserData();
      if (!this.currentUser) {
        return [];
      }
    }
    
    try {
      // Get applications from Python backend
      const applications = await firstValueFrom(
        this.http.get<any[]>(`${this.apiBaseUrl}/user/applications`)
      );
      
      return applications;
    } catch (error) {
      console.error('Error fetching applications:', error);
      return [];
    }
  }
}
