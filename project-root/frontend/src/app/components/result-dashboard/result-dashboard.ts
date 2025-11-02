import { Component, inject, OnInit, OnDestroy, AfterViewInit } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AnalysisResult } from '../../services/api.service';
import { MatExpansionModule } from '@angular/material/expansion';
// We'll lazy import jsPDF inside the method to avoid SSR issues

@Component({
  selector: 'app-result-dashboard',
  imports: [CommonModule, MatExpansionModule],
  standalone: true,
  templateUrl: './result-dashboard.html',
})
export class ResultDashboard implements OnInit, OnDestroy, AfterViewInit {
  private router = inject(Router);
  
  analysis: AnalysisResult | null = null;
  isGeneratingPdf = false;
  private charts: any[] = [];
  private ro?: ResizeObserver;
  private io?: IntersectionObserver;
  private isRendering = false;
  private pendingRender = false;
  private renderTimer?: any;
  private renderAttempts = 0;
  private readonly MAX_RENDER_ATTEMPTS = 5;

  ngOnInit() {
    const navigation = this.router.getCurrentNavigation();
    const fromNav = navigation?.extras?.state && (navigation.extras.state as any)['analysis'];
    const fromHistory = (history?.state && (history.state as any).analysis) || null;
    const fromStorage = (() => {
      try {
        const raw = sessionStorage.getItem('analysisLatest');
        return raw ? (JSON.parse(raw) as AnalysisResult) : null;
      } catch {
        return null;
      }
    })();

    this.analysis = (fromNav as AnalysisResult) || (fromHistory as AnalysisResult) || fromStorage;

    if (this.analysis) {
      // Debug logging
      console.log('[ResultDashboard] Analysis data received:', this.analysis);
      console.log('[ResultDashboard] Has benchmarks:', !!this.analysis.benchmarks,
                  'Count:', Object.keys(this.analysis.benchmarks || {}).length);
      console.log('[ResultDashboard] Has llmBenchmark:', !!this.analysis.llmBenchmark);
      console.log('[ResultDashboard] Has llmBenchmark.estimates:', !!this.analysis.llmBenchmark?.estimates,
                  'Count:', Object.keys(this.analysis.llmBenchmark?.estimates || {}).length);
      console.log('[ResultDashboard] hasBenchOrEstimates():', this.hasBenchOrEstimates());

      // keep a copy so reloads still show data
      try { sessionStorage.setItem('analysisLatest', JSON.stringify(this.analysis)); } catch {}
      // Rendering will occur in ngAfterViewInit to avoid double-initialization
    }
  }

  ngAfterViewInit(): void {
    // If analysis was already set (via sessionStorage/history), render charts now
    if (this.analysis) {
      console.log('[ResultDashboard] ngAfterViewInit: Analysis exists, scheduling render');
      this.scheduleRender(0);
    } else {
      console.log('[ResultDashboard] ngAfterViewInit: No analysis data available');
    }
    // Observe charts container for size/visibility changes to re-render charts when needed
    const container = document.getElementById('chartsContainer');
    if (container) {
      console.log('[ResultDashboard] Charts container found, setting up observers');
      if ('ResizeObserver' in window) {
        this.ro = new ResizeObserver(() => {
          // If charts already exist, let Chart.js handle responsive resizing internally.
          if (this.charts.length > 0) return;
          this.scheduleRender(120);
        });
        this.ro.observe(container);
      }
      if ('IntersectionObserver' in window) {
        this.io = new IntersectionObserver((entries) => {
          const e = entries[0];
          if (e && e.isIntersecting) {
            console.log('[ResultDashboard] Charts container is visible, charts count:', this.charts.length);
            // Only render if we haven't already created charts
            if (this.charts.length === 0) this.scheduleRender(0);
          }
        }, { threshold: 0.1 });
        this.io.observe(container);
      }
    } else {
      console.log('[ResultDashboard] WARNING: Charts container not found in DOM');
    }
  }

  goHome() {
    this.router.navigateByUrl('/');
  }

  ngOnDestroy(): void {
    // Clean up charts
    for (const ch of this.charts) {
      try { ch.destroy?.(); } catch {}
    }
    this.charts = [];
    // Disconnect observers
    try { this.ro?.disconnect(); } catch {}
    try { this.io?.disconnect(); } catch {}
  }

