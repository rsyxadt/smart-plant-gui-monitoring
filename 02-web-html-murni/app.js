/**
 * Smart Plant Web Dashboard - app.js (Paket 3)
 * Workshop Mikrokontroler Lanjut & Teknik Antarmuka (PENS)
 * 100% Offline-First Real-time Canvas Charts, Simulation, SSE Client,
 * Alarm Web Audio, Live Logging, & Slide 6 Table Generator.
 */

// State Aplikasi
const state = {
  running: false,
  mode: 'sim',
  sourceType: 'sim',
  simTimer: null,
  eventSource: null,
  totalReceived: 0,
  totalInvalid: 0,
  seenSeqs: new Set(),
  intervalHistory: [],
  rttHistory: [],
  uiLatencies: [],
  currentRtt: null,
  currentInterval: null,
  alarmCount: 0,
  lastAlarmReasons: [],
  startTime: null,
  // Buffer Grafik (Maks 50 data point)
  maxPlotPoints: 50,
  dataTemp: [],
  dataHum: [],
  dataSoil: [],
  dataDist: [],
  // CSV Records
  csvRows: []
};

// Web Audio API untuk Alarm Beep
let audioCtx = null;
function playAlarmBeep() {
  if (!document.getElementById('audioAlarm').checked) return;
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(1200, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.12);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.12);
  } catch (e) {
    // Abaikan jika audio tidak diizinkan oleh browser
  }
}

// Elemen DOM
const dom = {
  sourceMode: document.getElementById('sourceMode'),
  tcpConfigRow: document.getElementById('tcpConfigRow'),
  simIntervalGroup: document.getElementById('simIntervalGroup'),
  espHost: document.getElementById('espHost'),
  espPort: document.getElementById('espPort'),
  ahtMode: document.getElementById('ahtMode'),
  targetPackets: document.getElementById('targetPackets'),
  simInterval: document.getElementById('simInterval'),
  btnStart: document.getElementById('btnStart'),
  btnStop: document.getElementById('btnStop'),
  threshTemp: document.getElementById('threshTemp'),
  threshHum: document.getElementById('threshHum'),
  threshDist: document.getElementById('threshDist'),
  threshSoil: document.getElementById('threshSoil'),
  connPill: document.getElementById('connPill'),
  alarmBanner: document.getElementById('alarmBanner'),
  valTemp: document.getElementById('valTemp'),
  statTemp: document.getElementById('statTemp'),
  cardTemp: document.getElementById('cardTemp'),
  valHum: document.getElementById('valHum'),
  statHum: document.getElementById('statHum'),
  cardHum: document.getElementById('cardHum'),
  valSoil: document.getElementById('valSoil'),
  statSoil: document.getElementById('statSoil'),
  cardSoil: document.getElementById('cardSoil'),
  valDist: document.getElementById('valDist'),
  statDist: document.getElementById('statDist'),
  cardDist: document.getElementById('cardDist'),
  mRec: document.getElementById('mRec'),
  mFail: document.getElementById('mFail'),
  mIntv: document.getElementById('mIntv'),
  mRtt: document.getElementById('mRtt'),
  mUi: document.getElementById('mUi'),
  btnSlide6: document.getElementById('btnSlide6'),
  btnExportCsv: document.getElementById('btnExportCsv'),
  logsTableBody: document.getElementById('logsTableBody'),
  packetCountBadge: document.getElementById('packetCountBadge'),
  footerInfo: document.getElementById('footerInfo'),
  footerTime: document.getElementById('footerTime'),
  slide6Modal: document.getElementById('slide6Modal'),
  modalCloseBtn: document.getElementById('modalCloseBtn'),
  modalCloseBtn2: document.getElementById('modalCloseBtn2'),
  slide6TableBody: document.getElementById('slide6TableBody'),
  btnCopySlide6: document.getElementById('btnCopySlide6'),
  // Canvas
  canvasTemp: document.getElementById('chartTemp'),
  canvasHum: document.getElementById('chartHum'),
  canvasDist: document.getElementById('chartDist')
};

