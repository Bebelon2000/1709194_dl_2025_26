/**
 * Multiopen AI - Frontend Application
 * Gerencia chat, gravação de voz, upload de imagens e reprodução de áudio.
 */

// ============ Estado Global ============
const state = {
    isRecording: false,
    mediaRecorder: null,
    audioChunks: [],
    pendingImage: null,       // { file, base64, name }
    isProcessing: false,
    ws: null,
    currentStreamDiv: null,
    streamedText: '',
};

// ============ Elementos DOM ============
const $ = (sel) => document.querySelector(sel);
const chatArea = $('#chatArea');
const messagesContainer = $('#messagesContainer');
const welcomeContainer = $('#welcomeContainer');
const messageInput = $('#messageInput');
const btnSend = $('#btnSend');
const btnVoice = $('#btnVoice');
const btnUploadImage = $('#btnUploadImage');
const imageInput = $('#imageInput');
const imagePreviewBar = $('#imagePreviewBar');
const imagePreviewImg = $('#imagePreviewImg');
const imagePreviewName = $('#imagePreviewName');
const btnRemoveImage = $('#btnRemoveImage');
const btnNewChat = $('#btnNewChat');
const toggleSearch = $('#toggleSearch');
const toggleAutoTTS = $('#toggleAutoTTS');
const voiceSelect = $('#voiceSelect');
const audioPlayer = $('#audioPlayer');
const sidebar = $('#sidebar');
const sidebarToggle = $('#sidebarToggle');
const sidebarClose = $('#sidebarClose');
const sttStatus = $('#sttStatus');

// ============ Inicialização ============
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    connectWebSocket();
    autoResizeTextarea();
    checkSTTStatus();
});

// Check if STT is loaded
async function checkSTTStatus() {
    try {
        const resp = await fetch('/health');
        const data = await resp.json();
        if (data.services && data.services.stt) {
            sttStatus.classList.add('online');
        }
    } catch (e) {
        console.log('Health check falhou:', e);
    }
}

function setupEventListeners() {
    // Enviar mensagem
    btnSend.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto resize textarea
    messageInput.addEventListener('input', autoResizeTextarea);

    // Gravação de voz
    btnVoice.addEventListener('click', toggleRecording);

    // Upload de imagem
    btnUploadImage.addEventListener('click', () => imageInput.click());
    imageInput.addEventListener('change', handleImageSelect);
    btnRemoveImage.addEventListener('click', removeImage);

    // Nova conversa
    btnNewChat.addEventListener('click', clearChat);

    // Chips de sugestão
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            messageInput.value = chip.dataset.message;
            autoResizeTextarea();
            sendMessage();
        });
    });

    // Sidebar mobile
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => sidebar.classList.add('open'));
    }
    if (sidebarClose) {
        sidebarClose.addEventListener('click', () => sidebar.classList.remove('open'));
    }
}

// ============ WebSocket ============
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

    try {
        state.ws = new WebSocket(wsUrl);

        state.ws.onopen = () => {
            console.log('WebSocket conectado');
        };

        state.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleStreamData(data);
        };

        state.ws.onclose = () => {
            console.log('WebSocket desconectado. Reconectando em 3s...');
            setTimeout(connectWebSocket, 3000);
        };

        state.ws.onerror = (err) => {
            console.error('WebSocket erro:', err);
        };
    } catch (e) {
        console.error('Falha ao conectar WebSocket:', e);
        setTimeout(connectWebSocket, 3000);
    }
}

