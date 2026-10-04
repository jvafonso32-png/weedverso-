import pathlib
import re

html = pathlib.Path('d:/weedverso/app/index.html').read_text(encoding='utf-8')

css_to_add = """
/* FinTech Chart Styles */
@keyframes svgDraw { to { stroke-dashoffset: 0; } }
@keyframes popIn { from { opacity: 0; transform: translateY(10px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
.ft-panel { border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; background: linear-gradient(180deg, rgba(16,24,20,0.95), rgba(10,16,14,0.98)); box-shadow: 0 12px 32px rgba(0,0,0,0.3); padding: 16px; display: flex; flex-direction: column; gap: 16px; margin-bottom: 12px; position: relative; overflow: hidden; }
.ft-panel::before { content:''; position: absolute; top:0; left:0; right:0; height: 1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent); }
.ft-header { display: flex; justify-content: space-between; align-items: flex-end; z-index: 2; }
.ft-title { font-size: 0.8rem; color: var(--mut); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700; margin-bottom: 4px; }
.ft-amount { font-family: var(--font-display); font-size: 1.8rem; font-weight: 800; color: #fff; line-height: 1; letter-spacing: -0.02em; }
.ft-amount span { font-size: 1rem; color: var(--mut); font-weight: 600; }
.ft-badge { padding: 4px 10px; border-radius: 999px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.02em; display: inline-flex; align-items: center; gap: 4px; }
.ft-badge.up { background: rgba(255,95,112,0.15); color: #ff7d8d; border: 1px solid rgba(255,95,112,0.3); }
.ft-badge.down { background: rgba(57,255,143,0.15); color: #39ff8f; border: 1px solid rgba(57,255,143,0.3); }
.ft-badge.neutral { background: rgba(255,255,255,0.05); color: var(--mut); border: 1px solid rgba(255,255,255,0.1); }
.ft-chart-container { height: 140px; position: relative; margin: 8px -8px 0 -8px; z-index: 1; }
.ft-chart-svg { width: 100%; height: 100%; overflow: visible; }
.ft-chart-tooltip { position: absolute; background: rgba(0,0,0,0.8); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.1); padding: 6px 10px; border-radius: 8px; color: #fff; font-size: 0.75rem; font-weight: 600; pointer-events: none; opacity: 0; transition: opacity 0.2s, transform 0.1s; transform: translate(-50%, -100%); margin-top: -10px; z-index: 10; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
.ft-chart-point { position: absolute; width: 10px; height: 10px; border-radius: 50%; background: #fff; transform: translate(-50%, -50%); opacity: 0; transition: opacity 0.2s; pointer-events: none; z-index: 9; }
.ft-chart-touch { position: absolute; inset: 0; z-index: 5; }
.ft-chart-axis { display: flex; justify-content: space-between; padding: 0 16px; margin-top: -10px; z-index: 2; position: relative; }
.ft-chart-axis span { font-size: 0.65rem; color: rgba(255,255,255,0.4); font-weight: 600; }
.ft-cats { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; z-index: 2; }
.ft-cat { display: grid; grid-template-columns: 36px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 10px; background: rgba(255,255,255,0.02); border-radius: 12px; border: 1px solid rgba(255,255,255,0.04); animation: popIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) both; }
.ft-cat:hover { background: rgba(255,255,255,0.04); }
.ft-cat-icon { width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; font-size: 1.1rem; }
.ft-cat-info { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.ft-cat-name { font-size: 0.85rem; font-weight: 700; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1; }
.ft-cat-bar-wrap { height: 4px; background: rgba(255,255,255,0.06); border-radius: 999px; overflow: hidden; }
.ft-cat-bar { height: 100%; border-radius: 999px; transition: width 1s cubic-bezier(0.16, 1, 0.3, 1); }
.ft-cat-val { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
.ft-cat-val strong { font-family: var(--font-display); font-size: 0.95rem; font-weight: 700; color: #fff; line-height: 1; }
.ft-cat-val span { font-size: 0.65rem; color: var(--mut); font-weight: 600; }
"""

if '/* FinTech Chart Styles */' not in html:
    html = html.replace('</style>', css_to_add + '\n</style>')

