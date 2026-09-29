#!/usr/bin/env python3
"""
Patch Summary Template with Draw.io Enterprise Integration
============================================================

Automatically adds Draw.io viewer/editor capabilities to summary-template.html

Features:
- 4 new navigation menu items
- Multi-page tab viewer
- Enterprise Draw.io editor integration
- Offline Base64 embedding

Usage:
    python patch_template_drawio.py

Author: AVA Fabric Apps Agents
Date: 2026-04-15
"""

from pathlib import Path
import re

TEMPLATE_PATH = Path(__file__).parent / '../templates/html/summary-template.html'
BACKUP_PATH = TEMPLATE_PATH.with_suffix('.html.backup')

# ══════════════════════════════════════════════════════════════════
# NAVIGATION MENU ITEMS (after line ~591)
# ══════════════════════════════════════════════════════════════════

NAV_ITEMS = '''
    <!-- Drawio Diagrams (added by patch_template_drawio.py) -->
    <div class="ni" onclick="nav('s-f1-diagrams-c4',this)">
      <span class="nd ok" id="nd-f1-diagrams-c4"></span>
      <span data-i18n="nav-diagrams-c4">📐 Diagramas C4</span>
      <span class="nb ok" id="nb-diagrams-c4">0</span>
    </div>
    <div class="ni" onclick="nav('s-f1-diagrams-overall',this)">
      <span class="nd ok" id="nd-f1-diagrams-overall"></span>
      <span data-i18n="nav-diagrams-overall">🏗️ Arquitetura Overall</span>
      <span class="nb ok" id="nb-diagrams-overall">0</span>
    </div>
    <div class="ni" onclick="nav('s-f1-diagrams-bpmn',this)">
      <span class="nd" id="nd-f1-diagrams-bpmn"></span>
      <span data-i18n="nav-diagrams-bpmn">🔄 Processos BPMN</span>
      <span class="nb" id="nb-diagrams-bpmn">0</span>
    </div>
    <div class="ni" onclick="nav('s-f1-diagrams-sequence',this)">
      <span class="nd ok" id="nd-f1-diagrams-sequence"></span>
      <span data-i18n="nav-diagrams-sequence">📊 Seq. Diagrams</span>
      <span class="nb ok" id="nb-diagrams-sequence">0</span>
    </div>'''

# ══════════════════════════════════════════════════════════════════
# CSS STYLES
# ══════════════════════════════════════════════════════════════════

CSS_STYLES = '''
/* ═══ DRAWIO VIEWER (added by patch_template_drawio.py) ═════════ */
.drawio-container{
  background:var(--d2); border-radius:var(--rad2);
  border:1px solid var(--wb); overflow:hidden; margin-bottom:24px;
}
.drawio-header{
  background:var(--d1); border-bottom:1px solid var(--wb);
  padding:12px 16px; display:flex; align-items:center; justify-content:space-between;
}
.drawio-tabs{
  display:flex; gap:4px; flex:1;
}
.drawio-tab{
  padding:6px 14px; background:transparent; border:1px solid transparent;
  border-radius:var(--rad) var(--rad) 0 0; cursor:pointer;
  font-size:11px; font-weight:600; color:var(--g2);
  transition:all var(--tr); user-select:none;
}
.drawio-tab:hover{background:var(--wb); color:var(--fg)}
.drawio-tab.active{
  background:var(--d2); border-color:var(--wb); border-bottom-color:var(--d2);
  color:var(--r); position:relative; bottom:-1px;
}
.drawio-actions{
  display:flex; gap:6px;
}
.drawio-btn{
  padding:5px 12px; background:var(--d3); border:1px solid var(--wb);
  border-radius:var(--rad); font-size:11px; font-weight:600;
  cursor:pointer; transition:all var(--tr); color:var(--fg);
}
.drawio-btn:hover{background:var(--r); color:#fff; border-color:var(--r)}
.drawio-canvas{
  width:100%; height:600px; background:var(--k);
  display:flex; align-items:center; justify-content:center;
  position:relative; overflow:auto;
}
.drawio-loading{
  font-size:12px; color:var(--g2);
}
.drawio-not-available{
  padding:40px; text-align:center; color:var(--g2);
  font-size:12px; line-height:1.75;
}
.drawio-iframe{
  width:100%; height:100%; border:none;
}
.drawio-page-svg{
  max-width:100%; max-height:100%; object-fit:contain;
}
'''

