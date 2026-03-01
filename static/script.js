document.addEventListener("DOMContentLoaded", () => {
    // Check if we are on the interview page (has INTERVIEW_DATA)
    if (!window.INTERVIEW_DATA) {
        return; // Avoid running on company dashboard/login pages
    }

    const { token, candidateName, role } = window.INTERVIEW_DATA;

    const preInterview = document.getElementById("preInterview");
    const languageSelect = document.getElementById("languageSelect");
    const startInterviewBtn = document.getElementById("startInterviewBtn");

    const chatForm = document.getElementById("chatForm");
    const userInput = document.getElementById("userInput");
    const chatMessages = document.getElementById("chatMessages");
    const toggleVoiceBtn = document.getElementById("toggleVoice");

    const avatarImg = document.getElementById("avatarImage");
    const speakingIndicator = document.getElementById("speakingIndicator");
    const micBtn = document.getElementById("micBtn");

    const toggleCodeBtn = document.getElementById("toggleCodeBtn");
    const codeSection = document.getElementById("codeSection");
    const sendCodeBtn = document.getElementById("sendCodeBtn");

    let isVoiceEnabled = true;
    let selectedLanguage = "English";
    let isInterviewActive = false;
    let isCodeEditorOpen = false;

    // Toggle Code Editor
    if (toggleCodeBtn) {
        toggleCodeBtn.addEventListener("click", () => {
            isCodeEditorOpen = !isCodeEditorOpen;
            if (isCodeEditorOpen) {
                codeSection.style.display = "flex";
                toggleCodeBtn.innerHTML = '<i class="fas fa-times"></i> Close Code Editor';
                // Trigger monaco layout recalculation so it fits the new visible div
                setTimeout(() => {
                    if (window.codeEditor) {
                        window.codeEditor.layout();
                    }
                }, 100);
            } else {
                codeSection.style.display = "none";
                toggleCodeBtn.innerHTML = '<i class="fas fa-code"></i> Open Code Editor';
            }
        });
    }

    // Send Code to Chat
    if (sendCodeBtn) {
        sendCodeBtn.addEventListener("click", () => {
            if (!window.codeEditor || !isInterviewActive) return;
            const code = window.codeEditor.getValue().trim();
            if (!code || code === '# Write your technical solution here\ndef solution():\n    pass') {
                alert("Please write some code before sending!");
                return;
            }

            // Append code to the chat input and submit the form
            userInput.value = `Here is my code solution:\n\`\`\`python\n${code}\n\`\`\``;
            chatForm.dispatchEvent(new Event("submit"));
        });
    }

    // Web Speech API - Synthesis (TTS)
    const synth = window.speechSynthesis;
    let voices = [];

    // Web Speech API - Recognition (STT)
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    let isListening = false;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;

        recognition.onstart = () => {
            isListening = true;
            micBtn.classList.add("listening");
            userInput.placeholder = "Listening...";
        };

        recognition.onresult = (event) => {
            let finalTranscript = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    userInput.value = event.results[i][0].transcript;
                }
            }
            if (finalTranscript) {
                userInput.value = finalTranscript;
            }
        };

        recognition.onend = () => {
            isListening = false;
            micBtn.classList.remove("listening");
            userInput.placeholder = "Type or speak your answer...";
        };

        recognition.onerror = (event) => {
            console.error("Speech Recognition Error", event.error);
            isListening = false;
            micBtn.classList.remove("listening");
            userInput.placeholder = "Failed to transcribe. Type your answer...";
        };

        // Mic Toggle
        micBtn.addEventListener("click", () => {
            if (!isInterviewActive) return;
            if (isListening) {
                recognition.stop();
            } else {
                userInput.value = "";
                // Set Rec language based on choice
                if (selectedLanguage === "Hindi") {
                    recognition.lang = "hi-IN";
                } else if (selectedLanguage === "Gujarati") {
                    recognition.lang = "gu-IN";
                } else {
                    recognition.lang = "en-US";
                }
                recognition.start();
            }
        });
    } else {
        micBtn.style.display = 'none';
        userInput.placeholder = "Type your answer... (Microphone not supported)";
    }

    let currentAudio = null;

    // Toggle Voice Output
    toggleVoiceBtn.addEventListener("click", () => {
        isVoiceEnabled = !isVoiceEnabled;
        if (isVoiceEnabled) {
            toggleVoiceBtn.classList.add("active");
            toggleVoiceBtn.innerHTML = '<i class="fas fa-volume-up"></i> Voice is ON';
        } else {
            toggleVoiceBtn.classList.remove("active");
            toggleVoiceBtn.innerHTML = '<i class="fas fa-volume-mute"></i> Voice is OFF';

            // Stop generating/playing audio
            if (currentAudio) {
                currentAudio.pause();
                currentAudio.currentTime = 0;
            }
            stopAvatarAnimation();
        }
    });

    async function speak(text) {
        if (!isVoiceEnabled || !text) return;

        // Strip markdown
        const cleanText = text.replace(/[#*`~]/g, "").replace(/\n/g, " ");

        try {
            startAvatarAnimation();

            const response = await fetch("/api/speak", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: cleanText, language: selectedLanguage })
            });

            if (!response.ok) throw new Error("TTS Audio request failed");

            // Convert streaming response to MP3 Blob and play it
            const blob = await response.blob();
            const audioUrl = URL.createObjectURL(blob);

            // Stop any currently playing audio before starting new one
            if (currentAudio) {
                currentAudio.pause();
            }

            currentAudio = new Audio(audioUrl);
            currentAudio.playbackRate = 1.25; // Speed up the voice to sound more naturally human

            currentAudio.onended = () => {
                stopAvatarAnimation();
                URL.revokeObjectURL(audioUrl); // Clean up memory
            };

            currentAudio.onerror = () => {
                console.error("Audio playback error");
                stopAvatarAnimation();
            };

            await currentAudio.play();

        } catch (error) {
            console.error("Error generating voice:", error);
            stopAvatarAnimation();
        }
    }

    function startAvatarAnimation() {
        avatarImg.classList.add("speaking");
        speakingIndicator.classList.add("active");
    }

    function stopAvatarAnimation() {
        avatarImg.classList.remove("speaking");
        speakingIndicator.classList.remove("active");
    }

    function appendMessage(text, sender) {
        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message", sender);

        if (sender === "system") {
            const avatarImg = document.createElement("img");
            avatarImg.src = "/static/avatar.png";
            avatarImg.classList.add("chat-avatar");
            avatarImg.alt = "AIVA";
            msgDiv.appendChild(avatarImg);
        }

        const contentDiv = document.createElement("div");
        contentDiv.classList.add("msg-content");

        if (sender === "system") {
            contentDiv.innerHTML = marked.parse(text);
        } else {
            contentDiv.textContent = text;
        }

        msgDiv.appendChild(contentDiv);
        chatMessages.appendChild(msgDiv);

        setTimeout(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 100);
    }

    function showTyping() {
        const typingDiv = document.createElement("div");
        typingDiv.classList.add("message", "system");
        typingDiv.id = "typingIndicator";
        typingDiv.innerHTML = `
            <img src="/static/avatar.png" class="chat-avatar" alt="AIVA">
            <div class="typing-indicator">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
            </div>
        `;
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeTyping() {
        const typingDiv = document.getElementById("typingIndicator");
        if (typingDiv) {
            typingDiv.remove();
        }
    }

    // Start Interview Workflow
    startInterviewBtn.addEventListener("click", async () => {
        selectedLanguage = languageSelect.value;
        preInterview.style.display = "none";
        isInterviewActive = true;

        // Start Webcam Proctoring
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            const videoElem = document.getElementById("userWebcam");
            videoElem.srcObject = stream;
            document.getElementById("webcamContainer").style.display = "block";
        } catch (err) {
            console.warn("Webcam access denied or unavailable. Continuing without proctoring.", err);
        }

        chatMessages.innerHTML = '';
        showTyping();

        try {
            // Initiate the conversation mentioning the language
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: `[SYSTEM COMMAND] The user has joined. Conduct the entire interview exclusively in ${selectedLanguage} text/script. Do not write anything in English. Start now.`,
                    session_id: token,
                    language: selectedLanguage,
                    role: role
                })
            });
            const data = await response.json();

            removeTyping();

            if (data.status === "success") {
                appendMessage(data.response, "system");

                // Slight delay to ensure voices are loaded before speaking first line
                setTimeout(() => speak(data.response), 500);
            } else {
                appendMessage(`Error: ${data.error}`, "system");
            }
        } catch (error) {
            removeTyping();
            appendMessage(`Connection error: ${error.message}`, "system");
        }
    });

    async function checkAndGenerateReport(aiText) {
        const textLower = aiText.toLowerCase();
        const isEnd = textLower.includes("evaluation report") ||
            textLower.includes("officially complete") ||
            textLower.includes("સમાપ્ત") ||
            textLower.includes("समाप्त") ||
            textLower.includes("thank you for your time");

        if (isEnd) {
            isInterviewActive = false;
            document.getElementById("reportOverlay").style.display = "flex";

            try {
                const response = await fetch('/api/generate_report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: token,
                        token: token
                    })
                });

                const data = await response.json();

                const reportContent = document.getElementById("reportContent");
                const whatsappBtn = document.getElementById("whatsappShareBtn");
                const closeBtn = document.getElementById("closeReportBtn");

                if (data.status === "success") {
                    reportContent.innerHTML = marked.parse(data.report);
                    reportContent.style.display = "block";

                    // Setup WhatsApp Link
                    const waText = encodeURIComponent(`Candidate Interview Report\nName: ${candidateName}\nRole: ${role}\n--------------------------\n${data.report}\n--------------------------\nGenerated by AIVA AI`);
                    whatsappBtn.href = `https://api.whatsapp.com/send?text=${waText}`;
                    whatsappBtn.style.display = "flex";
                } else {
                    reportContent.innerHTML = `<p style="color:red">Failed to generate report: ${data.error}</p>`;
                    reportContent.style.display = "block";
                }
                closeBtn.style.display = "block";
                closeBtn.onclick = () => document.getElementById("reportOverlay").style.display = "none";

            } catch (err) {
                document.getElementById("reportContent").innerHTML = `<p style="color:red">Failed to connect to report server.</p>`;
                document.getElementById("reportContent").style.display = "block";
            }
        }
    }

    // Handle User Submission
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (!isInterviewActive) return;

        // If currently listening via mic, stop and use the current value
        if (isListening && recognition) {
            recognition.stop();
        }

        const message = userInput.value.trim();
        if (!message) return;

        synth.cancel();
        stopAvatarAnimation();

        appendMessage(message, "human");
        userInput.value = "";

        showTyping();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    session_id: token,
                    language: selectedLanguage,
                    role: role
                })
            });

            removeTyping();
            const data = await response.json();

            if (data.status === "success") {
                appendMessage(data.response, "system");
                speak(data.response);

                // Check if interview is over and trigger report Generation
                checkAndGenerateReport(data.response);
            } else {
                appendMessage(`Error: ${data.error}`, "system");
            }
        } catch (error) {
            removeTyping();
            appendMessage(`Failed to connect to backend: ${error.message}`, "system");
        }
    });

    // ─────────────────────────────────────────────────────
    //  ANTI-CHEAT: Tab / Window Switch Detection
    // ─────────────────────────────────────────────────────
    let tabSwitchCount = 0;
    const MAX_TAB_SWITCHES = 2; // 3rd switch = auto-disqualification

    function showWarningToast(message, level = 'warn') {
        const existing = document.querySelector('.anticheat-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'anticheat-toast';
        toast.style.cssText = `
            position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
            background: ${level === 'fail' ? '#dc2626' : '#d97706'};
            color: white; padding: 16px 28px; border-radius: 12px;
            font-weight: 700; font-size: 1rem; z-index: 99999;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            display: flex; align-items: center; gap: 10px;
        `;
        toast.innerHTML = `<i class="fas fa-${level === 'fail' ? 'ban' : 'exclamation-triangle'}"></i> ${message}`;
        document.body.appendChild(toast);

        if (level !== 'fail') {
            setTimeout(() => toast.remove(), 5000);
        }
    }

    document.addEventListener('visibilitychange', () => {
        if (document.hidden && isInterviewActive) {
            tabSwitchCount++;

            if (tabSwitchCount <= MAX_TAB_SWITCHES) {
                const msg = tabSwitchCount === MAX_TAB_SWITCHES
                    ? `🚨 FINAL WARNING (${tabSwitchCount}/${MAX_TAB_SWITCHES}): One more tab switch will AUTOMATICALLY DISQUALIFY you!`
                    : `⚠️ WARNING (${tabSwitchCount}/${MAX_TAB_SWITCHES}): Tab switching detected! This is a proctored interview.`;
                showWarningToast(msg, 'warn');
            }
        }

        // On returning to tab after max violations → auto disqualify
        if (!document.hidden && isInterviewActive && tabSwitchCount > MAX_TAB_SWITCHES) {
            isInterviewActive = false;
            showWarningToast('🚫 DISQUALIFIED: Interview terminated due to repeated tab switching (3 violations).', 'fail');
            appendMessage('⛔ This interview session has been TERMINATED due to repeated tab switching. A disqualification report is being generated.', 'system');

            setTimeout(() => {
                checkAndGenerateReport('FINAL EVALUATION REPORT disqualified due to tab switching violations');
            }, 2000);
        }
    });

    // Disable right-click during interview (basic deterrent)
    document.addEventListener('contextmenu', (e) => {
        if (isInterviewActive) {
            e.preventDefault();
            showWarningToast('⚠️ Right-click is disabled during the interview.', 'warn');
        }
    });
});