js_to_add = """
function generateCurveSVG(points, width, height, strokeColor, fillGradientId) {
  if (!points || points.length === 0) return { svg: '', coords: [] };
  const pData = points.length === 1 ? [points[0], points[0]] : points;
  const max = Math.max(...pData) || 1;
  const min = Math.min(...pData);
  const padTop = 15, padBot = 15;
  const innerW = width;
  const innerH = height - padTop - padBot;
  
  const coords = pData.map((val, i) => {
    const x = (i / (pData.length - 1)) * innerW;
    const y = padTop + innerH - (val / max) * innerH;
    return { x, y, val };
  });
  
  let d = `M ${coords[0].x},${coords[0].y}`;
  for (let i = 0; i < coords.length - 1; i++) {
    const cp1x = coords[i].x + (coords[i+1].x - coords[i].x) / 2;
    const cp2x = cp1x;
    d += ` C ${cp1x},${coords[i].y} ${cp2x},${coords[i+1].y} ${coords[i+1].x},${coords[i+1].y}`;
  }
  
  const areaD = `${d} L ${width},${height} L 0,${height} Z`;
  const pathLength = width * 2;
  
  const svg = `
    <svg class="ft-chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <defs>
        <linearGradient id="${fillGradientId}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${strokeColor}" stop-opacity="0.4" />
          <stop offset="100%" stop-color="${strokeColor}" stop-opacity="0.0" />
        </linearGradient>
        <filter id="glow-${fillGradientId}" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>
      <path d="${areaD}" fill="url(#${fillGradientId})" />
      <path d="${d}" fill="none" stroke="${strokeColor}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow-${fillGradientId})" style="stroke-dasharray: ${pathLength}; stroke-dashoffset: ${pathLength}; animation: svgDraw 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;" />
    </svg>
  `;
  return { svg, coords };
}

function attachChartInteraction(containerId, coords, labels) {
  const container = document.getElementById(containerId);
  if(!container) return;
  const touchArea = container.querySelector('.ft-chart-touch');
  const tooltip = container.querySelector('.ft-chart-tooltip');
  const point = container.querySelector('.ft-chart-point');
  if(!touchArea || !tooltip || !point) return;
  
  const update = (e) => {
    const rect = touchArea.getBoundingClientRect();
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
    let closest = coords[0], minDist = Infinity, bestIdx = 0;
    coords.forEach((c, i) => {
      const dist = Math.abs((c.x / 100 * rect.width) - x);
      if(dist < minDist) { minDist = dist; closest = c; bestIdx = i; }
    });
    const px = (closest.x / 100) * rect.width;
    const py = (closest.y / 100) * rect.height;
    point.style.transform = `translate(-50%, -50%) translate(${px}px, ${py}px)`;
    point.style.opacity = '1';
    point.style.boxShadow = `0 0 12px ${point.dataset.color}`;
    tooltip.innerHTML = `<span>${labels[bestIdx]}</span><br/><strong>${money(closest.val)}</strong>`;
    tooltip.style.left = `${px}px`;
    tooltip.style.top = `${py}px`;
    tooltip.style.opacity = '1';
  };
  
  const leave = () => { point.style.opacity = '0'; tooltip.style.opacity = '0'; };
  
  touchArea.addEventListener('mousemove', update);
  touchArea.addEventListener('touchmove', (e)=>{ e.preventDefault(); update(e); }, {passive:false});
  touchArea.addEventListener('mouseleave', leave);
  touchArea.addEventListener('touchend', leave);
}
"""

if 'function generateCurveSVG' not in html:
    html = html.replace('function drawDoughnutChart', js_to_add + '\nfunction drawDoughnutChart')