function handleStreamData(data) {
    switch (data.type) {
        case 'token':
            if (state.currentStreamDiv) {
                state.streamedText += data.data;
                state.currentStreamDiv.innerHTML = renderMarkdown(state.streamedText);
                scrollToBottom();
            }
            break;

        case 'search':
            // Mostrar badge de pesquisa
            if (state.currentStreamDiv) {
                const badge = document.createElement('div');
                badge.className = 'search-badge';
                badge.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/></svg> Pesquisa web realizada';
                state.currentStreamDiv.parentElement.insertBefore(badge, state.currentStreamDiv);
            }
            break;

        case 'done':
            // Remover indicador de digitação e adicionar ações
            const typingEl = state.currentStreamDiv?.parentElement?.querySelector('.typing-indicator');
            if (typingEl) typingEl.remove();

            if (state.currentStreamDiv) {
                addMessageActions(state.currentStreamDiv.parentElement, state.streamedText);
            }

            // Auto TTS
            if (toggleAutoTTS.checked && state.streamedText) {
                playTTS(state.streamedText);
            }

            state.currentStreamDiv = null;
            state.streamedText = '';
            state.isProcessing = false;
            updateSendButton();
            break;

        case 'error':
            if (state.currentStreamDiv) {
                state.currentStreamDiv.innerHTML = `<span style="color:var(--error)">Erro: ${data.data}</span>`;
            }
            state.isProcessing = false;
            updateSendButton();
            break;
    }
}

// ============ Enviar Mensagem ============
async function sendMessage() {
    const text = messageInput.value.trim();
    if ((!text && !state.pendingImage) || state.isProcessing) return;

    // --- Auto-detecção de Intents (Skill Automática) ---
    const lowerText = text.toLowerCase();
    
    // Auto-detect Web Search
    const webSearchRegex = /(pesquise|pesquisa|busca|busque|procura|procure).*(web|internet|google|online)/i;
    if (webSearchRegex.test(lowerText)) {
        toggleSearch.checked = true;
    }

    // Auto-detect Voice Response
    const voiceRegex = /(fala|fale|diz|diga|responde|responda|leia|lê|descreve|descreva).*(voz|para mim|me)|me descreva|descreva-me|fala-me|diz-me|lê para mim/i;
    if (voiceRegex.test(lowerText)) {
        toggleAutoTTS.checked = true;
    }
    // --------------------------------------------------

    state.isProcessing = true;
    updateSendButton();

    // Esconder welcome
    if (welcomeContainer) {
        welcomeContainer.style.display = 'none';
    }

    // Adicionar mensagem do utilizador
    const userMsg = text || '(imagem enviada)';
    addUserMessage(userMsg, state.pendingImage);

    // Limpar input
    messageInput.value = '';
    autoResizeTextarea();

    // Preparar resposta do assistente
    const { contentDiv } = addAssistantMessage();
    state.currentStreamDiv = contentDiv;
    state.streamedText = '';

    // Enviar via WebSocket ou REST
    if (state.pendingImage) {
        // Com imagem -> usar REST (WebSocket com base64 grande pode ser problemático)
        await sendWithImage(text, state.pendingImage);
        removeImage();
    } else if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        // Sem imagem -> usar WebSocket para streaming
        const payload = {
            message: text,
            web_search: toggleSearch.checked,
            voice_response: toggleAutoTTS.checked,
        };
        state.ws.send(JSON.stringify(payload));
    } else {
        // Fallback REST
        await sendREST(text);
    }
}