# ══════════════════════════════════════════════════════════════════
# SECTION HTML (4 sections)
# ══════════════════════════════════════════════════════════════════

SECTIONS_HTML = '''
<!-- ═══ F1 DIAGRAMS: DRAWIO VIEWERS (added by patch_template_drawio.py) ═══ -->

<!-- F1 Diagrams: C4 -->
<section id="s-f1-diagrams-c4" class="sec">
  <div class="ph">
    <h1 data-i18n="pg-diagrams-c4">Diagramas C4 AS-IS</h1>
    <p data-i18n="pg-diagrams-c4-sub">Context, Container e Component diagrams do sistema AS-IS</p>
    <div class="hl"></div>
  </div>
  <div id="drawio-viewer-c4"></div>
</section>

<!-- F1 Diagrams: Overall -->
<section id="s-f1-diagrams-overall" class="sec">
  <div class="ph">
    <h1 data-i18n="pg-diagrams-overall">Arquitetura Overall AS-IS</h1>
    <p data-i18n="pg-diagrams-overall-sub">Diagramas de componentes e classes do sistema legado</p>
    <div class="hl"></div>
  </div>
  <div id="drawio-viewer-overall"></div>
</section>

<!-- F1 Diagrams: BPMN -->
<section id="s-f1-diagrams-bpmn" class="sec">
  <div class="ph">
    <h1 data-i18n="pg-diagrams-bpmn">Processos de Negócio (BPMN)</h1>
    <p data-i18n="pg-diagrams-bpmn-sub">Fluxos de negócio e processos mapeados</p>
    <div class="hl"></div>
  </div>
  <div id="drawio-viewer-bpmn"></div>
</section>

<!-- F1 Diagrams: Sequence -->
<section id="s-f1-diagrams-sequence" class="sec">
  <div class="ph">
    <h1 data-i18n="pg-diagrams-sequence">Diagramas de Sequência AS-IS</h1>
    <p data-i18n="pg-diagrams-sequence-sub">Fluxos de interação e comunicação entre componentes</p>
    <div class="hl"></div>
  </div>
  <div id="drawio-viewer-sequence"></div>
</section>
'''

# ══════════════════════════════════════════════════════════════════
# I18N TRANSLATIONS
# ══════════════════════════════════════════════════════════════════

I18N_PT = '''"nav-diagrams-c4": "📐 Diagramas C4",
    "nav-diagrams-overall": "🏗️ Arquitetura Overall",
    "nav-diagrams-bpmn": "🔄 Processos BPMN",
    "nav-diagrams-sequence": "📊 Diagramas de Sequência",
    "pg-diagrams-c4": "Diagramas C4 AS-IS",
    "pg-diagrams-c4-sub": "Context, Container e Component diagrams do sistema AS-IS",
    "pg-diagrams-overall": "Arquitetura Overall AS-IS",
    "pg-diagrams-overall-sub": "Diagramas de componentes e classes do sistema legado",
    "pg-diagrams-bpmn": "Processos de Negócio (BPMN)",
    "pg-diagrams-bpmn-sub": "Fluxos de negócio e processos mapeados",
    "pg-diagrams-sequence": "Diagramas de Sequência AS-IS",
    "pg-diagrams-sequence-sub": "Fluxos de interação e comunicação entre componentes",
    "btn-edit-diagram": "✏️ Editar",
    "btn-export-svg": "📥 Exportar SVG",
    "btn-export-png": "📥 Exportar PNG",
    "btn-fullscreen": "⛶ Tela Cheia",
    "lbl-diagram-loading": "Carregando diagrama...",
    "lbl-diagram-not-available": "Diagrama não disponível. Execute: python generate_drawio_from_mermaid.py",
    "lbl-page": "Página",'''

