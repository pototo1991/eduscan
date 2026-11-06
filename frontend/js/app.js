/**
 * EduScan - Lógica de Aplicación Frontend (Vanilla JS)
 * ====================================================
 */

document.addEventListener('DOMContentLoaded', () => {
  // Estado Global
  const state = {
    q: '',
    region: 'todas',
    comuna: 'todas',
    dependencia: 'todas',
    grado: '4b',
    anio: 2024,
    page: 1,
    limit: 24,
    total: 0,
    allComunas: [],
    comparedRBDs: JSON.parse(sessionStorage.getItem('eduscan_compare') || '[]'),
    chartHistoricoInstance: null,
    chartComparatorInstance: null
  };

  // Elementos del DOM
  const dom = {
    statColegios: document.getElementById('stat-colegios'),
    statEvaluaciones: document.getElementById('stat-evaluaciones'),
    statComunas: document.getElementById('stat-comunas'),
    searchInput: document.getElementById('search-input'),
    btnSearch: document.getElementById('btn-search-trigger'),
    filterRegion: document.getElementById('filter-region'),
    filterComuna: document.getElementById('filter-comuna'),
    filterDependencia: document.getElementById('filter-dependencia'),
    filterGrado: document.getElementById('filter-grado'),
    filterAnio: document.getElementById('filter-anio'),
    resultsCountText: document.getElementById('results-count-text'),
    schoolsGrid: document.getElementById('schools-grid'),
    paginationWrapper: document.getElementById('pagination-wrapper'),
    btnPrevPage: document.getElementById('btn-prev-page'),
    btnNextPage: document.getElementById('btn-next-page'),
    pageIndicator: document.getElementById('page-indicator'),
    
    // Comparador Dock
    compareDock: document.getElementById('compare-dock'),
    dockCompareCount: document.getElementById('dock-compare-count'),
    navCompareCount: document.getElementById('nav-compare-count'),
    btnOpenCompareNav: document.getElementById('btn-open-compare-nav'),
    btnLaunchCompare: document.getElementById('btn-launch-compare'),
    btnClearCompare: document.getElementById('btn-clear-compare'),

    // Modal Detalle
    modalDetail: document.getElementById('modal-school-detail'),
    btnCloseDetail: document.getElementById('btn-close-detail'),
    modalDepBadge: document.getElementById('modal-dep-badge'),
    modalRbdChip: document.getElementById('modal-rbd-chip'),
    modalSchoolName: document.getElementById('modal-school-name'),
    modalSchoolLocation: document.getElementById('modal-school-location'),
    kpiLectura: document.getElementById('kpi-lectura'),
    kpiMatematica: document.getElementById('kpi-matematica'),
    kpiNse: document.getElementById('kpi-nse'),
    kpiSubLectura: document.getElementById('kpi-sub-lectura'),
    kpiSubMatematica: document.getElementById('kpi-sub-matematica'),
    edaLecturaPct: document.getElementById('eda-lectura-pct'),
    edaMatePct: document.getElementById('eda-mate-pct'),
    edaBarLectura: document.getElementById('eda-bar-lectura'),
    edaBarMatematica: document.getElementById('eda-bar-matematica'),
    chartHistoricoCanvas: document.getElementById('chart-historico'),

    // Modal Comparador
    modalComparator: document.getElementById('modal-comparator'),
    btnCloseCompare: document.getElementById('btn-close-compare'),
    chartComparatorCanvas: document.getElementById('chart-comparator'),
    compareTableHead: document.getElementById('compare-table-head'),
    compareTableBody: document.getElementById('compare-table-body')
  };

  // 1. Cargar Estadísticas Globales
  async function loadStats() {
    try {
      const res = await fetch('/api/stats');
      const data = await res.json();
      dom.statColegios.textContent = Number(data.total_establecimientos).toLocaleString('es-CL');
      dom.statEvaluaciones.textContent = Number(data.total_evaluaciones).toLocaleString('es-CL');
      dom.statComunas.textContent = Number(data.total_comunas).toLocaleString('es-CL');
    } catch (err) {
      console.error('Error cargando estadísticas:', err);
    }
  }

  // 2. Cargar Opciones de Filtros
  async function loadFiltros() {
    try {
      const res = await fetch('/api/filtros');
      const data = await res.json();
      state.allComunas = data.comunas || [];

      // Regiones
      data.regiones.forEach(r => {
        const opt = document.createElement('option');
        opt.value = r.nombre;
        opt.textContent = r.nombre;
        dom.filterRegion.appendChild(opt);
      });

      // Comunas
      populateComunas(state.allComunas);

      // Dependencias
      data.dependencias.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d;
        opt.textContent = d;
        dom.filterDependencia.appendChild(opt);
      });
    } catch (err) {
      console.error('Error cargando filtros:', err);
    }
  }

  function populateComunas(comunasList) {
    dom.filterComuna.innerHTML = '<option value="todas">Todas las comunas</option>';
    comunasList.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.nombre;
      opt.textContent = c.nombre;
      dom.filterComuna.appendChild(opt);
    });
  }

  // Filtrado en cascada Región -> Comuna
  dom.filterRegion.addEventListener('change', () => {
    state.region = dom.filterRegion.value;
    state.page = 1;
    if (state.region === 'todas') {
      populateComunas(state.allComunas);
    } else {
      const filtered = state.allComunas.filter(c => c.region === state.region);
      populateComunas(filtered);
    }
    state.comuna = 'todas';
    searchSchools();
  });

  dom.filterComuna.addEventListener('change', () => {
    state.comuna = dom.filterComuna.value;
    state.page = 1;
    searchSchools();
  });

  dom.filterDependencia.addEventListener('change', () => {
    state.dependencia = dom.filterDependencia.value;
    state.page = 1;
    searchSchools();
  });

  dom.filterGrado.addEventListener('change', () => {
    state.grado = dom.filterGrado.value;
    state.page = 1;
    searchSchools();
  });

  dom.filterAnio.addEventListener('change', () => {
    state.anio = parseInt(dom.filterAnio.value, 10);
    state.page = 1;
    searchSchools();
  });

  // Buscador de texto con Debounce
  let searchTimeout = null;
  dom.searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.q = e.target.value.trim();
      state.page = 1;
      searchSchools();
    }, 350);
  });

  dom.btnSearch.addEventListener('click', () => {
    state.q = dom.searchInput.value.trim();
    state.page = 1;
    searchSchools();
  });

  dom.searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      state.q = dom.searchInput.value.trim();
      state.page = 1;
      searchSchools();
    }
  });

  // 3. Buscar y Renderizar Colegios
  async function searchSchools() {
    dom.schoolsGrid.innerHTML = `
      <div class="loading-spinner" style="grid-column: 1 / -1;">
        <div class="spinner"></div>
        <span>Buscando colegios...</span>
      </div>
    `;

    const offset = (state.page - 1) * state.limit;
    const params = new URLSearchParams({
      grado: state.grado,
      anio: state.anio,
      limit: state.limit,
      offset: offset
    });

    if (state.q) params.set('q', state.q);
    if (state.region !== 'todas') params.set('region', state.region);
    if (state.comuna !== 'todas') params.set('comuna', state.comuna);
    if (state.dependencia !== 'todas') params.set('dependencia', state.dependencia);

    try {
      const res = await fetch(`/api/colegios?${params.toString()}`);
      const data = await res.json();
      state.total = data.total;
      renderSchools(data.resultados);
      updatePagination();
    } catch (err) {
      dom.schoolsGrid.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <h3>Error al conectar con la base de datos</h3>
          <p>Verifica que el contenedor en knossos esté en ejecución.</p>
        </div>
      `;
    }
  }

  function getDependenciaClass(dep) {
    if (!dep) return 'dep-Municipal';
    const clean = dep.toLowerCase();
    if (clean.includes('slep')) return 'dep-SLEP';
    if (clean.includes('subvencionado')) return 'dep-Subvencionado';
    if (clean.includes('pagado')) return 'dep-Pagado';
    if (clean.includes('delegada')) return 'dep-Delegada';
    return 'dep-Municipal';
  }

  function renderSchools(schools) {
    if (!schools || schools.length === 0) {
      dom.resultsCountText.innerHTML = `No se encontraron colegios coincidentes.`;
      dom.schoolsGrid.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <h3>Sin resultados</h3>
          <p>Prueba ajustando los filtros o utilizando otros términos de búsqueda.</p>
        </div>
      `;
      dom.paginationWrapper.style.display = 'none';
      return;
    }

    const start = (state.page - 1) * state.limit + 1;
    const end = Math.min(start + schools.length - 1, state.total);
    dom.resultsCountText.innerHTML = `Mostrando <strong>${start} - ${end}</strong> de <strong>${Number(state.total).toLocaleString('es-CL')}</strong> establecimientos`;

    dom.schoolsGrid.innerHTML = '';
    schools.forEach(school => {
      const isCompared = state.comparedRBDs.includes(school.rbd);
      const ev = school.evaluacion;

      let scoresHtml = '';
      if (ev && (ev.puntaje_lectura || ev.puntaje_matematica)) {
        // Cálculo de diferencia con la comuna
        let difLectHtml = '';
        if (ev.puntaje_lectura && ev.comuna_promedio_lectura) {
          const dif = Math.round(ev.puntaje_lectura - ev.comuna_promedio_lectura);
          const cls = dif >= 0 ? 'diff-positive' : 'diff-negative';
          difLectHtml = `<span class="diff-badge ${cls}">${dif >= 0 ? '+' : ''}${dif} com.</span>`;
        }

        let difMateHtml = '';
        if (ev.puntaje_matematica && ev.comuna_promedio_matematica) {
          const dif = Math.round(ev.puntaje_matematica - ev.comuna_promedio_matematica);
          const cls = dif >= 0 ? 'diff-positive' : 'diff-negative';
          difMateHtml = `<span class="diff-badge ${cls}">${dif >= 0 ? '+' : ''}${dif} com.</span>`;
        }

        scoresHtml = `
          <div class="card-scores-row">
            <div class="score-box">
              <span class="score-label">Lectura</span>
              <div class="score-val-wrap">
                <span class="score-val">${ev.puntaje_lectura ? Math.round(ev.puntaje_lectura) : 'S/I'}</span>
                ${difLectHtml}
              </div>
            </div>
            <div class="score-box">
              <span class="score-label">Matemática</span>
              <div class="score-val-wrap">
                <span class="score-val">${ev.puntaje_matematica ? Math.round(ev.puntaje_matematica) : 'S/I'}</span>
                ${difMateHtml}
              </div>
            </div>
          </div>
        `;
      } else {
        scoresHtml = `
          <div class="no-scores-msg">
            Puntaje no reportado para ${state.grado.toUpperCase()} (${state.anio})
          </div>
        `;
      }

      const card = document.createElement('div');
      card.className = 'school-card';
      card.innerHTML = `
        <div class="card-top">
          <div class="badge-row">
            <span class="dep-badge ${getDependenciaClass(school.dependencia)}">${school.dependencia || 'Sin clasificar'}</span>
            <span class="rbd-chip">RBD: ${school.rbd}</span>
          </div>
          <h3 class="card-title">${school.nombre}</h3>
          <div class="card-location">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
              <circle cx="12" cy="10" r="3"></circle>
            </svg>
            <span>${school.comuna}, ${school.region}</span>
          </div>
        </div>

        <div>
          ${scoresHtml}
          <div class="card-actions">
            <button class="btn-card-detail" data-rbd="${school.rbd}">Ver Ficha Escolar</button>
            <button class="btn-card-compare ${isCompared ? 'active' : ''}" data-rbd="${school.rbd}" title="Comparar este colegio">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/>
              </svg>
            </button>
          </div>
        </div>
      `;

      // Eventos de botones de la tarjeta
      card.querySelector('.btn-card-detail').addEventListener('click', () => openDetailModal(school.rbd));
      const btnComp = card.querySelector('.btn-card-compare');
      btnComp.addEventListener('click', () => toggleCompare(school.rbd, btnComp));

      dom.schoolsGrid.appendChild(card);
    });
  }

  function updatePagination() {
    const totalPages = Math.ceil(state.total / state.limit);
    if (totalPages <= 1) {
      dom.paginationWrapper.style.display = 'none';
      return;
    }
    dom.paginationWrapper.style.display = 'flex';
    dom.btnPrevPage.disabled = state.page <= 1;
    dom.btnNextPage.disabled = state.page >= totalPages;
    dom.pageIndicator.textContent = `Página ${state.page} de ${totalPages}`;
  }

  dom.btnPrevPage.addEventListener('click', () => {
    if (state.page > 1) {
      state.page--;
      searchSchools();
      window.scrollTo({ top: 350, behavior: 'smooth' });
    }
  });

  dom.btnNextPage.addEventListener('click', () => {
    state.page++;
    searchSchools();
    window.scrollTo({ top: 350, behavior: 'smooth' });
  });

  // 4. Comparador y Dock Flotante
  function toggleCompare(rbd, btnElement) {
    const idx = state.comparedRBDs.indexOf(rbd);
    if (idx > -1) {
      state.comparedRBDs.splice(idx, 1);
      if (btnElement) btnElement.classList.remove('active');
    } else {
      if (state.comparedRBDs.length >= 3) {
        alert('Puedes comparar hasta un máximo de 3 colegios a la vez.');
        return;
      }
      state.comparedRBDs.push(rbd);
      if (btnElement) btnElement.classList.add('active');
    }
    sessionStorage.setItem('eduscan_compare', JSON.stringify(state.comparedRBDs));
    updateCompareDock();
  }

  function updateCompareDock() {
    const count = state.comparedRBDs.length;
    dom.dockCompareCount.textContent = count;
    dom.navCompareCount.textContent = count;
    if (count > 0) {
      dom.compareDock.classList.add('visible');
    } else {
      dom.compareDock.classList.remove('visible');
    }
  }

  dom.btnClearCompare.addEventListener('click', () => {
    state.comparedRBDs = [];
    sessionStorage.setItem('eduscan_compare', '[]');
    updateCompareDock();
    document.querySelectorAll('.btn-card-compare.active').forEach(b => b.classList.remove('active'));
  });

  dom.btnOpenCompareNav.addEventListener('click', () => {
    if (state.comparedRBDs.length === 0) {
      alert('Selecciona al menos 1 colegio con el botón de comparación en su tarjeta.');
      return;
    }
    openComparatorModal();
  });

  dom.btnLaunchCompare.addEventListener('click', openComparatorModal);

  // 5. Modal de Detalle (Ficha Escolar Inteligente)
  async function openDetailModal(rbd) {
    dom.modalSchoolName.textContent = 'Cargando información...';
    dom.modalOverlay = dom.modalDetail;
    dom.modalDetail.classList.add('active');

    try {
      const res = await fetch(`/api/colegios/${rbd}`);
      if (!res.ok) throw new Error('No se pudo cargar el colegio');
      const data = await res.json();
      renderDetailModal(data);
    } catch (err) {
      alert('Error al cargar la ficha del establecimiento.');
      dom.modalDetail.classList.remove('active');
    }
  }

  function renderDetailModal(data) {
    const est = data.establecimiento;
    dom.modalSchoolName.textContent = est.nombre;
    dom.modalRbdChip.textContent = `RBD: ${est.rbd}`;
    dom.modalDepBadge.textContent = est.dependencia;
    dom.modalDepBadge.className = `dep-badge ${getDependenciaClass(est.dependencia)}`;
    dom.modalSchoolLocation.textContent = `${est.comuna}, ${est.provincia}, ${est.region}`;

    // Buscar la evaluación del grado y año activos (o la más reciente)
    const activeEval = data.historial_simce.find(e => e.anio === state.anio && e.grado === state.grado) 
                      || data.historial_simce[data.historial_simce.length - 1];

    if (activeEval) {
      dom.kpiLectura.textContent = activeEval.puntaje_lectura ? Math.round(activeEval.puntaje_lectura) : 'S/I';
      dom.kpiMatematica.textContent = activeEval.puntaje_matematica ? Math.round(activeEval.puntaje_matematica) : 'S/I';
      dom.kpiNse.textContent = activeEval.grupo_nse ? `Grupo ${activeEval.grupo_nse}` : 'No clasificado';

      // Benchmark comunal
      const comBench = data.benchmarks_comunales.find(c => c.anio === activeEval.anio && c.grado === activeEval.grado);
      if (comBench) {
        if (activeEval.puntaje_lectura && comBench.promedio_lectura) {
          const dif = Math.round(activeEval.puntaje_lectura - comBench.promedio_lectura);
          dom.kpiSubLectura.textContent = `${dif >= 0 ? '+' : ''}${dif} pts vs comuna (${Math.round(comBench.promedio_lectura)})`;
          dom.kpiSubLectura.style.color = dif >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)';
        }
        if (activeEval.puntaje_matematica && comBench.promedio_matematica) {
          const dif = Math.round(activeEval.puntaje_matematica - comBench.promedio_matematica);
          dom.kpiSubMatematica.textContent = `${dif >= 0 ? '+' : ''}${dif} pts vs comuna (${Math.round(comBench.promedio_matematica)})`;
          dom.kpiSubMatematica.style.color = dif >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)';
        }
      }

      // Estándares de Aprendizaje (EDA)
      renderEdaBars(activeEval);
    } else {
      dom.kpiLectura.textContent = 'S/I';
      dom.kpiMatematica.textContent = 'S/I';
      dom.kpiNse.textContent = '-';
    }

    // Gráfico de Evolución Histórica
    renderHistoricalChart(data.historial_simce, data.benchmarks_comunales);
  }

  function renderEdaBars(evalObj) {
    // Lectura
    const insL = evalObj.pct_insuficiente_lectura || 0;
    const eleL = evalObj.pct_elemental_lectura || 0;
    const adeL = evalObj.pct_adecuado_lectura || 0;
    dom.edaLecturaPct.textContent = `${adeL}% Adecuado / ${eleL}% Elemental / ${insL}% Insuf.`;
    dom.edaBarLectura.innerHTML = `
      <div class="bar-ins" style="width: ${insL}%" title="Insuficiente: ${insL}%"></div>
      <div class="bar-ele" style="width: ${eleL}%" title="Elemental: ${eleL}%"></div>
      <div class="bar-ade" style="width: ${adeL}%" title="Adecuado: ${adeL}%"></div>
    `;

    // Matemática
    const insM = evalObj.pct_insuficiente_matematica || 0;
    const eleM = evalObj.pct_elemental_matematica || 0;
    const adeM = evalObj.pct_adecuado_matematica || 0;
    dom.edaMatePct.textContent = `${adeM}% Adecuado / ${eleM}% Elemental / ${insM}% Insuf.`;
    dom.edaBarMatematica.innerHTML = `
      <div class="bar-ins" style="width: ${insM}%" title="Insuficiente: ${insM}%"></div>
      <div class="bar-ele" style="width: ${eleM}%" title="Elemental: ${eleM}%"></div>
      <div class="bar-ade" style="width: ${adeM}%" title="Adecuado: ${adeM}%"></div>
    `;
  }

  function renderHistoricalChart(evals, comunales) {
    if (state.chartHistoricoInstance) {
      state.chartHistoricoInstance.destroy();
    }

    // Filtrar evaluaciones por el grado seleccionado para que la serie sea coherente
    const evalsGrado = evals.filter(e => e.grado === state.grado);
    const labels = evalsGrado.map(e => `${e.anio} (${e.grado.toUpperCase()})`);
    const dataLectura = evalsGrado.map(e => e.puntaje_lectura);
    const dataMate = evalsGrado.map(e => e.puntaje_matematica);

    // Mapear promedio comunal para esos mismos años
    const dataComunaMate = evalsGrado.map(e => {
      const match = comunales.find(c => c.anio === e.anio && c.grado === e.grado);
      return match ? match.promedio_matematica : null;
    });

    state.chartHistoricoInstance = new Chart(dom.chartHistoricoCanvas, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Matemática (Colegio)',
            data: dataMate,
            borderColor: '#6366f1',
            backgroundColor: 'rgba(99, 102, 241, 0.1)',
            borderWidth: 3,
            tension: 0.3,
            pointRadius: 5,
            fill: true
          },
          {
            label: 'Lectura (Colegio)',
            data: dataLectura,
            borderColor: '#06b6d4',
            backgroundColor: 'rgba(6, 182, 212, 0.1)',
            borderWidth: 3,
            tension: 0.3,
            pointRadius: 5,
            fill: true
          },
          {
            label: 'Promedio Comuna (Matemática)',
            data: dataComunaMate,
            borderColor: '#64748b',
            borderWidth: 2,
            borderDash: [5, 5],
            pointRadius: 3,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            labels: { color: '#94a3b8', font: { family: 'Inter' } }
          }
        },
        scales: {
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8' },
            suggestedMin: 180,
            suggestedMax: 330
          },
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8' }
          }
        }
      }
    });
  }

  dom.btnCloseDetail.addEventListener('click', () => {
    dom.modalDetail.classList.remove('active');
  });

  // 6. Modal de Comparativa Lado a Lado
  async function openComparatorModal() {
    dom.modalComparator.classList.add('active');
    const rbdsParam = state.comparedRBDs.join(',');
    
    try {
      const res = await fetch(`/api/comparar?rbds=${rbdsParam}&grado=${state.grado}&anio=${state.anio}`);
      const data = await res.json();
      renderComparatorModal(data.colegios);
    } catch (err) {
      alert('Error al cargar la comparativa de colegios.');
      dom.modalComparator.classList.remove('active');
    }
  }

  function renderComparatorModal(colegios) {
    if (!colegios || colegios.length === 0) return;

    // 1. Armar Tabla Comparativa
    dom.compareTableHead.innerHTML = '<th>Indicador</th>' + colegios.map(c => `<th>${c.nombre}</th>`).join('');

    const rows = [
      { label: 'RBD', fn: c => c.rbd },
      { label: 'Dependencia', fn: c => `<span class="dep-badge ${getDependenciaClass(c.dependencia)}">${c.dependencia}</span>` },
      { label: 'Comuna', fn: c => c.nom_comuna },
      { label: 'Puntaje Lectura', fn: c => c.puntaje_lectura ? `<strong>${Math.round(c.puntaje_lectura)}</strong> pts` : 'S/I' },
      { label: 'Puntaje Matemática', fn: c => c.puntaje_matematica ? `<strong>${Math.round(c.puntaje_matematica)}</strong> pts` : 'S/I' },
      { label: 'Vs Promedio Comuna (Mate)', fn: c => {
        if (!c.puntaje_matematica || !c.comuna_matematica) return '-';
        const d = Math.round(c.puntaje_matematica - c.comuna_matematica);
        return `<span class="diff-badge ${d >= 0 ? 'diff-positive' : 'diff-negative'}">${d >= 0 ? '+' : ''}${d} pts</span>`;
      }},
      { label: '% Nivel Adecuado (Mate)', fn: c => c.pct_adecuado_matematica ? `${c.pct_adecuado_matematica}%` : '-' }
    ];

    dom.compareTableBody.innerHTML = rows.map(r => `
      <tr>
        <td><strong>${r.label}</strong></td>
        ${colegios.map(c => `<td>${r.fn(c)}</td>`).join('')}
      </tr>
    `).join('');

    // 2. Gráfico de Barras Agrupadas
    if (state.chartComparatorInstance) {
      state.chartComparatorInstance.destroy();
    }

    const schoolLabels = colegios.map(c => c.nombre.length > 20 ? c.nombre.substring(0, 18) + '...' : c.nombre);
    const mateScores = colegios.map(c => c.puntaje_matematica || 0);
    const lectScores = colegios.map(c => c.puntaje_lectura || 0);

    state.chartComparatorInstance = new Chart(dom.chartComparatorCanvas, {
      type: 'bar',
      data: {
        labels: schoolLabels,
        datasets: [
          {
            label: 'Matemática',
            data: mateScores,
            backgroundColor: '#6366f1',
            borderRadius: 6
          },
          {
            label: 'Lectura',
            data: lectScores,
            backgroundColor: '#06b6d4',
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { labels: { color: '#94a3b8' } }
        },
        scales: {
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8' },
            suggestedMin: 180,
            suggestedMax: 350
          },
          x: {
            grid: { display: false },
            ticks: { color: '#fff', font: { weight: 600 } }
          }
        }
      }
    });
  }

  dom.btnCloseCompare.addEventListener('click', () => {
    dom.modalComparator.classList.remove('active');
  });

  // Cerrar modales con Escape o clic fuera
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      dom.modalDetail.classList.remove('active');
      dom.modalComparator.classList.remove('active');
    }
  });

  [dom.modalDetail, dom.modalComparator].forEach(m => {
    m.addEventListener('click', (e) => {
      if (e.target === m) m.classList.remove('active');
    });
  });

  // Inicialización
  loadStats();
  loadFiltros();
  searchSchools();
  updateCompareDock();
});