async function sendWithImage(text, imageData) {
    try {
        const formData = new FormData();
        formData.append('message', text || 'Descreve esta imagem em detalhe.');
        formData.append('image', imageData.file);

        const response = await fetch('/api/chat/image', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        state.streamedText = data.response;
        state.currentStreamDiv.innerHTML = renderMarkdown(data.response);
        addMessageActions(state.currentStreamDiv.parentElement, data.response);

        if (toggleAutoTTS.checked && data.response) {
            playTTS(data.response);
        }

        scrollToBottom();
    } catch (err) {
        state.currentStreamDiv.innerHTML = `<span style="color:var(--error)">Erro: ${err.message}</span>`;
    } finally {
        state.isProcessing = false;
        state.currentStreamDiv = null;
        updateSendButton();
    }
}

async function sendREST(text) {
    try {
        const formData = new FormData();
        formData.append('message', text);
        formData.append('web_search', toggleSearch.checked);
        formData.append('voice_response', toggleAutoTTS.checked);

        const response = await fetch('/api/chat', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        if (data.web_search && data.search_context) {
            const badge = document.createElement('div');
            badge.className = 'search-badge';
            badge.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/></svg> Pesquisa web realizada';
            state.currentStreamDiv.parentElement.insertBefore(badge, state.currentStreamDiv);
        }

        state.streamedText = data.response;
        state.currentStreamDiv.innerHTML = renderMarkdown(data.response);
        addMessageActions(state.currentStreamDiv.parentElement, data.response);

        if (toggleAutoTTS.checked && data.response) {
            playTTS(data.response);
        }

        scrollToBottom();
    } catch (err) {
        state.currentStreamDiv.innerHTML = `<span style="color:var(--error)">Erro: ${err.message}</span>`;
    } finally {
        state.isProcessing = false;
        state.currentStreamDiv = null;
        updateSendButton();
    }
}

// ============ UI Mensagens ============
function addUserMessage(text, imageData) {
    const div = document.createElement('div');
    div.className = 'message message-user';

    let imageHtml = '';
    if (imageData) {
        imageHtml = `<img src="${imageData.base64}" alt="Imagem enviada" class="message-image">`;
    }

    div.innerHTML = `
        <div class="message-avatar">TU</div>
        <div class="message-body">
            ${imageHtml}
            <div class="message-content">${escapeHtml(text)}</div>
        </div>
    `;

    messagesContainer.appendChild(div);
    scrollToBottom();
}

function addAssistantMessage() {
    const div = document.createElement('div');
    div.className = 'message message-assistant';

    div.innerHTML = `
        <div class="message-avatar">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        </div>
        <div class="message-body">
            <div class="message-content">
                <div class="typing-indicator">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            </div>
        </div>
    `;

    messagesContainer.appendChild(div);
    scrollToBottom();

    const contentDiv = div.querySelector('.message-content');
    return { div, contentDiv };
}

function addMessageActions(el, text) {
    // Navigate to the .message div if we received a child element
    const messageDiv = el.closest ? el.closest('.message') || el : el;
    const body = messageDiv.querySelector('.message-body');
    if (!body || body.querySelector('.message-actions')) return;

    const actions = document.createElement('div');
    actions.className = 'message-actions';

    actions.innerHTML = `
        <button class="btn-action btn-tts-play" title="Ouvir resposta">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
            Ouvir
        </button>
        <button class="btn-action btn-copy" title="Copiar texto">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            Copiar
        </button>
    `;

    // Event: Ouvir
    actions.querySelector('.btn-tts-play').addEventListener('click', () => {
        playTTS(text);
    });

    // Event: Copiar
    actions.querySelector('.btn-copy').addEventListener('click', function () {
        navigator.clipboard.writeText(text).then(() => {
            this.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Copiado!';
            setTimeout(() => {
                this.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copiar';
            }, 2000);
        });
    });

    body.appendChild(actions);
}

// ============ Gravação de Voz ============
async function toggleRecording() {
    if (state.isRecording) {
        stopRecording();
    } else {
        await startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        state.audioChunks = [];

        state.mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus',
        });

        state.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) state.audioChunks.push(e.data);
        };

        state.mediaRecorder.onstop = async () => {
            stream.getTracks().forEach((t) => t.stop());

            const audioBlob = new Blob(state.audioChunks, { type: 'audio/webm' });
            await transcribeAudio(audioBlob);
        };

        state.mediaRecorder.start();
        state.isRecording = true;
        btnVoice.classList.add('recording');
        sttStatus.classList.add('online');
    } catch (err) {
        console.error('Erro ao aceder ao microfone:', err);
        alert('Não foi possível aceder ao microfone. Verifica as permissões do browser.');
    }
}

function stopRecording() {
    if (state.mediaRecorder && state.mediaRecorder.state !== 'inactive') {
        state.mediaRecorder.stop();
    }
    state.isRecording = false;
    btnVoice.classList.remove('recording');
}