new_account_flow = """
function renderAccountFlowChart(){
  const period = ui.accountFlowPeriod || 'month';
  const all = accountOutRows();
  const now = new Date(), today0 = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const end = new Date(today0); end.setDate(end.getDate() + 1);
  const wd = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'], mn = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
  
  let buckets = [], start, prevStart = null, prevEnd = null, label = '', unit = 'day';
  
  if(period === '7d'){
    start = new Date(today0); start.setDate(start.getDate() - 6);
    prevStart = new Date(start); prevStart.setDate(prevStart.getDate() - 7); prevEnd = start;
    for(let i=0; i<7; i++){ const d = new Date(start); d.setDate(start.getDate() + i); buckets.push({ key: spxDayKey(d), label: wd[d.getDay()], tip: `${d.getDate()}/${d.getMonth()+1}`, value: 0 }); }
    label = 'Últimos 7 dias';
  } else if(period === 'all'){
    unit = 'month';
    start = new Date(now.getFullYear(), now.getMonth() - 5, 1);
    for(let i=0; i<6; i++){ const d = new Date(start.getFullYear(), start.getMonth() + i, 1); buckets.push({ key: spxMonthKey(d), label: mn[d.getMonth()], tip: `${mn[d.getMonth()]}`, value: 0 }); }
    label = 'Últimos 6 meses';
  } else {
    start = new Date(now.getFullYear(), now.getMonth(), 1);
    prevStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    prevEnd = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate() + 1);
    for(let i=1; i<=now.getDate(); i++){ buckets.push({ key: spxDayKey(new Date(now.getFullYear(), now.getMonth(), i)), label: String(i), tip: `${i}/${now.getMonth()+1}`, value: 0 }); }
    label = 'Neste mês';
  }
  
  const inRange = all.filter(r => r.date >= start && r.date < end);
  const bmap = {}; buckets.forEach(b => bmap[b.key] = b);
  inRange.forEach(r => { const b = bmap[unit === 'month' ? spxMonthKey(r.date) : spxDayKey(r.date)]; if(b) b.value += r.value; });
  
  const total = inRange.reduce((s,r) => s + r.value, 0);
  let trendHtml = `<div class="ft-badge neutral">Sem dados</div>`;
  
  if(prevStart){
    const prev = all.filter(r => r.date >= prevStart && r.date < prevEnd).reduce((s,r) => s + r.value, 0);
    if(prev > 0){
      const diff = Math.round(((total - prev) / prev) * 100);
      trendHtml = diff > 0 ? `<div class="ft-badge up">▲ ${diff}% vs ant.</div>` : `<div class="ft-badge down">▼ ${Math.abs(diff)}% vs ant.</div>`;
    }
  }
  
  const catColors = ['#00e676','#18ffff','#b388ff','#ff4081','#ffeb3b','#ff9800','#00b0ff'];
  const cats = compressBreakdown(buildCategoryBreakdown(
    inRange.map(r => ({ value: r.value, label: r.label, key: r.key })),
    catColors, 'Sem categoria'
  ), 6, 'Outros');
  
  const wrap = document.getElementById('accountFlowLegend');
  if(!wrap) return;
  if(!total) {
    wrap.innerHTML = `<div class="ft-panel"><div class="empty">Nenhuma saída no período (${label}).</div></div>`;
    return;
  }
  
  const color = '#00e676';
  const { svg, coords } = generateCurveSVG(buckets.map(b => b.value), 100, 100, color, 'grad-acc');
  
  let html = `
    <div class="ft-panel">
      <div class="ft-header">
        <div>
          <div class="ft-title">SAÍDAS DA CONTA · ${label.toUpperCase()}</div>
          <div class="ft-amount">${money(total).replace(',','<span>,').replace('.','.')}</span></div>
        </div>
        ${trendHtml}
      </div>
      
      <div class="ft-chart-container" id="accChartTouch">
        ${svg}
        <div class="ft-chart-axis">
          <span>${buckets[0].label}</span>
          <span>${buckets[buckets.length-1].label}</span>
        </div>
        <div class="ft-chart-tooltip"></div>
        <div class="ft-chart-point" data-color="${color}"></div>
        <div class="ft-chart-touch"></div>
      </div>
      
      <div class="ft-cats">
        ${cats.map((c, i) => `
          <div class="ft-cat" style="animation-delay: ${i*60}ms">
            <div class="ft-cat-icon" style="background: ${c.color}22; color: ${c.color}; border: 1px solid ${c.color}44;">${spxEmoji(c.label)}</div>
            <div class="ft-cat-info">
              <div class="ft-cat-name">${safe(c.label)}</div>
              <div class="ft-cat-bar-wrap"><div class="ft-cat-bar" style="width: ${Math.max(4, c.pct)}%; background: ${c.color}; box-shadow: 0 0 8px ${c.color}aa;"></div></div>
            </div>
            <div class="ft-cat-val">
              <strong>${money(c.value)}</strong>
              <span>${c.pct}%</span>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
  
  wrap.innerHTML = html;
  if(el.accountFlowTotal) el.accountFlowTotal.textContent = money(total);
  if(el.accountFlowPeriodLabel) el.accountFlowPeriodLabel.textContent = label;
  
  setTimeout(() => attachChartInteraction('accChartTouch', coords, buckets.map(b => b.tip)), 50);
}
"""