  private scheduleRender(delay = 0) {
    if (this.isRendering) { this.pendingRender = true; return; }
    clearTimeout(this.renderTimer);
    this.renderTimer = setTimeout(() => this.renderCharts(), delay);
  }

  private async renderCharts() {
    console.log('[ResultDashboard] renderCharts called, attempt:', this.renderAttempts + 1);
    if (!this.analysis) {
      console.log('[ResultDashboard] No analysis data, skipping chart render');
      return;
    }
    if (this.isRendering) {
      console.log('[ResultDashboard] Already rendering, scheduling pending render');
      this.pendingRender = true;
      return;
    }
    this.renderAttempts++;
    if (this.renderAttempts > this.MAX_RENDER_ATTEMPTS) {
      console.warn('[ResultDashboard] Max render attempts reached. Stopping to prevent infinite loop.');
      console.warn('[ResultDashboard] Likely causes: No benchmark data OR canvas elements not in DOM');
      return;
    }
    this.isRendering = true;
    console.log('[ResultDashboard] Importing Chart.js...');
    const mod = await import('chart.js/auto');
    const Chart = (mod as any).default || (mod as any);
    console.log('[ResultDashboard] Chart.js loaded successfully');

    // Destroy existing charts before re-render
    for (const ch of this.charts) {
      try { ch.destroy?.(); } catch {}
    }
    this.charts = [];

    const bench = (this.analysis.benchmarks || {}) as Record<string, any>;
    let keys = Object.keys(bench);
    // If no dataset benchmarks, try to synthesize comparable arrays from estimates
    const estimates = (this.analysis.llmBenchmark?.estimates || {}) as Record<string, any>;
    const relative = (this.analysis.llmBenchmark?.relative || {}) as Record<string, string>;

    console.log('[ResultDashboard] DEBUG - benchmarks:', bench);
    console.log('[ResultDashboard] DEBUG - llmBenchmark:', this.analysis.llmBenchmark);
    console.log('[ResultDashboard] DEBUG - estimates:', estimates);

    let useEstimates = false;
    if (!keys.length && Object.keys(estimates).length) {
      keys = Object.keys(estimates);
      useEstimates = true;
    }
    console.log('[ResultDashboard] Found metrics keys:', keys, 'useEstimates:', useEstimates);
    if (keys.length) {
      const labels = keys.map(k => this.metricLabel(k));
      const percentiles = keys.map(k => {
        if (!useEstimates) return Math.round(((bench[k].percentile || 0) as number) * 100);
        // Approximate percentile from relative label if only estimates exist
        const rel = (relative[k] || '').toLowerCase();
        if (rel === 'above') return 75;
        if (rel === 'near') return 50;
        if (rel === 'below') return 25;
        return 50;
      });
      console.log('[ResultDashboard] Chart labels:', labels);
      console.log('[ResultDashboard] Chart percentiles:', percentiles);
      // Build company values: from benchmarks when available, otherwise from extractedMetrics
      const unitsMap: Record<string, string> = {};
      if (useEstimates) {
        for (const k of keys) unitsMap[k] = estimates[k]?.unit || '';
      }
      const companyVals = keys.map(k => {
        if (!useEstimates) return bench[k].companyValue ?? NaN;
        const v = this.getCompanyMetricValue(k, unitsMap[k]);
        return v == null ? NaN : v;
      });
      const medians = keys.map(k => useEstimates ? (estimates[k]?.median ?? 0) : (bench[k].median ?? 0));
      const hideCompany = companyVals.every(v => Number.isNaN(v));

      // Radar chart: percentiles
      const radarEl = document.getElementById('radarChart') as HTMLCanvasElement | null;
      console.log('[ResultDashboard] Radar canvas element:', radarEl ? 'found' : 'NOT FOUND');
      if (radarEl) {
        if (!this.ensureCanvasSize(radarEl, 240)) {
          console.log('[ResultDashboard] Radar canvas size not ready, rescheduling');
          this.scheduleRender(200);
          return;
        }
        // Ensure no existing chart is bound to this canvas
        try { (Chart as any).getChart?.(radarEl)?.destroy?.(); } catch {}
        console.log('[ResultDashboard] Creating radar chart with', labels.length, 'metrics');
        const radar = new Chart(radarEl, {
          type: 'radar',
          data: {
            labels,
            datasets: [{
              label: 'Percentile',
              data: percentiles,
              backgroundColor: 'rgba(99, 102, 241, 0.2)',
              borderColor: 'rgba(99, 102, 241, 0.9)',
              pointBackgroundColor: 'rgba(99, 102, 241, 1)'
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            resizeDelay: 100,
            animation: false,
            layout: { padding: { top: 4, bottom: 4, left: 4, right: 4 } },
            scales: { r: { suggestedMin: 0, suggestedMax: 100, ticks: { stepSize: 20 } } },
            plugins: { legend: { display: false } }
          }
        });
        this.charts.push(radar);
        console.log('[ResultDashboard] Radar chart created successfully');
      }

      // Bar chart: company vs median
      const barEl = document.getElementById('barChart') as HTMLCanvasElement | null;
      console.log('[ResultDashboard] Bar canvas element:', barEl ? 'found' : 'NOT FOUND');
      if (barEl) {
        if (!this.ensureCanvasSize(barEl, 240)) {
          this.scheduleRender(200);
          return;
        }
        // Ensure no existing chart is bound to this canvas
        try { (Chart as any).getChart?.(barEl)?.destroy?.(); } catch {}
        const bar = new Chart(barEl, {
          type: 'bar',
          data: {
            labels,
            datasets: [
              // Show company dataset if we have any values (from benchmarks or extractedMetrics)
              { label: 'Company', data: companyVals, backgroundColor: 'rgba(34,197,94,0.7)', hidden: hideCompany },
              { label: 'Median', data: medians, backgroundColor: 'rgba(148,163,184,0.7)' }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            resizeDelay: 100,
            animation: false,
            layout: { padding: { top: 4, bottom: 4, left: 4, right: 4 } },
            plugins: { legend: { position: 'bottom' } },
            scales: { x: { stacked: false }, y: { beginAtZero: true } }
          }
        });
        this.charts.push(bar);
        console.log('[ResultDashboard] Bar chart created successfully');
      }
    } else {
      console.log('[ResultDashboard] No metrics data available for radar/bar charts');
    }

    // Doughnut: composite score
    console.log('[ResultDashboard] Checking for composite score:', this.analysis.score?.composite);
    if (this.analysis.score && this.analysis.score.composite != null) {
      const comp = Math.max(0, Math.min(1, this.analysis.score.composite as number));
      const val = Math.round(comp * 100);
      const rem = 100 - val;
      const doughEl = document.getElementById('doughnutChart') as HTMLCanvasElement | null;
      console.log('[ResultDashboard] Doughnut canvas element:', doughEl ? 'found' : 'NOT FOUND');
      if (doughEl) {
        if (!this.ensureCanvasSize(doughEl, 200)) {
          this.scheduleRender(200);
          return;
        }
        // Ensure no existing chart is bound to this canvas
        try { (Chart as any).getChart?.(doughEl)?.destroy?.(); } catch {}
        const dough = new Chart(doughEl, {
          type: 'doughnut',
          data: {
            labels: ['Score', 'Remaining'],
            datasets: [{ data: [val, rem], backgroundColor: ['#16a34a', '#e5e7eb'] }]
          },
          options: { responsive: true, maintainAspectRatio: false, resizeDelay: 100, animation: false, plugins: { legend: { display: false } }, cutout: '70%' }
        });
        this.charts.push(dough);
        console.log('[ResultDashboard] Doughnut chart created successfully');
      }
    }

    // If canvases weren't in DOM yet AND we have data to render, retry once shortly
    const hasData = keys.length > 0 || (this.analysis.score && this.analysis.score.composite != null);
    if (!document.getElementById('radarChart') && !document.getElementById('barChart') && !document.getElementById('doughnutChart')) {
      if (hasData && this.renderAttempts <= this.MAX_RENDER_ATTEMPTS) {
        console.log('[ResultDashboard] No chart canvases found in DOM, rescheduling render');
        this.scheduleRender(250);
      } else if (!hasData) {
        console.warn('[ResultDashboard] No chart canvases AND no data. Skipping reschedule.');
      } else {
        console.warn('[ResultDashboard] Max attempts reached. Chart canvases may not be in DOM.');
      }
    }

    console.log('[ResultDashboard] Render complete. Total charts created:', this.charts.length);
    // Done rendering; handle any pending rerender request
    this.isRendering = false;
    if (this.pendingRender) { this.pendingRender = false; this.scheduleRender(0); }
  }

  // Ensure the canvas has a measurable size before rendering a chart
  private ensureCanvasSize(el: HTMLCanvasElement, defaultHeight: number): boolean {
    try {
      const rect = el.getBoundingClientRect();
      let width = rect.width;
      let height = rect.height;
      if (!width || !height) {
        // Apply fallback sizes via style so Chart.js gets non-zero computed size
        if (!el.style.width) el.style.width = '100%';
        // Only set default height if not already specified to avoid height growth
        if (!el.style.height || el.style.height === '0px') el.style.height = `${defaultHeight}px`;
        // Recompute
        const r2 = el.getBoundingClientRect();
        width = r2.width;
        height = r2.height;
      }
      // As a last resort, set canvas attributes
      if (!width || !height) {
        const parent = el.parentElement as HTMLElement | null;
        const pW = parent?.clientWidth || 600;
        width = pW;
        height = defaultHeight;
      }
      // Do not set el.width/el.height; let Chart.js manage internal sizing based on CSS box
      return width > 0 && height > 0;
    } catch {
      return false;
    }
  }

  async downloadPdf() {
    if (!this.analysis || this.isGeneratingPdf) return;
    this.isGeneratingPdf = true;
    try {
      const jsPDFmod = await import('jspdf');
      const { jsPDF } = jsPDFmod as any;

  // Data-driven PDF generation (no DOM rendering)
  const pdf = new jsPDF('p', 'mm', 'a4');
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const margin = 12; // outer margin (mm)
  const headerHeight = 18; // space reserved for header (mm)
  const footerHeight = 10; // space for footer page numbers
  const contentWidth = pageWidth - margin * 2;
  const lineHeight = 6; // mm per line
  const bulletIndent = 4; // mm
  let y = margin + headerHeight;

      const setFont = (style: 'normal' | 'bold' = 'normal', size = 11) => {
        pdf.setFont('helvetica', style);
        pdf.setFontSize(size);
      };

      const addHeader = () => {
        // Title and tagline
        pdf.setDrawColor(200);
        setFont('bold', 15);
        pdf.text('Startologer Analysis Report', margin, margin + 6);
        setFont('normal', 10);
        pdf.text('We got this after reading your startup\'s stars :)', margin, margin + 12);
        // Divider line
        pdf.line(margin, margin + 14, pageWidth - margin, margin + 14);
      };

      const ensureSpace = (neededLines = 1) => {
        const needed = neededLines * lineHeight;
        if (y + needed > pageHeight - margin - footerHeight) {
          pdf.addPage();
          addHeader();
          y = margin + headerHeight;
        }
      };

      const addTitle = (text: string) => {
        setFont('bold', 16);
        ensureSpace(2);
        pdf.text(text, margin, y);
        y += lineHeight + 2;
      };

      const addSection = (text: string) => {
        setFont('bold', 13);
        ensureSpace(2);
        pdf.text(text, margin, y);
        y += lineHeight;
      };

      const addLabel = (label: string) => {
        setFont('bold', 11);
        ensureSpace(1);
        pdf.text(label, margin, y);
        y += lineHeight - 1;
      };

      const addParagraph = (text?: string) => {
        if (!text) return;
        setFont('normal', 11);
        // Support multi-paragraph input separated by newlines
        const parts = String(text).split(/\n+/g);
        for (const part of parts) {
          const cleaned = this.sanitizeText(part);
          const lines = pdf.splitTextToSize(cleaned, contentWidth);
          for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            ensureSpace(1);
            // Justify all but the last line of the paragraph and lines with single word
            const hasSpace = line.trim().includes(' ');
            const isLast = i === lines.length - 1;
            if (!isLast && hasSpace) {
              const words = line.split(/\s+/g);
              const gaps = words.length - 1;
              if (gaps <= 0) {
                pdf.text(line, margin, y);
              } else {
                const lineWidth = pdf.getTextWidth(line);
                const extraTotal = contentWidth - lineWidth;
                const spaceWidth = pdf.getTextWidth(' ');
                const gapWidth = spaceWidth + (extraTotal / gaps);
                let x = margin;
                for (let w = 0; w < words.length; w++) {
                  const word = words[w];
                  pdf.text(word, x, y);
                  x += pdf.getTextWidth(word);
                  if (w < words.length - 1) x += gapWidth;
                }
              }
            } else {
              // Last line or no spaces: left-aligned
              pdf.text(line, margin, y);
            }
            y += lineHeight;
          }
          y += 2;
        }
      };

      const addBullets = (items: string[]) => {
        if (!items || !items.length) return;
        setFont('normal', 11);
        for (const raw of items) {
          const cleanedItem = this.sanitizeText(raw);
          const wrapped = pdf.splitTextToSize(cleanedItem, contentWidth - bulletIndent);
          ensureSpace(wrapped.length);
          // First line with bullet symbol
          pdf.text('•', margin, y);
          pdf.text(wrapped[0], margin + bulletIndent, y);
          y += lineHeight;
          // Continuation lines aligned to text indent
          for (let i = 1; i < wrapped.length; i++) {
            ensureSpace(1);
            pdf.text(wrapped[i], margin + bulletIndent, y);
            y += lineHeight;
          }
        }
        y += 2;
      };

      const a = this.analysis!;

  // First page header
  addHeader();
  addTitle(''); // add small spacing under header keeping consistent title spacing

      // Executive Summary
      addSection('Executive Summary');
      addParagraph(a.executiveSummary);

      // Market Analysis
      addSection('Market Analysis');
      addLabel('Market Size');
      addParagraph(a.marketAnalysis?.marketSize);
      addLabel('Growth Rate');
      addParagraph(a.marketAnalysis?.growthRate);
      addLabel('Competition');
      const compTokens = this.tokenize(a.marketAnalysis?.competition);
      if (compTokens.length) {
        addBullets(compTokens);
      } else {
        addParagraph(a.marketAnalysis?.competition);
      }
      addLabel('Barriers to Entry');
      addParagraph(a.marketAnalysis?.entryBarriers);
      addLabel('Regulation');
      addParagraph(a.marketAnalysis?.regulation);

      // Risks
      if (a.risks && a.risks.length) {
        addSection('Key Risks');
        for (const r of a.risks) {
          setFont('bold', 11);
          ensureSpace(1);
          const header = `${r.factor} (${r.impact || 'n/a'})`;
          pdf.text(header, margin, y);
          y += lineHeight - 2;
          addParagraph(r.description);
        }
      }

      // Recommendations
      if (a.recommendations && a.recommendations.length) {
        addSection('Recommendations');
        for (const rec of a.recommendations) {
          const text = `${rec.title ? rec.title + ': ' : ''}${rec.description || ''}`.trim();
          addBullets([text]);
        }
      }

      // Benchmarks
      if (a.benchmarks && Object.keys(a.benchmarks).length) {
        addSection('Benchmarks');
        const entries = Object.entries(a.benchmarks);
        for (const [name, v] of entries) {
          const line = `${name}: ${v.companyValue} · median ${v.median} (${v.status})`;
          addParagraph(line);
        }
      }

      // Benchmark Estimates (neutral label)
      if (a.llmBenchmark && a.llmBenchmark.estimates && Object.keys(a.llmBenchmark.estimates).length) {
        addSection('Benchmark Estimates');
        const rel = a.llmBenchmark.relative || {} as Record<string, string>;
        for (const [name, est] of Object.entries(a.llmBenchmark.estimates as Record<string, any>)) {
          const unit = (est as any).unit ? ` ${(est as any).unit}` : '';
          const r = rel[name] ? ` (${rel[name]})` : '';
          addParagraph(`${this.metricLabel(name)}: median ${(est as any).median}${unit}${r}`);
        }
        // Neutral note without mentioning model provenance
        addParagraph('Note: Estimates are directional; validate with dataset medians for your cohort.');
      }

      // Composite Score
      if (a.score && a.score.composite != null) {
        addSection('Composite Score');
        addParagraph(`Score: ${(a.score.composite as number).toFixed(2)} · Verdict: ${a.score.verdict || ''}`);
      }

      // Footer page numbers
      const pageCount = (pdf as any).getNumberOfPages?.() || pdf.getNumberOfPages?.() || 1;
      for (let i = 1; i <= pageCount; i++) {
        pdf.setPage(i);
        setFont('normal', 9);
        pdf.text(`Page ${i} of ${pageCount}`, pageWidth - margin, pageHeight - 6, { align: 'right' } as any);
      }

      pdf.save('startologer_analysis_result.pdf');
    } catch (e) {
      console.error('Failed to generate PDF:', e);
    } finally {
      this.isGeneratingPdf = false;
    }
  }

  // Helpers to render long lists/strings more readably
  tokenize(text?: string): string[] {
    if (!text) return [];
    return text
      .split(/[\n•;\u2022,]/g)
      .map(s => s.trim())
      .filter(Boolean);
  }

  // Normalize text content to avoid odd glyphs in PDF (e.g., superscript 1 instead of INR symbol)
  private sanitizeText(text?: string): string {
    if (!text) return '';
    let s = String(text);
    try { s = s.normalize('NFKC'); } catch {}
    // Remove zero-width and BOM
    s = s.replace(/[\u200B-\u200D\uFEFF]/g, '');
    // Replace superscript 1 and rupee sign with ASCII-safe 'INR '
    s = s.replace(/[\u00B9\u20B9]/g, 'INR ');
    // Replace non-breaking space with normal space
    s = s.replace(/\u00A0/g, ' ');
    // Normalize curly quotes and dashes
    s = s.replace(/[\u2018\u2019]/g, "'")
         .replace(/[\u201C\u201D]/g, '"')
         .replace(/[\u2013\u2014]/g, '-');
    return s;
  }

  // ----- UI helpers for nicer Benchmarks header -----
  hasSectorOrStage(): boolean {
    const chips = this.getSectorChips();
    const stage = this.getStageLabel();
    return (chips.length > 0) || !!stage;
  }

  getSectorChips(): string[] {
    const raw = (this.analysis?.cohort?.sector || this.analysis?.extractedMetrics?.sector || '').toString();
    if (!raw) return [];
    // Split on common separators and whitespace
    const tokens = raw
      .split(/[\s,;\/|·]+/g)
  .map((t: string) => t.trim())
      .filter(Boolean);

    // Common stopwords and noise that can sneak into sector strings
    const stop = new Set([
      'm','mn','mo','mos','month','months','k','cr','crore','lakh','lakhs','bn','b','mm','billion','million',
      'yoy','mom','arr','mrr','ltv','cac','margin','growth','churn','headcount','runway',
      'in','the','and','of','to','for','with','on','at','by','from','as','is','are','be','where','compliance',
      'competitive','competition','sector','stage','benchmarks','benchmark','company','deck','summary','overview',
      'business','plan','gtm','go','market','analysis','regulation','entry','barriers'
    ]);

    // Map synonyms/variants to canonical sector chips
    const canonicalMap: Record<string, string> = {
      saas: 'SaaS', software: 'SaaS', enterprise: 'SaaS',
      fintech: 'Fintech', finance: 'Fintech', payments: 'Fintech', paytech: 'Fintech',
      bfsi: 'BFSI',
      insurtech: 'Insurtech', insuretech: 'Insurtech',
      ecommerce: 'Ecommerce', ecom: 'Ecommerce', commerce: 'Ecommerce', marketplace: 'Marketplace', marketplaces: 'Marketplace',
      healthtech: 'Healthtech', healthcare: 'Healthtech', medtech: 'Healthtech',
      edtech: 'Edtech',
      mobility: 'Mobility', logistics: 'Logistics',
      gaming: 'Gaming',
      ai: 'AI', ml: 'AI',
      security: 'Security',
      devtools: 'DevTools', developer: 'DevTools',
      proptech: 'Proptech', realestate: 'Proptech',
      travel: 'Travel', media: 'Media',
      agritech: 'Agritech', agri: 'Agritech',
      hr: 'HR', hrtech: 'HR',
      resale: 'Resale'
    };

    const seen = new Set<string>();
    const chips: string[] = [];
    for (const tokRaw of tokens) {
      if (/\d/.test(tokRaw)) continue; // skip tokens with digits
      if (!/^[A-Za-z][A-Za-z&+.-]*$/.test(tokRaw)) continue; // alpha-ish only
      const tok = tokRaw.toLowerCase();
      if (tok.length <= 1) continue;
      if (stop.has(tok)) continue;
      const canonical = canonicalMap[tok];
      if (!canonical) continue; // only show recognized sectors
      if (!seen.has(canonical)) {
        seen.add(canonical);
        chips.push(canonical);
      }
      if (chips.length >= 4) break; // cap
    }
    return chips;
  }

  getStageLabel(): string {
    const raw = (this.analysis?.cohort?.stage || this.analysis?.extractedMetrics?.stage || '').toString().trim().toLowerCase();
    if (!raw) return '';
    if (/pre\s*-?\s*seed/.test(raw)) return 'Pre-Seed';
    if (/seed/.test(raw)) return 'Seed';
    if (/angel/.test(raw)) return 'Angel';
    const m = raw.match(/series\s*-?\s*([a-z])/i);
    if (m && m[1]) return `Series ${m[1].toUpperCase()}`;
    if (/(growth|late)/.test(raw)) return 'Growth';
    // Fallback to a cleaned title case up to 20 chars
    const cleaned = raw.replace(/[^a-z\s-]/gi, ' ').replace(/\s+/g, ' ').trim();
    const titled = this.titleCase(cleaned);
    return titled.length > 20 ? titled.slice(0, 20) + '…' : titled;
  }

  stageClass(label: string): string {
    const l = (label || '').toLowerCase();
    if (!l) return 'bg-slate-500';
    if (l.includes('pre-seed')) return 'bg-amber-600';
    if (l.includes('seed')) return 'bg-emerald-600';
    if (l.includes('series')) return 'bg-indigo-600';
    if (l.includes('angel')) return 'bg-teal-600';
    if (l.includes('growth')) return 'bg-purple-600';
    return 'bg-slate-600';
  }

  private titleCase(s: string): string {
    return s
      .toLowerCase()
      .split(/\s+/)
      .map(w => w ? w[0].toUpperCase() + w.slice(1) : w)
      .join(' ');
  }

  metricLabel(key: string): string {
    const k = (key || '').toString();
    const map: Record<string, string> = {
      arr: 'ARR',
      mrr: 'MRR',
      growthYoY: 'Growth YoY',
      growthMoM: 'Growth MoM',
      churnRate: 'Churn Rate',
      cac: 'CAC',
      ltv: 'LTV',
      grossMargin: 'Gross Margin',
      headcount: 'Headcount',
      runwayMonths: 'Runway (months)'
    };
    return map[k] || this.titleCase(k);
  }

  // ----- Chart guards -----
  hasBenchOrEstimates(): boolean {
    const b = this.analysis?.benchmarks as Record<string, any> | undefined;
    const e = this.analysis?.llmBenchmark?.estimates as Record<string, any> | undefined;
    return (!!b && Object.keys(b).length > 0) || (!!e && Object.keys(e).length > 0);
  }

  // Map extractedMetrics to chart keys and normalize based on unit
  private getCompanyMetricValue(key: string, unit?: string): number | null {
    const em = this.analysis?.extractedMetrics as Record<string, any> | undefined;
    if (!em) return null;
    const mapKey = key;
    let v: any = undefined;
    // direct key
    v = em[mapKey];
    // simple aliases
    if (v == null) {
      const aliases: Record<string, string[]> = {
        growthYoY: ['growthYoY', 'yoy', 'growth_yoy'],
        growthMoM: ['growthMoM', 'mom', 'growth_mom'],
        churnRate: ['churnRate', 'churn'],
        grossMargin: ['grossMargin', 'margin'],
      };
      for (const [k, arr] of Object.entries(aliases)) {
        if (k === key) {
          for (const a of arr) {
            if (em[a] != null) { v = em[a]; break; }
          }
        }
      }
    }
    if (v == null) return null;
    let num = Number(v);
    if (!isFinite(num)) return null;
    const u = (unit || '').toLowerCase();
    // Normalize percent metrics: if values are in [0,1] but unit indicates %, scale to match medians
    const percentKeys = new Set(['growthYoY','growthMoM','churnRate','grossMargin']);
    if (percentKeys.has(key)) {
      if (u.includes('%')) {
        // If extracted value seems 0-1, convert to percentage scale similar to medians
        if (num <= 1) num = num * 100;
      } else {
        // No % unit provided; keep as-is but if clearly 0-1, scale to 0-100 for comparison
        if (num <= 1) num = num * 100;
      }
    }
    // Currency-like: leave as-is; units mismatch is acceptable for rough comparison
    return num;
  }
}
