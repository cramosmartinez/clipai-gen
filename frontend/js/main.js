document.addEventListener('DOMContentLoaded', () => {
    
    // --- REFERENCIAS DOM ---
    const dom = {
        navLoginBtn: document.getElementById('navLoginBtn'),
        navLogoutBtn: document.getElementById('navLogoutBtn'),
        closeModalBtn: document.getElementById('closeModalBtn'),
        loginModal: document.getElementById('loginModal'),
        loginForm: document.getElementById('loginForm'),
        loginSubmitBtn: document.getElementById('loginSubmitBtn'),
        loginSpinner: document.getElementById('loginSpinner'),
        loginError: document.getElementById('loginError'),
        
        videoUrl: document.getElementById('videoUrl'),
        videoThumb: document.getElementById('videoThumb'), // Referencia a la imagen
        processBtn: document.getElementById('processBtn'),
        settingsPanel: document.getElementById('settingsPanel'),
        
        resultsArea: document.getElementById('resultsArea'),
        progressBar: document.getElementById('progressBar'),
        progressStatus: document.getElementById('progressStatus'),
        progressPercent: document.getElementById('progressPercent'),
        progressDetail: document.getElementById('progressDetail'),
        clipsGrid: document.getElementById('clipsGrid'),
        
        userMenuBtn: document.getElementById('userMenuBtn'),
        creditsCounter: document.getElementById('creditsCounter'),
        usernameDisplay: document.getElementById('usernameDisplay'),
        
        optionBtns: document.querySelectorAll('.option-btn'),
        colorPrimary: document.getElementById('colorPrimary'),
        colorOutline: document.getElementById('colorOutline')
    };

    // --- ESTADO ---
    let state = {
        isAuthenticated: false,
        credits: 0,
        settings: {
            crop: 'auto',
            duration: 'auto',
            model: 'gemini-2.5',
            primaryColor: '#FFFFFF',
            outlineColor: '#000000'
        }
    };

    // --- 1. LÓGICA DE UI Y MINIATURAS (CORREGIDA) ---

    function detectVideo(url) {
        // Regex robusto para ID de YouTube (soporta shorts, embed, watch, youtu.be)
        const regExp = /^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#&?]*).*/;
        const match = url.match(regExp);
        const videoId = (match && match[7].length == 11) ? match[7] : false;

        if (videoId) {
            // Actualizar miniatura
            // Usamos hqdefault para mejor calidad, o maxresdefault si existe
            if (dom.videoThumb) {
                dom.videoThumb.src = `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;
            }
            
            dom.settingsPanel.classList.remove('hidden');
            
            // Habilitar botón si está logueado
            if (state.isAuthenticated) {
                dom.processBtn.disabled = false;
                dom.processBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
            dom.processBtn.classList.add('hover:scale-[1.02]');
        } else {
            dom.settingsPanel.classList.add('hidden');
            dom.processBtn.disabled = true;
            dom.processBtn.classList.add('opacity-50', 'cursor-not-allowed');
            dom.processBtn.classList.remove('hover:scale-[1.02]');
        }
    }

    // --- 2. LÓGICA DE BIBLIOTECA (AGRUPADA POR PROYECTO) ---

    const fetchHistory = async () => {
        if (!state.isAuthenticated) return;
        try {
            const res = await fetch('/history');
            const clips = await res.json();
            renderLibrary(clips);
        } catch (e) { console.error("Error historial:", e); }
    };

    const renderLibrary = (clips) => {
        dom.clipsGrid.innerHTML = '';
        
        if (clips.length === 0) {
             dom.clipsGrid.innerHTML = `
                <div class="col-span-full flex flex-col items-center justify-center py-16 text-zinc-500 space-y-4">
                    <i class="ph-thin ph-film-slate text-6xl text-zinc-600 mb-2"></i>
                    <p class="text-lg font-medium">Tu biblioteca está vacía.</p>
                </div>`;
             return;
        }

        // A. Agrupar clips por 'source_id' (Video Original)
        const projects = {};
        clips.forEach(clip => {
            // Usamos source_id como clave única del proyecto
            const key = clip.source_id || 'unknown';
            if (!projects[key]) {
                projects[key] = {
                    title: clip.original_video || "Video Sin Título",
                    source_id: clip.source_id,
                    date: new Date(clip.created_at * 1000).toLocaleDateString(),
                    clips: []
                };
            }
            projects[key].clips.push(clip);
        });

        // B. Renderizar cada Proyecto
        Object.values(projects).forEach(project => {
            const projectHTML = document.createElement('div');
            projectHTML.className = "col-span-full space-y-4 mb-8 animate-fade-in-up"; // Ocupa todo el ancho
            
            // Header del Proyecto (Miniatura Original + Título)
            const thumbUrl = project.source_id 
                ? `https://img.youtube.com/vi/${project.source_id}/mqdefault.jpg` 
                : 'https://via.placeholder.com/120x68?text=No+Img';

            projectHTML.innerHTML = `
                <div class="flex items-center gap-4 p-4 glass-panel rounded-xl border-l-4 border-brand">
                    <div class="w-32 h-20 flex-shrink-0 rounded-lg overflow-hidden bg-black relative group">
                        <img src="${thumbUrl}" class="w-full h-full object-cover opacity-80 group-hover:scale-110 transition-transform duration-500">
                        <div class="absolute inset-0 flex items-center justify-center">
                            <i class="ph-fill ph-youtube-logo text-red-500 text-2xl drop-shadow-md"></i>
                        </div>
                    </div>
                    <div>
                        <h3 class="text-lg font-bold text-white leading-tight">${project.title}</h3>
                        <div class="flex items-center gap-3 mt-2 text-xs text-zinc-400">
                            <span class="flex items-center gap-1"><i class="ph-bold ph-calendar-blank"></i> ${project.date}</span>
                            <span class="flex items-center gap-1 text-brand-light font-bold"><i class="ph-fill ph-film-strip"></i> ${project.clips.length} clips generados</span>
                        </div>
                    </div>
                </div>
                
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 pl-4 border-l border-white/5 ml-4">
                    ${project.clips.map(clip => createClipCardHTML(clip)).join('')}
                </div>
            `;
            
            dom.clipsGrid.appendChild(projectHTML);
        });
    };

    function createClipCardHTML(clip) {
        return `
            <div class="glass-panel rounded-2xl overflow-hidden group hover:-translate-y-2 hover:shadow-2xl hover:shadow-brand/20 transition-all duration-300 relative bg-zinc-900">
                <div class="absolute top-2 right-2 z-10 flex items-center gap-1.5 px-2 py-0.5 bg-black/60 backdrop-blur-md rounded-full border border-white/10">
                    <span class="text-[10px] font-bold text-yellow-400">⭐ ${clip.score ? clip.score.toFixed(1) : 'N/A'}</span>
                </div>
                <div class="relative aspect-[9/16] bg-black">
                    <video src="${clip.url}" controls class="w-full h-full object-cover"></video>
                </div>
                <div class="p-3">
                    <h4 class="font-bold text-xs text-zinc-200 line-clamp-2 mb-3 min-h-[2.5em]">${clip.title}</h4>
                    <a href="${clip.url}" download class="flex items-center justify-center gap-2 w-full py-2 bg-white/5 hover:bg-brand text-white text-[10px] font-bold rounded-lg border border-white/5 transition-all">
                        <i class="ph-bold ph-download-simple"></i> Descargar
                    </a>
                </div>
            </div>
        `;
    }


    // --- 3. FUNCIONES DE ESTADO (AUTH, MODAL, PROCESO) ---

    const toggleModal = (show) => {
        if (show) {
            dom.loginModal.classList.remove('hidden');
            dom.loginError.classList.add('hidden');
            document.getElementById('usernameInput').focus();
        } else {
            dom.loginModal.classList.add('hidden');
        }
    };

    const updateUIAuth = () => {
        if (state.isAuthenticated) {
            dom.navLoginBtn.classList.add('hidden');
            dom.userMenuBtn.classList.remove('hidden');
            dom.userMenuBtn.classList.add('flex');
            dom.creditsCounter.classList.remove('hidden');
            dom.creditsCounter.classList.add('flex');
            dom.creditsCounter.innerHTML = `<i class="ph-fill ph-lightning text-yellow-400"></i> <span>${state.credits} Créditos</span>`;
            dom.videoUrl.disabled = false;
            if(dom.videoUrl.value) dom.processBtn.disabled = false;
        } else {
            dom.navLoginBtn.classList.remove('hidden');
            dom.userMenuBtn.classList.add('hidden');
            dom.creditsCounter.classList.add('hidden');
            dom.videoUrl.disabled = true;
            dom.processBtn.disabled = true;
        }
    };

    const fetchStatus = async () => {
        try {
            const res = await fetch('/user_status');
            const data = await res.json();
            state.isAuthenticated = data.is_authenticated;
            state.credits = data.credits;
            if (data.username) dom.usernameDisplay.innerText = data.username;
            updateUIAuth();
            if(state.isAuthenticated) fetchHistory();
        } catch (e) { console.error(e); }
    };

    const login = async (e) => {
        e.preventDefault();
        const username = document.getElementById('usernameInput').value;
        const password = document.getElementById('passwordInput').value;
        
        dom.loginSubmitBtn.disabled = true;
        dom.loginSpinner.classList.remove('hidden');
        dom.loginError.classList.add('hidden');

        try {
            const res = await fetch('/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            
            if (res.ok) {
                toggleModal(false);
                fetchStatus();
            } else {
                throw new Error(data.message);
            }
        } catch (err) {
            dom.loginError.innerText = err.message;
            dom.loginError.classList.remove('hidden');
        } finally {
            dom.loginSubmitBtn.disabled = false;
            dom.loginSpinner.classList.add('hidden');
        }
    };

    const logout = async () => {
        await fetch('/logout');
        state.isAuthenticated = false;
        updateUIAuth();
        dom.videoUrl.value = '';
        dom.settingsPanel.classList.add('hidden');
        dom.resultsArea.classList.add('hidden');
    };

    const resetUIForNewProcess = () => {
        dom.resultsArea.classList.remove('hidden');
        dom.progressBar.style.width = '5%';
        dom.progressBar.parentElement.classList.add('animate-pulse');
        dom.progressPercent.innerText = '0%';
        dom.progressStatus.innerText = 'Iniciando...';
        // No borramos clipsGrid aquí para que el usuario siga viendo su historial
        // mientras se genera lo nuevo, se actualizará al final.
    };

    const startProcessing = async () => {
        if (!state.isAuthenticated) return toggleModal(true);
        const url = dom.videoUrl.value;
        if (!url) return;

        dom.processBtn.disabled = true;
        
        try {
            const res = await fetch('/start_process', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url, ...state.settings })
            });
            
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);

            localStorage.setItem('activeJobId', data.job_id);
            resetUIForNewProcess();
            connectToJobStream(data.job_id);

        } catch (err) {
            alert(err.message);
            dom.processBtn.disabled = false;
        }
    };

    const connectToJobStream = (jobId) => {
        dom.resultsArea.classList.remove('hidden');
        dom.processBtn.disabled = true;
        dom.processBtn.innerHTML = '<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Procesando...';

        const evtSource = new EventSource(`/stream/${jobId}`);
            
        evtSource.onmessage = (e) => {
            const msg = JSON.parse(e.data);
            if (msg.step === 'ping') return;
            
            const percent = Math.round(msg.progress) + '%';
            dom.progressBar.style.width = percent;
            dom.progressPercent.innerText = percent;
            dom.progressStatus.innerText = msg.msg;
            dom.progressDetail.innerText = `Estado: ${msg.step.toUpperCase()}`;
            
            if (msg.step === 'download' || msg.step === 'transcribe') {
                 dom.progressBar.parentElement.classList.remove('animate-pulse');
            }

            if (['complete', 'error'].includes(msg.step)) {
                evtSource.close();
                localStorage.removeItem('activeJobId');
                dom.processBtn.disabled = false;
                dom.processBtn.innerHTML = '<i class="ph-fill ph-sparkle text-xl mr-2"></i> Generar Clips';
                
                if (msg.step === 'complete') {
                    dom.progressBar.classList.add('bg-green-500');
                    dom.progressBar.classList.remove('from-brand', 'to-accent');
                    fetchHistory(); // Refrescar biblioteca agrupada
                    fetchStatus(); // Refrescar créditos
                } else {
                     dom.progressBar.classList.add('bg-red-500');
                     alert("Error: " + msg.msg);
                }
            }
        };
        
        evtSource.onerror = () => { 
            evtSource.close(); 
            dom.processBtn.disabled = false; 
            dom.processBtn.innerHTML = '<i class="ph-fill ph-sparkle text-xl mr-2"></i> Reintentar';
        };
    };

    // --- LISTENERS ---
    dom.navLoginBtn.addEventListener('click', () => toggleModal(true));
    dom.closeModalBtn.addEventListener('click', () => toggleModal(false));
    dom.loginForm.addEventListener('submit', login);
    dom.navLogoutBtn.addEventListener('click', logout);

    dom.videoUrl.addEventListener('input', (e) => {
        detectVideo(e.target.value); // Llama a la función corregida
    });

    dom.optionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.dataset.type;
            const val = btn.dataset.val;
            state.settings[type] = val;
            document.querySelectorAll(`.option-btn[data-type="${type}"]`).forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    dom.colorPrimary.addEventListener('change', (e) => state.settings.primaryColor = e.target.value);
    dom.colorOutline.addEventListener('change', (e) => state.settings.outlineColor = e.target.value);

    dom.processBtn.addEventListener('click', startProcessing);

    // Init
    fetchStatus();
    const activeJobId = localStorage.getItem('activeJobId');
    if (activeJobId) connectToJobStream(activeJobId);
});