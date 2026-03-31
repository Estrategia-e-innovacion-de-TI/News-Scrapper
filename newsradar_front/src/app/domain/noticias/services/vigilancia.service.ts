import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class VigilanciaService {
  validateSubscription(email: string, name: string, groups: string[]): boolean {
    return this.isValidEmail(email) && !!name.trim() && groups.length > 0;
  }

  isValidEmail(email: string): boolean {
    if (!email || !email.trim()) return false;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email.trim());
  }
}