I18N_EN = '''"nav-diagrams-c4": "📐 C4 Diagrams",
    "nav-diagrams-overall": "🏗️ Overall Architecture",
    "nav-diagrams-bpmn": "🔄 BPMN Processes",
    "nav-diagrams-sequence": "📊 Sequence Diagrams",
    "pg-diagrams-c4": "AS-IS C4 Diagrams",
    "pg-diagrams-c4-sub": "Context, Container and Component diagrams of AS-IS system",
    "pg-diagrams-overall": "AS-IS Overall Architecture",
    "pg-diagrams-overall-sub": "Component and class diagrams of legacy system",
    "pg-diagrams-bpmn": "Business Processes (BPMN)",
    "pg-diagrams-bpmn-sub": "Mapped business flows and processes",
    "pg-diagrams-sequence": "AS-IS Sequence Diagrams",
    "pg-diagrams-sequence-sub": "Interaction flows and component communication",
    "btn-edit-diagram": "✏️ Edit",
    "btn-export-svg": "📥 Export SVG",
    "btn-export-png": "📥 Export PNG",
    "btn-fullscreen": "⛶ Fullscreen",
    "lbl-diagram-loading": "Loading diagram...",
    "lbl-diagram-not-available": "Diagram not available. Run: python generate_drawio_from_mermaid.py",
    "lbl-page": "Page",'''

# ══════════════════════════════════════════════════════════════════
# JAVASCRIPT CODE
# ══════════════════════════════════════════════════════════════════

