/* =========================================
   MeetScribe - Main Application Logic
   ========================================= */

(function () {
  "use strict";

  // ---- State ----
  let captionsData = []; // raw captions from API
  let speakerMap = {}; // e.g. { "A": "John Doe", "B": "Jane" }
  let audioSegments = {}; // e.g. { "A": "/path/to/a.mp3", ... }
  let audioElements = {}; // Audio() instances per speaker
  let isSeeking = {}; // track seeking state per speaker
  let hasData = false;

  // ---- DOM refs ----
  const uploadSection = document.getElementById("uploadSection");
  const uploadArea = document.getElementById("uploadArea");
  const fileInput = document.getElementById("fileInput");
  const browseBtn = document.getElementById("browseBtn");
  const uploadProgress = document.getElementById("uploadProgress");
  const uploadStatusText = document.getElementById("uploadStatusText");
  const progressBarFill = document.getElementById("progressBarFill");
  const resultsSection = document.getElementById("resultsSection");
  const speakerList = document.getElementById("speakerList");
  const captionsList = document.getElementById("captionsList");
  const captionCount = document.getElementById("captionCount");
  const downloadPdfBtn = document.getElementById("downloadPdfBtn");
  const downloadSummaryBtn = document.getElementById("downloadSummaryBtn");
  const newUploadBtn = document.getElementById("newUploadBtn");
  const confirmModal = document.getElementById("confirmModal");
  const cancelUploadBtn = document.getElementById("cancelUploadBtn");
  const confirmUploadBtn = document.getElementById("confirmUploadBtn");

  // ---- Persistence (sessionStorage) ----
  const STORAGE_KEY_MAP = "meetscribe_speaker_map";
  const STORAGE_KEY_CAPTIONS = "meetscribe_captions";
  const STORAGE_KEY_SEGMENTS = "meetscribe_segments";

  function savePersistence() {
    sessionStorage.setItem(STORAGE_KEY_MAP, JSON.stringify(speakerMap));
    sessionStorage.setItem(STORAGE_KEY_CAPTIONS, JSON.stringify(captionsData));
    sessionStorage.setItem(STORAGE_KEY_SEGMENTS, JSON.stringify(audioSegments));
  }

  function loadPersistence() {
    try {
      const map = sessionStorage.getItem(STORAGE_KEY_MAP);
      const captions = sessionStorage.getItem(STORAGE_KEY_CAPTIONS);
      const segments = sessionStorage.getItem(STORAGE_KEY_SEGMENTS);
      if (map) speakerMap = JSON.parse(map);
      if (captions) captionsData = JSON.parse(captions);
      if (segments) audioSegments = JSON.parse(segments);
      return captionsData.length > 0;
    } catch (err) {
      console.error("[v0] Error loading persistence:", err);
      return false;
    }
  }

  function clearPersistence() {
    try {
      sessionStorage.removeItem(STORAGE_KEY_MAP);
      sessionStorage.removeItem(STORAGE_KEY_CAPTIONS);
      sessionStorage.removeItem(STORAGE_KEY_SEGMENTS);
      speakerMap = {};
      captionsData = [];
      audioSegments = {};
      audioElements = {};
      isSeeking = {};
      hasData = false;
    } catch (err) {
      console.error("[v0] Error clearing persistence:", err);
    }
  }

  // ---- Helpers ----
  function formatTime(seconds) {
    try {
      const s = Math.floor(seconds);
      const m = Math.floor(s / 60);
      const sec = s % 60;
      const h = Math.floor(m / 60);
      const min = m % 60;
      if (h > 0) {
        return `${h}:${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
      }
      return `${min}:${String(sec).padStart(2, "0")}`;
    } catch (err) {
      console.error("[v0] Error formatting time:", err);
      return "0:00";
    }
  }

  function getSpeakerColor(speaker) {
    try {
      const colors = ["a", "b", "c", "d", "e", "f"];
      const char = speaker.toString().charAt(0);
      let idx;
      
      // Handle both letters (A-Z) and numbers (0-9)
      if (/[A-Z]/i.test(char)) {
        idx = char.toUpperCase().charCodeAt(0) - 65; // A=0, B=1, ...
      } else if (/[0-9]/.test(char)) {
        idx = parseInt(char); // 0=0, 1=1, ...
      } else {
        idx = 0; // Default to first color
      }
      
      return colors[idx % colors.length];
    } catch (err) {
      console.error("[v0] Error getting speaker color:", err);
      return "a";
    }
  }

  function getDisplayName(speaker) {
    try {
      return speakerMap[speaker] && speakerMap[speaker].trim()
        ? speakerMap[speaker].trim()
        : `Speaker ${speaker}`;
    } catch (err) {
      console.error("[v0] Error getting display name:", err);
      return `Speaker ${speaker}`;
    }
  }

  function getUniqueSpeakers() {
    try {
      const seen = new Set();
      captionsData.forEach((c) => seen.add(c.speaker));
      return Array.from(seen).sort();
    } catch (err) {
      console.error("[v0] Error getting unique speakers:", err);
      return [];
    }
  }

  // ---- Rendering ----
  function renderCaptions() {
    try {
      captionsList.innerHTML = "";
      captionsData.forEach((item) => {
        const color = getSpeakerColor(item.speaker);
        const div = document.createElement("div");
        div.className = `caption-item caption-item-${color}`;
        div.innerHTML = `
          <div class="caption-timestamp">${formatTime(item.timestamp.start)} - ${formatTime(item.timestamp.end)}</div>
          <div class="caption-speaker caption-speaker-${color}">${getDisplayName(item.speaker)}</div>
          <div class="caption-text">${escapeHtml(item.text)}</div>
        `;
        captionsList.appendChild(div);
      });
      captionCount.textContent = `${captionsData.length} segment${captionsData.length !== 1 ? "s" : ""}`;
    } catch (err) {
      console.error("[v0] Error rendering captions:", err);
    }
  }

  function escapeHtml(str) {
    try {
      const d = document.createElement("div");
      d.textContent = str;
      return d.innerHTML;
    } catch (err) {
      console.error("[v0] Error escaping HTML:", err);
      return str;
    }
  }

  function renderSpeakerCards() {
    try {
      speakerList.innerHTML = "";
      const speakers = getUniqueSpeakers();

      speakers.forEach((spk) => {
        try {
          const color = getSpeakerColor(spk);
          const card = document.createElement("div");
          card.className = "speaker-card";

          const hasAudio = audioSegments[spk];

          card.innerHTML = `
            <div class="speaker-card-header">
              <div class="speaker-badge speaker-badge-${color}">${spk}</div>
              <span class="speaker-label">Speaker ${spk}</span>
            </div>
            <input
              type="text"
              class="speaker-name-input"
              placeholder="Enter name (e.g. John Doe)"
              value="${speakerMap[spk] ? escapeHtml(speakerMap[spk]) : ""}"
              data-speaker="${spk}"
            />
            ${
              hasAudio
                ? `
            <div class="speaker-audio-player" data-speaker="${spk}">
              <button class="play-btn" data-speaker="${spk}" aria-label="Play audio for Speaker ${spk}">
                <svg viewBox="0 0 24 24" fill="currentColor" stroke="none">
                  <polygon points="5,3 19,12 5,21"/>
                </svg>
              </button>
              <div class="audio-bar-track" data-speaker="${spk}">
                <div class="audio-bar-fill" id="audioFill-${spk}"></div>
              </div>
              <span class="audio-time" id="audioTime-${spk}">0:00</span>
            </div>`
                : `<div style="font-size:12px;color:var(--text-secondary);opacity:0.6;">No audio segment available</div>`
            }
          `;

          speakerList.appendChild(card);
        } catch (err) {
          console.error(`[v0] Error rendering speaker card for ${spk}:`, err);
        }
      });

      // Bind input events
      speakerList.querySelectorAll(".speaker-name-input").forEach((input) => {
        try {
          input.addEventListener("input", handleNameChange);
        } catch (err) {
          console.error("[v0] Error binding name input:", err);
        }
      });

      // Bind play buttons
      speakerList.querySelectorAll(".play-btn").forEach((btn) => {
        try {
          btn.addEventListener("click", handlePlayAudio);
        } catch (err) {
          console.error("[v0] Error binding play button:", err);
        }
      });

      // Bind audio bar clicks
      speakerList.querySelectorAll(".audio-bar-track").forEach((bar) => {
        try {
          bar.addEventListener("mousedown", handleAudioSeekStart);
          bar.addEventListener("click", handleAudioSeek);
        } catch (err) {
          console.error("[v0] Error binding audio bar:", err);
        }
      });
    } catch (err) {
      console.error("[v0] Error rendering speaker cards:", err);
    }
  }

  // ---- Event Handlers ----
  function handleNameChange(e) {
    try {
      const speaker = e.target.dataset.speaker;
      speakerMap[speaker] = e.target.value;
      savePersistence();
      renderCaptions();
    } catch (err) {
      console.error("[v0] Error handling name change:", err);
    }
  }

  function handlePlayAudio(e) {
    try {
      const btn = e.currentTarget;
      const speaker = btn.dataset.speaker;
      const src = audioSegments[speaker];
      if (!src) return;

      // Pause all others
      Object.keys(audioElements).forEach((k) => {
        try {
          if (k !== speaker && audioElements[k]) {
            audioElements[k].pause();
            updatePlayIcon(k, false);
          }
        } catch (err) {
          console.error(`[v0] Error pausing audio for speaker ${k}:`, err);
        }
      });

      if (!audioElements[speaker]) {
        audioElements[speaker] = new Audio(src);
        audioElements[speaker].crossOrigin = "anonymous";
        bindAudioEvents(speaker);
      }

      const audio = audioElements[speaker];
      if (audio.paused) {
        audio.play().catch((err) => {
          console.error(`[v0] Error playing audio for speaker ${speaker}:`, err);
        });
        updatePlayIcon(speaker, true);
      } else {
        audio.pause();
        updatePlayIcon(speaker, false);
      }
    } catch (err) {
      console.error("[v0] Error handling play audio:", err);
    }
  }

  function handleAudioSeekStart(e) {
    try {
      const speaker = e.currentTarget.dataset.speaker;
      if (!audioElements[speaker]) return;
      isSeeking[speaker] = true;
    } catch (err) {
      console.error("[v0] Error in seek start:", err);
    }
  }

  function handleAudioSeek(e) {
    try {
      const speaker = e.currentTarget.dataset.speaker;
      if (!audioElements[speaker]) return;

      const rect = e.currentTarget.getBoundingClientRect();
      const pct = (e.clientX - rect.left) / rect.width;
      const newTime = Math.max(0, Math.min(pct * audioElements[speaker].duration, audioElements[speaker].duration));
      audioElements[speaker].currentTime = newTime;
      isSeeking[speaker] = false;
    } catch (err) {
      console.error("[v0] Error handling audio seek:", err);
    }
  }

  function bindAudioEvents(speaker) {
    try {
      const audio = audioElements[speaker];
      const fill = document.getElementById(`audioFill-${speaker}`);
      const time = document.getElementById(`audioTime-${speaker}`);

      audio.addEventListener("timeupdate", () => {
        try {
          if (isSeeking[speaker]) return; // Don't update during seeking
          if (fill && audio.duration) {
            fill.style.width = (audio.currentTime / audio.duration) * 100 + "%";
          }
          if (time) {
            time.textContent = formatTime(audio.currentTime);
          }
        } catch (err) {
          console.error("[v0] Error in timeupdate:", err);
        }
      });

      audio.addEventListener("ended", () => {
        try {
          updatePlayIcon(speaker, false);
          if (fill) fill.style.width = "0%";
          if (time) time.textContent = "0:00";
        } catch (err) {
          console.error("[v0] Error in ended event:", err);
        }
      });

      audio.addEventListener("error", (err) => {
        console.error(`[v0] Audio error for speaker ${speaker}:`, err);
      });
    } catch (err) {
      console.error("[v0] Error binding audio events:", err);
    }
  }

  function updatePlayIcon(speaker, isPlaying) {
    try {
      const btn = speakerList.querySelector(`.play-btn[data-speaker="${speaker}"]`);
      if (!btn) return;
      if (isPlaying) {
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor" stroke="none"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>`;
      } else {
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5,3 19,12 5,21"/></svg>`;
      }
    } catch (err) {
      console.error("[v0] Error updating play icon:", err);
    }
  }

  // ---- Upload Flow ----
  function showUpload() {
    try {
      uploadSection.style.display = "";
      resultsSection.style.display = "none";
      downloadPdfBtn.disabled = true;
      downloadSummaryBtn.disabled = true;
      uploadArea.style.display = "";
      uploadProgress.style.display = "none";
    } catch (err) {
      console.error("[v0] Error showing upload:", err);
    }
  }

  function showResults() {
    try {
      uploadSection.style.display = "none";
      resultsSection.style.display = "";
      downloadPdfBtn.disabled = false;
      downloadSummaryBtn.disabled = false;
      console.log("[v0] showResults: downloadSummaryBtn disabled =", downloadSummaryBtn.disabled, downloadSummaryBtn);
      renderSpeakerCards();
      renderCaptions();
    } catch (err) {
      console.error("[v0] Error showing results:", err);
    }
  }

  function triggerNewUpload() {
    try {
      if (hasData) {
        confirmModal.classList.add("active");
      } else {
        fileInput.click();
      }
    } catch (err) {
      console.error("[v0] Error triggering new upload:", err);
    }
  }

  // Drag and drop
  uploadArea.addEventListener("click", (e) => {
    try {
      if (e.target === browseBtn || browseBtn.contains(e.target)) return;
      fileInput.click();
    } catch (err) {
      console.error("[v0] Error in upload area click:", err);
    }
  });

  browseBtn.addEventListener("click", (e) => {
    try {
      e.stopPropagation();
      fileInput.click();
    } catch (err) {
      console.error("[v0] Error in browse button click:", err);
    }
  });

  uploadArea.addEventListener("dragover", (e) => {
    try {
      e.preventDefault();
      uploadArea.classList.add("drag-over");
    } catch (err) {
      console.error("[v0] Error in dragover:", err);
    }
  });

  uploadArea.addEventListener("dragleave", () => {
    try {
      uploadArea.classList.remove("drag-over");
    } catch (err) {
      console.error("[v0] Error in dragleave:", err);
    }
  });

  uploadArea.addEventListener("drop", (e) => {
    try {
      e.preventDefault();
      uploadArea.classList.remove("drag-over");
      if (e.dataTransfer.files.length > 0) {
        handleFileSelected(e.dataTransfer.files[0]);
      }
    } catch (err) {
      console.error("[v0] Error in drop:", err);
    }
  });

  fileInput.addEventListener("change", () => {
    try {
      if (fileInput.files.length > 0) {
        handleFileSelected(fileInput.files[0]);
      }
    } catch (err) {
      console.error("[v0] Error in file input change:", err);
    }
  });

  function handleFileSelected(file) {
    try {
      if (hasData) {
        // Store the file temporarily and show confirmation
        window._pendingFile = file;
        confirmModal.classList.add("active");
        return;
      }
      processFile(file);
    } catch (err) {
      console.error("[v0] Error handling file selected:", err);
    }
  }

  async function processFile(file) {
    try {
      // Show progress
      uploadArea.style.display = "none";
      uploadProgress.style.display = "";
      uploadStatusText.textContent = `Uploading "${file.name}"...`;
      progressBarFill.style.width = "20%";

      try {
        // Upload to the transcription API
        const formData = new FormData();
        formData.append("file", file);

        uploadStatusText.textContent = "Transcribing your recording...";
        progressBarFill.style.width = "50%";

        // Fetch captions from AssemblyAI endpoint
        const captionsRes = await fetch("http://127.0.0.1:8000/deepgram/get_captions", {
          method: "POST",
          body: formData,
        });

        if (!captionsRes.ok) throw new Error("Failed to fetch captions");

        progressBarFill.style.width = "75%";
        uploadStatusText.textContent = "Loading audio segments...";

        function toConvertedPath(fileName) {
          try {
            const lastDot = fileName.lastIndexOf(".");
            const stem =
              lastDot === -1 ? fileName : fileName.slice(0, lastDot);

            return `./files/${stem}_16k.flac`;
          } catch (err) {
            console.error("[v0] Error converting path:", err);
            return `./files/${fileName}`;
          }
        }

        const audioFilePath = toConvertedPath(file.name)

        const captionsJson = await captionsRes.json();
        captionsData = captionsJson.diarization;


        // Fetch audio segments
        const segmentsRes = await fetch("http://127.0.0.1:8000/deepgram/get_audio_segments", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            "audio_file": audioFilePath,
            "diarization": captionsJson.diarization
          }),
        });

        if (segmentsRes.ok) {
          const segmentsJson = await segmentsRes.json();
          audioSegments = segmentsJson;
        }

        progressBarFill.style.width = "100%";
        uploadStatusText.textContent = "Done!";

        hasData = true;
        speakerMap = {};
        savePersistence();

        setTimeout(() => {
          showResults();
        }, 500);
      } catch (err) {
        console.error("[v0] Error processing file:", err);
        uploadStatusText.textContent = "Error: " + err.message;
        progressBarFill.style.width = "0%";
        setTimeout(() => {
          showUpload();
        }, 2500);
      }
    } catch (err) {
      console.error("[v0] Error in processFile:", err);
    }
  }

  // ---- Confirm Modal ----
  cancelUploadBtn.addEventListener("click", () => {
    try {
      confirmModal.classList.remove("active");
      window._pendingFile = null;
      // Reset file input
      fileInput.value = "";
    } catch (err) {
      console.error("[v0] Error in cancel upload:", err);
    }
  });

  confirmUploadBtn.addEventListener("click", () => {
    try {
      confirmModal.classList.remove("active");
      clearPersistence();
      hasData = false;
      showUpload();

      // If there was a pending file (from drop or input), process it
      if (window._pendingFile) {
        const f = window._pendingFile;
        window._pendingFile = null;
        processFile(f);
      } else {
        fileInput.click();
      }
    } catch (err) {
      console.error("[v0] Error in confirm upload:", err);
    }
  });

  // ---- New Upload ----
  newUploadBtn.addEventListener("click", triggerNewUpload);

  // ---- Unnamed Speakers Modal ----
  const unnamedSpeakersModal = document.getElementById("unnamedSpeakersModal");
  const unnamedSpeakersMsg = document.getElementById("unnamedSpeakersMsg");
  const goBackNamingBtn = document.getElementById("goBackNamingBtn");
  const downloadAnywayBtn = document.getElementById("downloadAnywayBtn");
  let pendingDownloadAction = null; // stores the function to call on "Download Anyway"

  function getUnnamedSpeakers() {
    const speakers = getUniqueSpeakers();
    return speakers.filter((spk) => !speakerMap[spk] || !speakerMap[spk].trim());
  }

  function checkSpeakersBeforeDownload(downloadFn) {
    const unnamed = getUnnamedSpeakers();
    if (unnamed.length === 0) {
      // All speakers named, proceed directly
      downloadFn();
    } else {
      // Show warning modal
      const labels = unnamed.map((spk) => `Speaker ${spk}`).join(", ");
      unnamedSpeakersMsg.textContent = `The following speakers have not been named: ${labels}. You can go back to assign names or download anyway.`;
      pendingDownloadAction = downloadFn;
      unnamedSpeakersModal.classList.add("active");
    }
  }

  goBackNamingBtn.addEventListener("click", () => {
    unnamedSpeakersModal.classList.remove("active");
    pendingDownloadAction = null;
  });

  downloadAnywayBtn.addEventListener("click", () => {
    unnamedSpeakersModal.classList.remove("active");
    if (pendingDownloadAction) {
      pendingDownloadAction();
      pendingDownloadAction = null;
    }
  });

  // ---- PDF Download ----
  downloadPdfBtn.addEventListener("click", () => checkSpeakersBeforeDownload(generatePdf));
  downloadSummaryBtn.addEventListener("click", () => checkSpeakersBeforeDownload(downloadSummary));

  async function downloadSummary() {
    try {
      downloadSummaryBtn.disabled = false;
      downloadSummaryBtn.textContent = "Generating...";

      // Build captions with speaker names applied
      const captions = captionsData.map((item) => ({
        timestamp: item.timestamp,
        speaker: getDisplayName(item.speaker),
        text: item.text,
      }));

      const res = await fetch("http://127.0.0.1:8000/summarize/get_summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ "captions" : captions }),
      });

      if (!res.ok) throw new Error("Failed to fetch summary");

      const data = await res.json();

      // Build PDF with summary and action items
      const { jsPDF } = window.jspdf;
      const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
      const margin = 20;
      const pageWidth = doc.internal.pageSize.getWidth();
      const usableWidth = pageWidth - margin * 2;
      let y = margin;

      // Title
      doc.setFont("helvetica", "bold");
      doc.setFontSize(20);
      doc.setTextColor(30, 30, 46);
      doc.text("Meeting Summary", margin, y);
      y += 8;

      // Date
      doc.setFont("helvetica", "normal");
      doc.setFontSize(10);
      doc.setTextColor(120, 120, 120);
      doc.text("Generated on " + new Date().toLocaleString(), margin, y);
      y += 4;

      doc.setDrawColor(200, 200, 200);
      doc.line(margin, y, pageWidth - margin, y);
      y += 10;

      // Summary
      doc.setFont("helvetica", "bold");
      doc.setFontSize(14);
      doc.setTextColor(15, 123, 108);
      doc.text("Summary", margin, y);
      y += 7;

      doc.setFont("helvetica", "normal");
      doc.setFontSize(11);
      doc.setTextColor(30, 30, 46);
      const summaryLines = doc.splitTextToSize(data.summary || "No summary available.", usableWidth);
      summaryLines.forEach((line) => {
        if (y > doc.internal.pageSize.getHeight() - margin) {
          doc.addPage();
          y = margin;
        }
        doc.text(line, margin, y);
        y += 5.5;
      });

      y += 8;

      // Action Items
      if (data.action_items) {
        if (y > doc.internal.pageSize.getHeight() - margin - 20) {
          doc.addPage();
          y = margin;
        }

        doc.setFont("helvetica", "bold");
        doc.setFontSize(14);
        doc.setTextColor(15, 123, 108);
        doc.text("Action Items", margin, y);
        y += 7;

        doc.setFont("helvetica", "normal");
        doc.setFontSize(11);
        doc.setTextColor(30, 30, 46);

        const items = data.action_items.filter((v) => v && v.trim());
        if (items.length === 0) {
          doc.text("No action items identified.", margin, y);
          y += 6;
        } else {
          items.forEach((item, idx) => {
            const bulletLines = doc.splitTextToSize(`${idx + 1}. ${item}`, usableWidth - 4);
            bulletLines.forEach((line) => {
              if (y > doc.internal.pageSize.getHeight() - margin) {
                doc.addPage();
                y = margin;
              }
              doc.text(line, margin, y);
              y += 5.5;
            });
            y += 2;
          });
        }
      }

      doc.save("meeting-summary.pdf");
    } catch (err) {
      console.error("[v0] Error downloading summary:", err);
      alert("Failed to generate summary: " + err.message);
    } finally {
      downloadSummaryBtn.disabled = false;
      downloadSummaryBtn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10 9 9 9 8 9"/>
        </svg>
        Download Summary`;
    }
  }

  function generatePdf() {
    try {
      const { jsPDF } = window.jspdf;
      const doc = new jsPDF({
        orientation: "portrait",
        unit: "mm",
        format: "a4",
      });

      const margin = 20;
      const pageWidth = doc.internal.pageSize.getWidth();
      const usableWidth = pageWidth - margin * 2;
      let y = margin;

      // Title
      doc.setFont("helvetica", "bold");
      doc.setFontSize(20);
      doc.text("Meeting Captions", margin, y);
      y += 8;

      // Date
      doc.setFont("helvetica", "normal");
      doc.setFontSize(10);
      doc.setTextColor(120, 120, 120);
      doc.text("Generated on " + new Date().toLocaleString(), margin, y);
      y += 4;

      // Separator
      doc.setDrawColor(200, 200, 200);
      doc.line(margin, y, pageWidth - margin, y);
      y += 8;

      // Speaker legend
      const speakers = getUniqueSpeakers();
      doc.setFontSize(11);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(30, 30, 46);
      doc.text("Speakers:", margin, y);
      y += 6;
      doc.setFont("helvetica", "normal");
      doc.setFontSize(10);
      speakers.forEach((spk) => {
        try {
          doc.setTextColor(80, 80, 80);
          doc.text(`${spk} = ${getDisplayName(spk)}`, margin + 4, y);
          y += 5;
        } catch (err) {
          console.error(`[v0] Error adding speaker ${spk} to PDF:`, err);
        }
      });
      y += 6;

      doc.line(margin, y, pageWidth - margin, y);
      y += 8;

      // Captions
      captionsData.forEach((item) => {
        try {
          const timeStr = `${formatTime(item.timestamp.start)} - ${formatTime(item.timestamp.end)}`;
          const speakerStr = getDisplayName(item.speaker);
          const text = item.text;

          // Check space
          const textLines = doc.splitTextToSize(text, usableWidth - 4);
          const blockHeight = 6 + 5 + textLines.length * 4.5 + 8;

          if (y + blockHeight > doc.internal.pageSize.getHeight() - margin) {
            doc.addPage();
            y = margin;
          }

          // Timestamp
          doc.setFont("courier", "normal");
          doc.setFontSize(9);
          doc.setTextColor(120, 120, 120);
          doc.text(timeStr, margin, y);
          y += 5;

          // Speaker
          doc.setFont("helvetica", "bold");
          doc.setFontSize(10);
          doc.setTextColor(15, 123, 108);
          doc.text(speakerStr, margin, y);
          y += 5;

          // Text
          doc.setFont("helvetica", "normal");
          doc.setFontSize(10);
          doc.setTextColor(30, 30, 46);
          textLines.forEach((line) => {
            try {
              if (y > doc.internal.pageSize.getHeight() - margin) {
                doc.addPage();
                y = margin;
              }
              doc.text(line, margin, y);
              y += 4.5;
            } catch (err) {
              console.error("[v0] Error adding PDF line:", err);
            }
          });

          y += 6;
        } catch (err) {
          console.error("[v0] Error adding caption to PDF:", err);
        }
      });

      doc.save("meeting-captions.pdf");
    } catch (err) {
      console.error("[v0] Error generating PDF:", err);
    }
  }

  // ---- Init ----
  function init() {
    try {
      const restored = loadPersistence();
      if (restored) {
        hasData = true;
        showResults();
      } else {
        showUpload();
      }
    } catch (err) {
      console.error("[v0] Error in init:", err);
    }
  }

  init();
})();
