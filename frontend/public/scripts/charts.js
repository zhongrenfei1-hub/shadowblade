// Tiny dependency-free chart primitives used across pages.
// Kept inline so the Design ring can iterate on visual rhythm
// without bringing in a charting framework.

(function () {
  const ACCENT =
    (typeof getComputedStyle === 'function' &&
      getComputedStyle(document.documentElement)
        .getPropertyValue('--sb-accent-500')
        .trim()) ||
    '#22D3B7';

  function inject(svg, points, opts = {}) {
    const ns = 'http://www.w3.org/2000/svg';
    const w = opts.width || 600;
    const h = opts.height || 220;
    const pad = opts.pad || { top: 12, right: 12, bottom: 28, left: 32 };
    const max = Math.max(...points.map((p) => p.value));
    const min = 0;
    const stepX = (w - pad.left - pad.right) / (points.length - 1);

    svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    svg.classList.add('sb-chart');

    const defs = document.createElementNS(ns, 'defs');
    defs.innerHTML = `
      <linearGradient id="sb-grad-accent" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#22D3B7" stop-opacity="0.45"/>
        <stop offset="100%" stop-color="#22D3B7" stop-opacity="0"/>
      </linearGradient>
      <linearGradient id="sb-grad-bar" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#38BDF8" stop-opacity="0.85"/>
        <stop offset="100%" stop-color="#22D3B7" stop-opacity="0.65"/>
      </linearGradient>`;
    svg.appendChild(defs);

    // gridlines
    const gridCount = 4;
    for (let i = 0; i <= gridCount; i++) {
      const y = pad.top + ((h - pad.top - pad.bottom) / gridCount) * i;
      const ln = document.createElementNS(ns, 'line');
      ln.setAttribute('x1', pad.left);
      ln.setAttribute('x2', w - pad.right);
      ln.setAttribute('y1', y);
      ln.setAttribute('y2', y);
      ln.setAttribute('class', 'grid');
      svg.appendChild(ln);
      const label = document.createElementNS(ns, 'text');
      label.setAttribute('x', pad.left - 6);
      label.setAttribute('y', y + 3);
      label.setAttribute('text-anchor', 'end');
      label.textContent = Math.round(max - ((max - min) / gridCount) * i);
      svg.appendChild(label);
    }

    if (opts.kind === 'bar') {
      const bw = stepX * 0.45;
      points.forEach((p, i) => {
        const x = pad.left + stepX * i - bw / 2;
        const yv = pad.top + (h - pad.top - pad.bottom) * (1 - (p.value - min) / (max - min));
        const rect = document.createElementNS(ns, 'rect');
        rect.setAttribute('x', x);
        rect.setAttribute('y', yv);
        rect.setAttribute('width', bw);
        rect.setAttribute('height', h - pad.bottom - yv);
        rect.setAttribute('rx', 4);
        rect.setAttribute('class', 'bar-primary');
        svg.appendChild(rect);

        const lbl = document.createElementNS(ns, 'text');
        lbl.setAttribute('x', pad.left + stepX * i);
        lbl.setAttribute('y', h - pad.bottom + 16);
        lbl.setAttribute('text-anchor', 'middle');
        lbl.textContent = p.label;
        svg.appendChild(lbl);
      });
      return;
    }

    // area + line
    const linePts = points.map((p, i) => {
      const x = pad.left + stepX * i;
      const y = pad.top + (h - pad.top - pad.bottom) * (1 - (p.value - min) / (max - min));
      return [x, y];
    });

    const areaD =
      `M ${linePts[0][0]} ${h - pad.bottom} ` +
      linePts.map(([x, y]) => `L ${x} ${y}`).join(' ') +
      ` L ${linePts[linePts.length - 1][0]} ${h - pad.bottom} Z`;
    const area = document.createElementNS(ns, 'path');
    area.setAttribute('d', areaD);
    area.setAttribute('class', 'area-primary');
    svg.appendChild(area);

    const lineD = linePts.map(([x, y], i) => `${i ? 'L' : 'M'} ${x} ${y}`).join(' ');
    const line = document.createElementNS(ns, 'path');
    line.setAttribute('d', lineD);
    line.setAttribute('class', 'line-primary');
    svg.appendChild(line);

    points.forEach((p, i) => {
      const [x, y] = linePts[i];
      const c = document.createElementNS(ns, 'circle');
      c.setAttribute('cx', x);
      c.setAttribute('cy', y);
      c.setAttribute('r', 3);
      c.setAttribute('fill', ACCENT);
      svg.appendChild(c);

      const lbl = document.createElementNS(ns, 'text');
      lbl.setAttribute('x', x);
      lbl.setAttribute('y', h - pad.bottom + 16);
      lbl.setAttribute('text-anchor', 'middle');
      lbl.textContent = p.label;
      svg.appendChild(lbl);
    });
  }

  function sparkline(svg, values) {
    const ns = 'http://www.w3.org/2000/svg';
    const w = 120,
      h = 36,
      pad = 2;
    const max = Math.max(...values);
    const min = Math.min(...values);
    const stepX = (w - pad * 2) / (values.length - 1);
    svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    const pts = values.map((v, i) => {
      const x = pad + stepX * i;
      const y = pad + (h - pad * 2) * (1 - (v - min) / Math.max(max - min, 1));
      return [x, y];
    });
    const line = document.createElementNS(ns, 'path');
    line.setAttribute('d', pts.map(([x, y], i) => `${i ? 'L' : 'M'} ${x} ${y}`).join(' '));
    line.setAttribute('fill', 'none');
    line.setAttribute('stroke', ACCENT);
    line.setAttribute('stroke-width', '1.5');
    svg.appendChild(line);
    const dot = document.createElementNS(ns, 'circle');
    const last = pts[pts.length - 1];
    dot.setAttribute('cx', last[0]);
    dot.setAttribute('cy', last[1]);
    dot.setAttribute('r', '2');
    dot.setAttribute('fill', ACCENT);
    svg.appendChild(dot);
  }

  window.ShadowBladeCharts = { inject, sparkline };
})();

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-sparkline]').forEach((el) => {
    const values = JSON.parse(el.dataset.sparkline);
    window.ShadowBladeCharts.sparkline(el, values);
  });
  document.querySelectorAll('[data-chart]').forEach((el) => {
    const data = JSON.parse(el.dataset.chart);
    const opts = JSON.parse(el.dataset.chartOpts || '{}');
    window.ShadowBladeCharts.inject(el, data, opts);
  });
});