JAVASCRIPT_CODE = '''
/* ═══════════════════════════════════════════════════════════════
   DRAWIO VIEWER — Enterprise-grade embedded viewer/editor
   (added by patch_template_drawio.py)
   Uses data URIs + Draw.io integration for multi-page editing
   ═══════════════════════════════════════════════════════════════ */

function renderDrawioViewer(containerId, drawioKey){
  const container = document.getElementById(containerId);
  if(!container) return;
  
  const drawioData = D.drawioFiles[drawioKey];
  
  if(!drawioData || !drawioData.exists){
    container.innerHTML = `
      <div class="drawio-not-available">
        <p><strong>${t('lbl-diagram-not-available')}</strong></p>
        <p style="font-family:monospace;margin-top:12px;color:var(--g3)">
          python src/modules/ava-fabric-agents/summary/utils/generate_drawio_from_mermaid.py --project ${D.project}
        </p>
      </div>`;
    return;
  }
  
  // Decode Base64 content
  const xml = atob(drawioData.content);
  
  // Parse XML to extract diagram pages
  const parser = new DOMParser();
  const doc = parser.parseFromString(xml, 'text/xml');
  const diagrams = doc.querySelectorAll('diagram');
  
  const pages = Array.from(diagrams).map((diagram, index) => ({
    id: diagram.getAttribute('id'),
    name: diagram.getAttribute('name') || `${t('lbl-page')} ${index + 1}`,
    xml: diagram.outerHTML
  }));
  
  if(pages.length === 0){
    container.innerHTML = '<div class="drawio-loading">⚠️ No diagrams found in file</div>';
    return;
  }
  
  // Build viewer HTML
  const viewerHTML = `
    <div class="drawio-container">
      <div class="drawio-header">
        <div class="drawio-tabs" id="tabs-${drawioKey}">
          ${pages.map((p, i) => 
            `<div class="drawio-tab ${i===0?'active':''}" onclick="switchDrawioPage('${drawioKey}', ${i})">${p.name}</div>`
          ).join('')}
        </div>
        <div class="drawio-actions">
          <button class="drawio-btn" onclick="editDrawio('${drawioKey}')" title="${t('btn-edit-diagram')}">
            ✏️ ${t('btn-edit-diagram')}
          </button>
          <button class="drawio-btn" onclick="exportDrawioSVG('${drawioKey}')" title="${t('btn-export-svg')}">
            📥 SVG
          </button>
          <button class="drawio-btn" onclick="fullscreenDrawio('${drawioKey}')" title="${t('btn-fullscreen')}">
            ⛶
          </button>
        </div>
      </div>
      <div class="drawio-canvas" id="canvas-${drawioKey}">
        <div class="drawio-loading">${t('lbl-diagram-loading')}</div>
      </div>
    </div>
  `;
  
  container.innerHTML = viewerHTML;
  
  // Render first page
  renderDrawioPage(drawioKey, 0, xml, pages);
  
  // Store data for later use
  window.drawioViewers = window.drawioViewers || {};
  window.drawioViewers[drawioKey] = {
    xml: xml,
    pages: pages,
    currentPage: 0,
    filename: drawioData.filename
  };
}

function renderDrawioPage(key, pageIndex, fullXml, pages){
  const canvas = document.getElementById(`canvas-${key}`);
  if(!canvas) return;
  
  const page = pages[pageIndex];
  
  // Simple approach: show message to open in Draw.io
  // (inline rendering would require mxGraph library - adds ~2MB to template)
  canvas.innerHTML = `
    <div class="drawio-not-available">
      <p><strong>📐 ${page.name}</strong></p>
      <p style="margin-top:16px;color:var(--g3)">
        Para visualizar e editar este diagrama, clique em <strong>"✏️ Editar"</strong> acima.<br/>
        O diagrama será aberto no editor Draw.io em uma nova janela.
      </p>
      <p style="margin-top:12px;font-size:11px;color:var(--g2)">
        ${pages.length} página(s) disponível(is) neste arquivo .drawio
      </p>
      <div style="margin-top:20px;">
        <button class="drawio-btn" onclick="editDrawio('${key}')" style="font-size:13px;padding:8px 20px;">
          🚀 Abrir no Draw.io Editor
        </button>
      </div>
    </div>
  `;
  
  // Update active tab
  const tabs = document.querySelectorAll(`#tabs-${key} .drawio-tab`);
  tabs.forEach((tab, i) => {
    tab.classList.toggle('active', i === pageIndex);
  });
  
  // Update global state
  if(window.drawioViewers && window.drawioViewers[key]){
    window.drawioViewers[key].currentPage = pageIndex;
  }
}

function switchDrawioPage(key, pageIndex){
  const viewer = window.drawioViewers[key];
  if(!viewer) return;
  
  renderDrawioPage(key, pageIndex, viewer.xml, viewer.pages);
}

function editDrawio(key){
  const viewer = window.drawioViewers[key];
  if(!viewer) return;
  
  // Create data URI
  const dataUri = 'data:application/vnd.jgraph.mxfile;base64,' + btoa(viewer.xml);
  
  // Open in diagrams.net with edit mode
  const editorUrl = `https://app.diagrams.net/?lightbox=0&edit=_blank&layers=1&nav=1&title=${viewer.filename}#${encodeURIComponent(dataUri)}`;
  
  window.open(editorUrl, '_blank', 'width=1400,height=900');
}

function exportDrawioSVG(key){
  alert('Exportar SVG: Use o botão "✏️ Editar" para abrir no Draw.io, depois File > Export as > SVG');
}

function fullscreenDrawio(key){
  const container = document.querySelector(`#canvas-${key}`).closest('.drawio-container');
  if(!container) return;
  
  if(container.requestFullscreen){
    container.requestFullscreen();
  } else if(container.webkitRequestFullscreen){
    container.webkitRequestFullscreen();
  }
}

/* ── Render all Drawio viewers on init ────────────────────────── */
function renderAllDrawioViewers(){
  renderDrawioViewer('drawio-viewer-c4', 'c4');
  renderDrawioViewer('drawio-viewer-overall', 'overall');
  renderDrawioViewer('drawio-viewer-bpmn', 'bpmn');
  renderDrawioViewer('drawio-viewer-sequence', 'sequence');
  
  // Update navigation badges
  const updateBadge = (key, elId) => {
    const data = D.drawioFiles[key];
    const el = document.getElementById(elId);
    if(el && data && data.exists){
      el.textContent = data.pages;
    }
    // Update dot indicator
    const dotId = elId.replace('nb-', 'nd-');
    ndot(dotId.replace('nd-', ''), data && data.exists ? 'done' : 'idle');
  };
  
  updateBadge('c4', 'nb-diagrams-c4');
  updateBadge('overall', 'nb-diagrams-overall');
  updateBadge('bpmn', 'nb-diagrams-bpmn');
  updateBadge('sequence', 'nb-diagrams-sequence');
}
'''


