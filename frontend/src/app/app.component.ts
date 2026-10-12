import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { Subscription, interval, startWith, switchMap } from 'rxjs';

interface Desk { number: number; ticket_id: number | null; ticket_number: string | null; status: string | null }
interface Ticket { id: number; number: string; created_at: string }
interface State { desks: Desk[]; available_desks: number; waiting_count: number; waiting: Ticket[] }

@Component({ selector: 'app-root', standalone: true, imports: [CommonModule], template: `
  <header class="topbar"><a class="brand" href="#"><span class="brand-mark">B</span><span>Banco <b>Central</b></span></a><nav class="view-switch" aria-label="Cambiar vista"><button [class.selected]="view === 'client'" [attr.aria-pressed]="view === 'client'" (click)="setView('client')">Cliente</button><button [class.selected]="view === 'admin'" [attr.aria-pressed]="view === 'admin'" (click)="setView('admin')">Administrador</button></nav><span class="live"><i></i> Sistema en línea</span></header>
  <main>
    <ng-container *ngIf="view === 'client'; else adminView">
      <section class="intro"><div><p class="eyebrow">VISTA DEL CLIENTE</p><h1>Bienvenido a tu banco</h1><p class="sub">Toma tu turno y consulta qué mesa está atendiendo.</p></div><div class="clock"><span class="clock-dot"></span> Atención presencial</div></section>
      <section class="client-layout">
      <article class="card ticket-card"><div class="section-label"><span class="icon">＋</span><span>NUEVO TURNO</span></div><h2>¿En qué podemos ayudarte?</h2><p class="muted">Presiona el botón para obtener tu turno de atención.</p>
        <div class="ticket-display" *ngIf="lastTicket"><span>Tu turno</span><strong>{{lastTicket}}</strong><small>{{lastDesk ? 'Dirígete a la mesa ' + lastDesk : 'Te llamaremos en cuanto una mesa esté disponible'}}</small></div>
        <button class="primary" [disabled]="issuing" (click)="takeTicket()"><span>{{issuing ? 'Generando…' : 'Tomar turno'}}</span><span class="arrow">→</span></button>
        <p class="footnote">El turno se asigna automáticamente a la siguiente mesa disponible.</p>
      </article>
      <article class="card public-board"><div class="section-label"><span class="status-icon">▦</span><span>MESAS EN USO</span><span class="refresh">● Actualizado en vivo</span></div>
        <div class="next-ticket"><span>EL SIGUIENTE TURNO EN ESPERA</span><strong>{{nextTicket}}</strong><small *ngIf="state?.waiting_count">Se llamará cuando una mesa quede libre</small><small *ngIf="!state?.waiting_count">No hay turnos en espera</small></div>
        <div class="public-desks" *ngIf="occupiedDesks.length; else noOccupiedDesks"><div class="public-desk" *ngFor="let desk of occupiedDesks"><span class="public-desk-number">{{desk.number}}</span><span class="public-desk-label"><b>Mesa {{desk.number}}</b><small>Atendiendo ahora</small></span><strong>{{desk.ticket_number}}</strong></div></div>
        <ng-template #noOccupiedDesks><div class="public-empty">Todas las mesas están libres. Puedes tomar un turno.</div></ng-template>
      </article>
      </section>
    </ng-container>
    <ng-template #adminView>
    <section class="intro"><div><p class="eyebrow">PANEL DE ADMINISTRACIÓN</p><h1>Control de atención</h1><p class="sub">Revisa la fila y libera las mesas al finalizar cada servicio.</p></div><div class="clock"><span class="clock-dot"></span> Actualización en vivo</div></section>
    <section class="layout admin-layout">
      <article class="card admin-summary"><div class="section-label"><span class="status-icon">▦</span><span>RESUMEN</span></div><div class="metrics"><div><strong>{{state?.available_desks ?? 4}}<small>/4</small></strong><span>Mesas disponibles</span></div><div><strong>{{state?.waiting_count ?? 0}}</strong><span>Personas en espera</span></div><div><strong>{{occupiedDesks.length}}</strong><span>Mesas ocupadas</span></div></div><p class="admin-note">Al finalizar un servicio, el turno más antiguo en espera se asigna automáticamente a esa mesa.</p></article>
      <article class="card status-card"><div class="section-label"><span class="status-icon">▦</span><span>CONTROL DE MESAS</span><span class="refresh">● Actualizado en vivo</span></div>
        <div class="desk-list"><div class="desk-row" *ngFor="let desk of state?.desks"><div class="desk-number">{{desk.number}}</div><div class="desk-name"><b>Mesa {{desk.number}}</b><span>{{desk.ticket_number ? 'Atendiendo turno' : 'Lista para atender'}}</span></div><div class="desk-ticket" [class.occupied]="desk.ticket_number">{{desk.ticket_number || 'Disponible'}}</div><button *ngIf="desk.ticket_number" class="finish" (click)="finish(desk.number)">Finalizar atención</button></div></div>
        <div class="queue" *ngIf="state?.waiting_count"><span>EN ESPERA</span><div class="queue-tags"><b *ngFor="let ticket of state?.waiting">{{ticket.number}}</b></div></div>
        <div class="empty-queue" *ngIf="!state?.waiting_count">No hay turnos en espera</div>
      </article>
    </section>
    </ng-template>
    <footer><span>© 2026 Banco Central</span><span>Gracias por tu visita</span></footer>
    <div class="toast" *ngIf="error">{{error}}</div>
  </main>
` })
export class AppComponent implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  private subscription?: Subscription;
  state: State | null = null;
  view: 'client' | 'admin' = 'client';
  lastTicket = '';
  lastDesk: number | null = null;
  issuing = false;
  error = '';
  get occupiedDesks(): Desk[] { return this.state?.desks.filter((desk) => desk.ticket_number !== null) ?? []; }
  get nextTicket(): string { return this.state?.waiting[0]?.number ?? '—'; }
  setView(view: 'client' | 'admin'): void { this.view = view; }
  ngOnInit(): void { this.subscription = interval(1800).pipe(startWith(0), switchMap(() => this.http.get<State>('/api/state'))).subscribe({ next: (state) => this.state = state, error: () => this.showError('No se pudo conectar con el servidor. Inicia la API en localhost:8000.') }); }
  ngOnDestroy(): void { this.subscription?.unsubscribe(); }
  takeTicket(): void { this.issuing = true; this.error = ''; this.http.post<{number: string; desk: number | null}>('/api/tickets', {}).subscribe({ next: (ticket) => { this.lastTicket = ticket.number; this.lastDesk = ticket.desk; this.issuing = false; this.refresh(); }, error: () => { this.issuing = false; this.showError('No se pudo generar el turno. Intenta de nuevo.'); } }); }
  finish(desk: number): void { this.http.post(`/api/desks/${desk}/complete`, {}).subscribe({ next: () => this.refresh(), error: () => this.showError('No se pudo finalizar la atención.') }); }
  private refresh(): void { this.http.get<State>('/api/state').subscribe({ next: (state) => this.state = state }); }
  private showError(message: string): void { this.error = message; setTimeout(() => this.error = '', 5000); }
}