new_credit_chart = """
function renderCreditDescChart(){
  syncCreditExpenseMonthPicker();
  const activeMonthKey = creditExpenseMonthKey();
  const activeMonthLabel = monthLabelFromKey(activeMonthKey);
  const breakdown = creditExpenseBreakdown(activeMonthKey);
  
  const catColors = ['#651fff','#d500f9','#f50057','#ff3d00','#ffea00','#00e5ff','#1de9b6'];
  const cats = compressBreakdown(buildCategoryBreakdown(
    breakdown.map(r => ({ value: r.value, label: r.label, key: r.label })),
    catColors, 'Sem categoria'
  ), 6, 'Outros');
  
  const total = cats.reduce((s,c) => s + c.value, 0);
  const wrap = el.ccDescLegend;
  if(!wrap) return;
  
  if(el.ccDescTotal) el.ccDescTotal.textContent = money(total);
  if(document.getElementById('ccDescMonth')) document.getElementById('ccDescMonth').textContent = `em ${activeMonthLabel}`;
  if(el.ccChartMonthTag) el.ccChartMonthTag.textContent = activeMonthLabel;
  if(el.ccDescChart) el.ccDescChart.style.display = 'none';
  
  if(!total) {
    wrap.innerHTML = `<div class="ft-panel"><div class="empty">Sem gastos classificados em ${safe(activeMonthLabel)}.</div></div>`;
    return;
  }
  
  let buckets = [];
  const color = '#b388ff';
  let chartHtml = '';
  
  if(activeMonthKey !== 'all' && st.credit && st.credit.tx) {
    const [y, m] = activeMonthKey.split('-');
    if(y && m) {
      const start = new Date(Number(y), Number(m)-1, 1);
      const end = new Date(Number(y), Number(m), 1);
      const inRange = st.credit.tx.filter(x => x.type === 'expense' && x.at >= start.toISOString() && x.at < end.toISOString());
      const daysInMonth = new Date(Number(y), Number(m), 0).getDate();
      for(let i=1; i<=daysInMonth; i++) {
        const d = new Date(Number(y), Number(m)-1, i);
        const dayTotal = inRange.filter(x => new Date(x.at).getDate() === i).reduce((s,x) => s + Number(x.value||0), 0);
        buckets.push({ val: dayTotal, tip: `${i}/${m}` });
      }
      
      const { svg, coords } = generateCurveSVG(buckets.map(b => b.val), 100, 100, color, 'grad-cc');
      
      chartHtml = `
        <div class="ft-chart-container" id="ccChartTouch">
          ${svg}
          <div class="ft-chart-axis">
            <span>1</span>
            <span>${daysInMonth}</span>
          </div>
          <div class="ft-chart-tooltip"></div>
          <div class="ft-chart-point" data-color="${color}"></div>
          <div class="ft-chart-touch"></div>
        </div>
      `;
      setTimeout(() => attachChartInteraction('ccChartTouch', coords, buckets.map(b => b.tip)), 50);
    }
  }

  let html = `
    <div class="ft-panel" style="background: linear-gradient(180deg, rgba(20,16,36,0.95), rgba(14,10,24,0.98)); border-color: rgba(179,136,255,0.15);">
      <div class="ft-header">
        <div>
          <div class="ft-title" style="color:#b388ff">GASTOS DO CARTÃO · ${activeMonthLabel.toUpperCase()}</div>
          <div class="ft-amount">${money(total).replace(',','<span>,').replace('.','.')}</span></div>
        </div>
      </div>
      
      ${chartHtml}
      
      <div class="ft-cats">
        ${cats.map((c, i) => `
          <div class="ft-cat" style="animation-delay: ${i*60}ms">
            <div class="ft-cat-icon" style="background: ${c.color}22; color: ${c.color}; border: 1px solid ${c.color}44;">${spxEmoji(c.label)}</div>
            <div class="ft-cat-info">
              <div class="ft-cat-name">${safe(c.label)}</div>
              <div class="ft-cat-bar-wrap"><div class="ft-cat-bar" style="width: ${Math.max(4, c.pct)}%; background: ${c.color}; box-shadow: 0 0 8px ${c.color}aa;"></div></div>
            </div>
            <div class="ft-cat-val">
              <strong>${money(c.value)}</strong>
              <span>${c.pct}%</span>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
  
  wrap.innerHTML = html;
}
"""

html = re.sub(r'function renderAccountFlowChart\(\)\{.*?(?=\nfunction |\Z)', new_account_flow + '\n', html, flags=re.DOTALL)
html = re.sub(r'function renderCreditDescChart\(\)\{.*?(?=\nfunction |\Z)', new_credit_chart + '\n', html, flags=re.DOTALL)

# Strip out old spx structural headers and keep only #accountFlowLegend
html = re.sub(r'<div class="spxHead">.*?<div id="accountFlowLegend"></div>\s*</div>', '<div id="accountFlowLegend"></div>', html, flags=re.DOTALL)
# It was actually <div class="spx"...
html = re.sub(r'<div class="spx".*?<div id="accountFlowLegend"></div>\s*</div>', '<div id="accountFlowLegend"></div>', html, flags=re.DOTALL)
# Try more relaxed substitution for the old spx if it's there
html = re.sub(r'<div class="spx[^>]*>.*?<div id="accountFlowLegend"></div>.*?</div>', '<div id="accountFlowLegend"></div>', html, flags=re.DOTALL)

pathlib.Path('d:/weedverso/app/index.html').write_text(html, encoding='utf-8')