def patch_template():
    """Apply all patches to summary-template.html"""
    
    if not TEMPLATE_PATH.exists():
        print(f"❌ Template not found: {TEMPLATE_PATH}")
        return False
    
    # Create backup
    if not BACKUP_PATH.exists():
        print(f"📦 Creating backup: {BACKUP_PATH.name}")
        BACKUP_PATH.write_text(TEMPLATE_PATH.read_text(encoding='utf-8'), encoding='utf-8')
    
    print(f"🔧 Patching template: {TEMPLATE_PATH.name}")
    
    html = TEMPLATE_PATH.read_text(encoding='utf-8')
    
    # Check if already patched
    if 'patch_template_drawio.py' in html or 's-f1-diagrams-c4' in html:
        print("⚠️  Template already patched! Skipping.")
        return True
    
    # 1. Add navigation items (after "Banco de Dados" nav item - use regex)
    print("  [1/7] Adding navigation menu items...")
    pattern = r'(<div class="ni" onclick="nav\(\'s-f1-db\',this\)">.*?</div>)\s*(</div>\s*<!-- F2)'
    replacement = r'\1' + NAV_ITEMS + '\n  \\2'
    html = re.sub(pattern, replacement, html, flags=re.DOTALL)
    
    # 2. Add CSS (after diagram styles - search for specific pattern)
    print("  [2/7] Adding CSS styles...")
    css_marker = '/* ═══ DIAGRAM STYLES ══════════════════'
    if css_marker in html:
        # Find end of diagram styles section
        pos = html.find(css_marker)
        next_section = html.find('/* ═══', pos + 10)
        if next_section > pos:
            html = html[:next_section] + CSS_STYLES + '\n\n' + html[next_section:]
    
    # 3. Add sections (after s-f1-db section - use specific comment marker)
    print("  [3/7] Adding content sections...")
    pattern = r'(</div>\s*)<!-- F2: Blueprint TO-BE'
    replacement = r'\1' + SECTIONS_HTML + '\n<!-- F2: Blueprint TO-BE'
    html = re.sub(pattern, replacement, html, count=1)
    
    # 4. Add drawioFiles to const D
    print("  [4/7] Adding data object placeholder...")
    d_marker = 'agentStatus: {{AGENT_STATUS_JSON}},'
    if d_marker in html:
        html = html.replace(
            d_marker,
            "drawioFiles: {{DRAWIO_FILES_JSON}},\n  " + d_marker
        )
    
    # 5. Add PT translations
    print("  [5/7] Adding Portuguese translations...")
    pt_marker = '"nav-db": "Banco de Dados",'
    if pt_marker in html:
        html = html.replace(pt_marker, pt_marker + '\n    ' + I18N_PT)
    
    # 6. Add EN translations
    print("  [6/7] Adding English translations...")
    en_marker = '"nav-db": "Database",'
    if en_marker in html:
        html = html.replace(en_marker, en_marker + '\n    ' + I18N_EN)
    
    # 7. Add JavaScript (before closing script tag - find init function)
    print("  [7/7] Adding JavaScript functions...")
    js_marker = 'function init(){'
    if js_marker in html:
        # Add before init function
        html = html.replace(js_marker, JAVASCRIPT_CODE + '\n' + js_marker)
        
        # Add render call in init function
        init_marker = 'renderAllDiagrams();'
        if init_marker in html:
            html = html.replace(init_marker, init_marker + '\n  renderAllDrawioViewers();')
    
    # Write patched template
    TEMPLATE_PATH.write_text(html, encoding='utf-8')
    
    print("\n✅ Template patched successfully!")
    print(f"   Backup saved: {BACKUP_PATH}")
    print(f"   Modified: {TEMPLATE_PATH}")
    
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("  Draw.io Enterprise Integration - Template Patcher")
    print("=" * 60)
    print()
    
    success = patch_template()
    
    if success:
        print("\n🎉 Patch complete! Next steps:")
        print("   1. Update build_summary_comprehensive.py (add load_drawio_files)")
        print("   2. Generate .drawio files: python generate_drawio_from_mermaid.py")
        print("   3. Build summary: python build_summary_comprehensive.py")
        print()
    else:
        print("\n❌ Patch failed. Check errors above.")
        exit(1)