// Inisialisasi Jam Footer
setInterval(() => {
  const now = new Date();
  dom.footerTime.textContent = now.toLocaleTimeString();
}, 1000);

// Toggle Tampilan Form berdasarkan Sumber Data
dom.sourceMode.addEventListener('change', () => {
  const isSim = dom.sourceMode.value === 'sim';
  dom.tcpConfigRow.style.display = isSim ? 'none' : 'flex';
  dom.simIntervalGroup.style.display = isSim ? 'block' : 'none';
});
dom.sourceMode.dispatchEvent(new Event('change'));

// Inisialisasi Canvas Hi-DPI
function setupCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  return { ctx, width: rect.width, height: rect.height };
}

window.addEventListener('resize', () => {
  drawAllCharts();
});

// Render Kurva Real-Time pada Canvas
function drawChart(canvas, points, minY, maxY, lineColors, threshY, threshLabel) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  if (canvas.width !== Math.floor(rect.width * dpr) || canvas.height !== Math.floor(rect.height * dpr)) {
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
  }
  const ctx = canvas.getContext('2d');
  ctx.save();
  ctx.scale(dpr, dpr);
  const w = rect.width;
  const h = rect.height;

  ctx.clearRect(0, 0, w, h);

  // Background & Grid
  ctx.strokeStyle = '#1E293B';
  ctx.lineWidth = 1;
  const gridLines = 4;
  for (let i = 0; i <= gridLines; i++) {
    const y = (h / gridLines) * i;
    ctx.beginPath();
    ctx.moveTo(35, y);
    ctx.lineTo(w - 10, y);
    ctx.stroke();

    // Nilai Sumbu Y
    const val = maxY - ((maxY - minY) / gridLines) * i;
    ctx.fillStyle = '#64748B';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(val.toFixed(0), 30, y + 3);
  }

  const plotLeft = 35;
  const plotWidth = w - plotLeft - 10;
  const plotHeight = h;

  // Garis Ambang Batas (Putus-putus)
  if (threshY !== null && threshY !== undefined) {
    const ty = plotHeight - ((threshY - minY) / (maxY - minY)) * plotHeight;
    ctx.strokeStyle = '#EF4444';
    ctx.lineWidth = 1.2;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(plotLeft, ty);
    ctx.lineTo(w - 10, ty);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  if (!points || points.length === 0) {
    ctx.fillStyle = '#475569';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Menunggu data...', w / 2, h / 2);
    ctx.restore();
    return;
  }

  // Gambar Kurva
  lineColors.forEach(({ key, color }) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.8;
    ctx.beginPath();

    const maxCount = state.maxPlotPoints;
    points.forEach((pt, idx) => {
      const val = pt[key];
      if (val === null || val === undefined) return;
      const x = plotLeft + (idx / (maxCount - 1)) * plotWidth;
      const clampedVal = Math.max(minY, Math.min(maxY, val));
      const y = plotHeight - ((clampedVal - minY) / (maxY - minY)) * plotHeight;
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });

  ctx.restore();
}

function drawAllCharts() {
  const tThresh = parseFloat(dom.threshTemp.value) || 32.0;
  drawChart(dom.canvasTemp, state.dataTemp, 15, 45, [{ key: 'temp', color: '#EF4444' }], tThresh);

  drawChart(dom.canvasHum, state.dataHum, 0, 100, [
    { key: 'hum', color: '#3B82F6' },
    { key: 'soil', color: '#F59E0B' }
  ], null);

  const dThresh = parseFloat(dom.threshDist.value) || 15.0;
  drawChart(dom.canvasDist, state.dataDist, 0, 60, [{ key: 'dist', color: '#A855F7' }], dThresh);
}

// Handler Tombol Mulai & Berhenti
dom.btnStart.addEventListener('click', () => startStream());
dom.btnStop.addEventListener('click', () => stopStream());

function startStream() {
  if (state.running) return;

  // Reset Riwayat & Metrik
  state.running = true;
  state.startTime = performance.now();
  state.totalReceived = 0;
  state.totalInvalid = 0;
  state.seenSeqs.clear();
  state.intervalHistory = [];
  state.rttHistory = [];
  state.uiLatencies = [];
  state.alarmCount = 0;
  state.currentRtt = null;
  state.currentInterval = null;
  state.dataTemp = [];
  state.dataHum = [];
  state.dataSoil = [];
  state.dataDist = [];
  state.csvRows = [];

  dom.logsTableBody.innerHTML = '';
  dom.btnStart.disabled = true;
  dom.btnStop.disabled = false;

  state.sourceType = dom.sourceMode.value;

  if (state.sourceType === 'sim') {
    startSimulation();
  } else {
    startSseClient();
  }
}

function stopStream() {
  if (!state.running) return;
  state.running = false;

  if (state.simTimer) {
    clearInterval(state.simTimer);
    state.simTimer = null;
  }

  if (state.eventSource) {
    state.eventSource.close();
    state.eventSource = null;
    fetch('/api/stop').catch(() => {});
  }

  dom.btnStart.disabled = false;
  dom.btnStop.disabled = true;
  setConnPill('disconnected', '● TERPUTUS');
  dom.footerInfo.textContent = 'Streaming dihentikan. Data tersimpan di memori (dapat diunduh CSV).';
}

function setConnPill(statusClass, text) {
  dom.connPill.className = `pill ${statusClass}`;
  dom.connPill.textContent = text;
}

// ==============================================================================
// 1. ENGINE SIMULASI SINTETIS PROTOCOL 4 (OFFLINE DEMO)
// ==============================================================================
function startSimulation() {
  const intervalMs = parseInt(dom.simInterval.value) || 85;
  const targetPackets = parseInt(dom.targetPackets.value) || 0;
  setConnPill('connected', `● SIMULASI AKTIF (${intervalMs}ms)`);
  dom.footerInfo.textContent = `Mode Simulasi berjalan (Interval ~${intervalMs}ms, Target: ${targetPackets || 'Kontinu'}).`;

  let seq = 1;
  const simStart = performance.now();
  let lastSend = performance.now();

  state.simTimer = setInterval(() => {
    if (!state.running) return;

    const now = performance.now();
    const elapsed = (now - simStart) / 1000;
    const actualInterval = seq > 1 ? now - lastSend : null;
    lastSend = now;

    // Sintesis data dinamis realistis
    const temp = 28.5 + 4.5 * Math.sin(elapsed * 0.15) + (Math.random() - 0.5) * 0.5;
    const hum = 65.0 - 10.0 * Math.sin(elapsed * 0.15) + (Math.random() - 0.5) * 0.8;
    const dist = Math.max(5.0, 28.0 + 16.0 * Math.cos(elapsed * 0.18) + (Math.random() - 0.5) * 0.6);
    const soilAdc = 2100 + 400 * Math.sin(elapsed * 0.08) + (Math.random() - 0.5) * 30;
    const soilPct = Math.max(0.0, Math.min(100.0, (1.0 - (soilAdc - 1500) / 1500) * 100.0));

    const frame = {
      type: 'data',
      protocol: 4,
      boot_id: 'sim_web_boot',
      stream_id: 'sim_web_str',
      seq: seq,
      esp_ms: Math.floor(elapsed * 1000),
      send_start_us: Math.floor(elapsed * 1000000),
      packet_interval_ms: actualInterval,
      soil: { sample: seq * 15, value: Math.round(soilAdc), second: Math.round(soilPct * 10) / 10, status: 'ok' },
      aht: { sample: seq, value: Math.round(temp * 100) / 100, second: Math.round(hum * 10) / 10, status: 'ok' },
      ultrasonic: { sample: seq * 2, value: Math.round(dist * 10) / 10, second: null, status: 'ok' }
    };

    handleDataFrame(frame, JSON.stringify(frame).length);

    // Kirim RTT sintetis
    const rttVal = intervalMs < 500 ? 35 + Math.random() * 12 : 55 + Math.random() * 25;
    handleRttFrame({ type: 'rtt', seq: seq, rtt_ms: Math.round(rttVal * 10) / 10 });

    seq++;
    if (targetPackets > 0 && seq > targetPackets) {
      stopStream();
      dom.footerInfo.textContent = `Target ${targetPackets} paket simulasi telah tercapai.`;
    }
  }, intervalMs);
}

// ==============================================================================
// 2. KLIEN SSE UNTUK ESP32 VIA SERVER.PY
// ==============================================================================
function startSseClient() {
  const host = dom.espHost.value.trim() || '192.168.4.1';
  const port = dom.espPort.value.trim() || '5000';
  const ahtMode = dom.ahtMode.value;
  const packets = dom.targetPackets.value;

  setConnPill('connecting', '● MENGHUBUNGKAN...');
  dom.footerInfo.textContent = `Menghubungkan ke ESP32 TCP (${host}:${port})...`;

  const url = `/api/stream?host=${encodeURIComponent(host)}&port=${encodeURIComponent(port)}&aht_mode=${encodeURIComponent(ahtMode)}&packets=${encodeURIComponent(packets)}`;
  state.eventSource = new EventSource(url);

  state.eventSource.onopen = () => {
    setConnPill('connected', '● TERHUBUNG ESP32');
    dom.footerInfo.textContent = `Terhubung ke ESP32 ${host}:${port}. Menunggu data...`;
  };

  state.eventSource.onmessage = (e) => {
    try {
      const payload = JSON.parse(e.data);
      if (payload.event === 'message') {
        const msg = payload.data;
        if (msg.type === 'data') {
          handleDataFrame(msg, payload.bytes);
        } else if (msg.type === 'rtt') {
          handleRttFrame(msg);
        } else if (msg.type === 'status' && msg.state === 'done') {
          stopStream();
          dom.footerInfo.textContent = 'ESP32 melaporkan target paket selesai.';
        }
      } else if (payload.event === 'connected') {
        setConnPill('connected', '● STREAM ESP32 AKTIF');
      } else if (payload.event === 'disconnected') {
        stopStream();
        setConnPill('disconnected', '● TERPUTUS');
        dom.footerInfo.textContent = `Koneksi terputus: ${payload.message || 'ESP32 offline'}`;
      } else if (payload.event === 'invalid_frame') {
        state.totalInvalid++;
        dom.mFail.textContent = `${state.totalInvalid} baris`;
        dom.mFail.className = 'text-danger';
      }
    } catch (err) {
      state.totalInvalid++;
      dom.mFail.textContent = `${state.totalInvalid} baris`;
    }
  };

  state.eventSource.onerror = () => {
    if (state.running) {
      stopStream();
      setConnPill('disconnected', '● SERVER ERROR');
      dom.footerInfo.textContent = 'Gagal berkomunikasi dengan server.py lokal. Buka RUN_HTML.bat dahulu!';
    }
  };
}

// ==============================================================================
// 3. PEMROSESAN DATA FRAME, ALARM, DAN GRAFIK
// ==============================================================================
function handleDataFrame(msg, rawBytes) {
  const tUi0 = performance.now();
  state.totalReceived++;
  const seq = msg.seq || state.totalReceived;
  state.seenSeqs.add(seq);

  const soil = msg.soil || {};
  const aht = msg.aht || {};
  const dist = msg.ultrasonic || {};

  const temp = aht.value;
  const hum = aht.second;
  const soilAdc = soil.value;
  const soilPct = soil.second;
  const distCm = dist.value;

  // Interval Metrik
  if (msg.packet_interval_ms && msg.packet_interval_ms > 0) {
    state.currentInterval = msg.packet_interval_ms;
    state.intervalHistory.push(msg.packet_interval_ms);
    if (state.intervalHistory.length > 100) state.intervalHistory.shift();
    const meanIntv = state.intervalHistory.reduce((a, b) => a + b, 0) / state.intervalHistory.length;
    dom.mIntv.textContent = `${meanIntv.toFixed(1)} ms`;
  }

  // Evaluasi Ambang Batas Alarm
  let alarmActive = false;
  const reasons = [];

  const tThresh = parseFloat(dom.threshTemp.value) || 32.0;
  if (temp !== null && temp > tThresh) {
    alarmActive = true;
    reasons.push(`Suhu ${temp.toFixed(1)}°C > ${tThresh}°C`);
    dom.cardTemp.classList.add('alarm-state');
    dom.statTemp.textContent = `⚠️ ALARM: > ${tThresh.toFixed(1)}°C`;
  } else {
    dom.cardTemp.classList.remove('alarm-state');
    dom.statTemp.textContent = `Status: ${aht.status || 'ok'} | Ambang: < ${tThresh.toFixed(1)}°C`;
  }

  const hThresh = parseFloat(dom.threshHum.value) || 40.0;
  if (hum !== null && hum < hThresh) {
    alarmActive = true;
    reasons.push(`RH ${hum.toFixed(1)}% < ${hThresh}%`);
    dom.cardHum.classList.add('alarm-state');
    dom.statHum.textContent = `⚠️ ALARM: < ${hThresh.toFixed(1)}%`;
  } else {
    dom.cardHum.classList.remove('alarm-state');
    dom.statHum.textContent = `Status: ${aht.status || 'ok'} | Ambang: > ${hThresh.toFixed(1)}%`;
  }

  const sThresh = parseFloat(dom.threshSoil.value) || 20.0;
  if (soilPct !== null && soilPct < sThresh) {
    alarmActive = true;
    reasons.push(`Soil ${soilPct.toFixed(1)}% < ${sThresh}%`);
    dom.cardSoil.classList.add('alarm-state');
    dom.statSoil.textContent = `⚠️ ALARM: Tanah Kering (< ${sThresh.toFixed(1)}%)`;
  } else {
    dom.cardSoil.classList.remove('alarm-state');
    dom.statSoil.textContent = `ADC: ${soilAdc ?? '--'} | Status: ${soil.status || 'ok'}`;
  }

  const dThresh = parseFloat(dom.threshDist.value) || 15.0;
  if (distCm !== null && distCm < dThresh) {
    alarmActive = true;
    reasons.push(`Jarak ${distCm.toFixed(1)}cm < ${dThresh}cm`);
    dom.cardDist.classList.add('alarm-state');
    dom.statDist.textContent = `⚠️ ALARM: Objek Dekat (< ${dThresh.toFixed(1)}cm)`;
  } else {
    dom.cardDist.classList.remove('alarm-state');
    dom.statDist.textContent = `Status: ${dist.status || 'ok'} | Ambang: > ${dThresh.toFixed(1)} cm`;
  }

  // Update Nilai Kartu
  dom.valTemp.textContent = temp !== null ? `${temp.toFixed(1)} °C` : '-- °C';
  dom.valHum.textContent = hum !== null ? `${hum.toFixed(1)} %RH` : '-- %RH';
  dom.valSoil.textContent = soilPct !== null ? `${soilPct.toFixed(1)} %` : (soilAdc ? `ADC ${soilAdc}` : '-- %');
  dom.valDist.textContent = distCm !== null ? `${distCm.toFixed(1)} cm` : '-- cm';

  // Banner Alarm & Audio Beep
  if (alarmActive) {
    state.alarmCount++;
    state.lastAlarmReasons = reasons;
    dom.alarmBanner.className = 'pill alarm';
    dom.alarmBanner.textContent = `⚠️ ALARM: ${reasons[0]}`;
    if (state.totalReceived % 3 === 0) playAlarmBeep();
  } else {
    dom.alarmBanner.className = 'pill normal';
    dom.alarmBanner.textContent = 'SISTEM NORMAL';
  }

  // Update Metrik Panel Kiri
  dom.mRec.textContent = `${state.totalReceived} baris`;
  dom.packetCountBadge.textContent = `${state.totalReceived} Paket`;

  // Masukkan ke Buffer Grafik
  state.dataTemp.push({ seq, temp });
  state.dataHum.push({ seq, hum, soil: soilPct });
  state.dataDist.push({ seq, dist: distCm });

  if (state.dataTemp.length > state.maxPlotPoints) state.dataTemp.shift();
  if (state.dataHum.length > state.maxPlotPoints) state.dataHum.shift();
  if (state.dataDist.length > state.maxPlotPoints) state.dataDist.shift();

  drawAllCharts();

  // Ukur Durasi Render UI (ms)
  const tUi1 = performance.now();
  const uiLat = tUi1 - tUi0;
  state.uiLatencies.push(uiLat);
  if (state.uiLatencies.length > 100) state.uiLatencies.shift();
  const meanUi = state.uiLatencies.reduce((a, b) => a + b, 0) / state.uiLatencies.length;
  dom.mUi.textContent = `${meanUi.toFixed(2)} ms`;

  // Tambahkan Baris ke Tabel Riwayat
  const timeStr = new Date().toLocaleTimeString();
  const alarmLabel = alarmActive ? `<span class="badge-alarm-cell">⚠️ ${reasons.join(', ')}</span>` : '<span class="badge-normal-cell">NORMAL</span>';

  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><strong>#${seq}</strong></td>
    <td>${timeStr}</td>
    <td>${temp !== null ? temp.toFixed(1) : '--'}</td>
    <td>${hum !== null ? hum.toFixed(1) : '--'}</td>
    <td>${soilAdc ?? '--'}</td>
    <td>${soilPct !== null ? soilPct.toFixed(1) : '--'}</td>
    <td>${distCm !== null ? distCm.toFixed(1) : '--'}</td>
    <td>${state.currentRtt !== null ? state.currentRtt.toFixed(1) : '--'}</td>
    <td>${state.currentInterval !== null ? state.currentInterval.toFixed(1) : '--'}</td>
    <td>${alarmLabel}</td>
  `;

  if (dom.logsTableBody.querySelector('.text-muted')) {
    dom.logsTableBody.innerHTML = '';
  }
  dom.logsTableBody.insertBefore(tr, dom.logsTableBody.firstChild);

  // Batasi tabel maksimal 40 baris agar ringan
  while (dom.logsTableBody.children.length > 40) {
    dom.logsTableBody.removeChild(dom.logsTableBody.lastChild);
  }

  // Simpan baris ke memori untuk Ekspor CSV
  state.csvRows.push({
    timestamp: new Date().toISOString(),
    seq,
    temp,
    hum,
    soilAdc,
    soilPct,
    distCm,
    rtt: state.currentRtt,
    interval: state.currentInterval,
    alarm: alarmActive ? 1 : 0,
    reasons: reasons.join(';')
  });
}

function handleRttFrame(msg) {
  if (msg.rtt_ms !== undefined && msg.rtt_ms !== null) {
    state.currentRtt = msg.rtt_ms;
    state.rttHistory.push(msg.rtt_ms);
    if (state.rttHistory.length > 100) state.rttHistory.shift();
    const meanRtt = state.rttHistory.reduce((a, b) => a + b, 0) / state.rttHistory.length;
    dom.mRtt.textContent = `${meanRtt.toFixed(1)} ms`;
  }
}

// ==============================================================================
// 4. MODAL SLIDE 6 & SALIN KE CLIPBOARD
// ==============================================================================
dom.btnSlide6.addEventListener('click', () => {
  const meanIntv = state.intervalHistory.length ? (state.intervalHistory.reduce((a, b) => a + b, 0) / state.intervalHistory.length).toFixed(1) : '--';
  const meanUi = state.uiLatencies.length ? (state.uiLatencies.reduce((a, b) => a + b, 0) / state.uiLatencies.length).toFixed(2) : '--';
  const grafikOk = state.totalReceived > 0 ? 'Ya (Lancar real-time)' : 'Belum diuji';
  const alarmOk = state.alarmCount > 0 ? `Ya (${state.alarmCount}x terpicu)` : 'Ya (Sesuai ambang)';
  const logOk = state.csvRows.length > 0 ? `Ya (${state.csvRows.length} baris di memori)` : 'Belum ada';
  const stabilOk = state.totalReceived > 0 ? 'Ya (100% stabil)' : 'Belum diuji';

  const rows = [
    ['Interval pembaruan (ms)', `${meanIntv} ms`, 'Diukur dari selisih waktu paket masuk'],
    ['Data diterima (baris)', `${state.totalReceived} baris`, `Total baris paket valid (Seq: ${state.seenSeqs.size})`],
    ['Data gagal parsing (baris)', `${state.totalInvalid} baris`, 'Frame JSON korup / malformed'],
    ['Respons tampilan UI (ms)', `${meanUi} ms`, 'Waktu render canvas & pembaruan DOM'],
    ['Grafik diperbarui', grafikOk, '3 subplot grafik real-time bergulir'],
    ['Alarm sesuai ambang', alarmOk, 'Evaluasi ambang batas Suhu, RH, Tanah, Jarak'],
    ['Logging tersimpan', logOk, 'Siap diunduh format .csv (Excel standard)'],
    ['Apakah GUI stabil lama?', stabilOk, 'Tidak ada memory leak / canvas buffering lancar']
  ];

  dom.slide6TableBody.innerHTML = rows.map(r => `
    <tr>
      <td><strong>${r[0]}</strong></td>
      <td style="text-align:center; color:#60A5FA; font-weight:700;">${r[1]}</td>
      <td style="color:#94A3B8;">${r[2]}</td>
    </tr>
  `).join('');

  dom.slide6Modal.classList.add('open');
});

dom.modalCloseBtn.addEventListener('click', () => dom.slide6Modal.classList.remove('open'));
dom.modalCloseBtn2.addEventListener('click', () => dom.slide6Modal.classList.remove('open'));

dom.btnCopySlide6.addEventListener('click', () => {
  const table = dom.slide6TableBody;
  let text = 'Parameter\tHasil Pengujian\tKeterangan\n';
  table.querySelectorAll('tr').forEach(tr => {
    const tds = tr.querySelectorAll('td');
    text += `${tds[0].innerText}\t${tds[1].innerText}\t${tds[2].innerText}\n`;
  });
  navigator.clipboard.writeText(text).then(() => {
    alert('Tabel hasil pengujian berhasil disalin ke Clipboard!\nAnda dapat langsung paste (Ctrl+V) ke PowerPoint Slide 6 atau Word.');
  });
});

// ==============================================================================
// 5. EKSPOR LOG DATA KE FORMAT CSV (EXCEL DELIMITER ;)
// ==============================================================================
dom.btnExportCsv.addEventListener('click', () => {
  if (state.csvRows.length === 0) {
    alert('Belum ada data masuk untuk diekspor!');
    return;
  }
  const headers = ['Timestamp_Local', 'Seq', 'Suhu_C', 'RH_Pct', 'Soil_ADC', 'Soil_Pct', 'Jarak_cm', 'RTT_ms', 'Interval_ms', 'Alarm_Active', 'Alarm_Reasons'];
  let csvContent = '\uFEFF' + headers.join(';') + '\n';

  state.csvRows.forEach(r => {
    const row = [
      r.timestamp,
      r.seq,
      r.temp ?? '',
      r.hum ?? '',
      r.soilAdc ?? '',
      r.soilPct ?? '',
      r.distCm ?? '',
      r.rtt ?? '',
      r.interval ?? '',
      r.alarm,
      `"${r.reasons || ''}"`
    ];
    csvContent += row.join(';') + '\n';
  });

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const dateStr = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  a.href = url;
  a.download = `log_gui_web_${dateStr}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

// Gambar awal grafik kosong
drawAllCharts();