async function transcribeAudio(audioBlob) {
    try {
        // Mostrar spinner no input
        messageInput.placeholder = 'A transcrever áudio...';
        messageInput.disabled = true;

        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');
        formData.append('language', 'pt');

        const response = await fetch('/api/stt', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        if (data.text) {
            messageInput.value = data.text;
            autoResizeTextarea();
            // Colocar o cursor no input para o utilizador rever antes de enviar
            messageInput.focus();
        } else {
            messageInput.placeholder = 'Não foi possível transcrever o áudio.';
            setTimeout(() => {
                messageInput.placeholder = 'Escreve uma mensagem...';
            }, 2000);
        }
    } catch (err) {
        console.error('Erro na transcrição:', err);
        messageInput.placeholder = 'Erro na transcrição. Tenta novamente.';
        setTimeout(() => {
            messageInput.placeholder = 'Escreve uma mensagem...';
        }, 2000);
    } finally {
        messageInput.disabled = false;
        sttStatus.classList.remove('online');
    }
}

// ============ Upload de Imagem ============
function handleImageSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (ev) => {
        state.pendingImage = {
            file: file,
            base64: ev.target.result,
            name: file.name,
        };

        imagePreviewImg.src = ev.target.result;
        imagePreviewName.textContent = file.name;
        imagePreviewBar.style.display = 'block';
    };
    reader.readAsDataURL(file);

    // Limpar input para permitir re-selecção
    imageInput.value = '';
}

function removeImage() {
    state.pendingImage = null;
    imagePreviewBar.style.display = 'none';
    imagePreviewImg.src = '';
    imagePreviewName.textContent = '';
}

// ============ Text-to-Speech ============
async function playTTS(text) {
    if (!text) return;

    // Limpar markdown/código/emojis do texto para TTS mais natural
    const cleanText = text
        .replace(/```[\s\S]*?```/g, ' código omitido ')
        .replace(/`[^`]+`/g, '')
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/\*([^*]+)\*/g, '$1')
        .replace(/#+\s/g, '')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{200D}\u{20E3}\u{E0020}-\u{E007F}✨⭐🌟💡🎯🔥❤️✅❌⚡️🎉👋🤔💭🧠📌🔗📎💻🖥️📱🔒🔓📢🗣️💬🗨️📝✏️📚📖🎓🏆🥇🥈🥉🏅🎖️]/gu, '')
        .replace(/\s{2,}/g, ' ')
        .replace(/\n/g, ' ')
        .trim();

    if (!cleanText) return;

    try {
        const formData = new FormData();
        formData.append('text', cleanText);
        formData.append('voice', voiceSelect.value);

        const response = await fetch('/api/tts', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);

        audioPlayer.src = audioUrl;
        audioPlayer.play().catch(err => console.error('Erro ao reproduzir:', err));

        // Limpar URL quando terminar
        audioPlayer.onended = () => {
            URL.revokeObjectURL(audioUrl);
        };
    } catch (err) {
        console.error('Erro no TTS:', err);
    }
}

// ============ Chat Management ============
async function clearChat() {
    try {
        await fetch('/api/chat/clear', { method: 'POST' });
    } catch (e) {
        console.error('Erro ao limpar chat:', e);
    }

    messagesContainer.innerHTML = '';
    if (welcomeContainer) {
        welcomeContainer.style.display = 'flex';
    }
    sidebar.classList.remove('open');
}

// ============ Utilitários ============
function scrollToBottom() {
    chatArea.scrollTop = chatArea.scrollHeight;
}

function autoResizeTextarea() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
}

function updateSendButton() {
    if (state.isProcessing) {
        btnSend.innerHTML = '<span class="spinner"></span>';
        btnSend.disabled = true;
    } else {
        btnSend.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
        btnSend.disabled = false;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderMarkdown(text) {
    if (!text) return '';

    let html = escapeHtml(text);

    // Code blocks
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

    // Lists
    html = html.replace(/^\s*[-*]\s+(.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Line breaks -> paragraphs
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    if (!html.startsWith('<')) {
        html = '<p>' + html + '</p>';
    }

    return html;
}
