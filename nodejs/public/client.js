let currentSegmentPaths = [];
let segmentCount = 1;
let segmentDurations = [];

document.addEventListener('DOMContentLoaded', () => {
    const addSegmentBtn = document.querySelector('.add-segment-btn');
    const textSegmentsContainer = document.getElementById('textSegmentsContainer');
    
    addSegmentBtn.addEventListener('click', () => {
        segmentCount++;
        const newSegment = createSegmentElement(segmentCount);
        textSegmentsContainer.appendChild(newSegment);
        updateRemoveButtons();
    });
    
    textSegmentsContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-segment')) {
            const index = Array.from(textSegmentsContainer.children).indexOf(e.target.closest('.segment-group'));
            segmentDurations.splice(index, 1);
            e.target.closest('.segment-group').remove();
            updateSegmentNumbers();
            updateRemoveButtons();
            updateTimingDisplay();
        }
    });
    
    document.getElementById('ttsForm').addEventListener('submit', handleFormSubmit);
    document.getElementById('downloadCombinedSRT').addEventListener('click', downloadCombinedSRT);
    document.getElementById('showTimingInfo').addEventListener('click', toggleTimingInfo);
});

function createSegmentElement(number) {
    const div = document.createElement('div');
    div.className = 'segment-group';
    div.innerHTML = `
        <div class="segment-header">
            <h3>Text Segment ${number}</h3>
            <button type="button" class="btn remove-segment">Remove</button>
        </div>
        <textarea class="gen-text-segment" required placeholder="Enter text to generate"></textarea>
        <div class="timing-info" style="display: none;">
            <span class="duration">Duration: --</span>
            <span class="start-time">Start: --</span>
            <span class="end-time">End: --</span>
        </div>
    `;
    return div;
}

function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = (seconds % 60).toFixed(3);
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.padStart(6, '0')}`;
}

function updateTimingDisplay() {
    const segments = document.querySelectorAll('.segment-group');
    let currentTime = 0;
    
    segments.forEach((segment, index) => {
        const duration = segmentDurations[index] || 0;
        const timingInfo = segment.querySelector('.timing-info');
        
        if (timingInfo) {
            timingInfo.querySelector('.duration').textContent = `Duration: ${duration.toFixed(3)}s`;
            timingInfo.querySelector('.start-time').textContent = `Start: ${formatTime(currentTime)}`;
            timingInfo.querySelector('.end-time').textContent = `End: ${formatTime(currentTime + duration)}`;
        }
        
        currentTime += duration + 0.1; // Add 100ms gap between segments
    });
    
    // Update total duration display
    const totalDuration = segmentDurations.reduce((sum, duration) => sum + duration, 0);
    document.getElementById('totalDuration').textContent = `Total Duration: ${totalDuration.toFixed(3)}s`;
}

function toggleTimingInfo() {
    const timingInfos = document.querySelectorAll('.timing-info');
    const isVisible = timingInfos[0]?.style.display !== 'none';
    
    timingInfos.forEach(info => {
        info.style.display = isVisible ? 'none' : 'block';
    });
    
    document.getElementById('showTimingInfo').textContent = 
        isVisible ? 'Show Timing Info' : 'Hide Timing Info';
}

// client.js - Simplified handleFormSubmit function without timeouts

async function handleFormSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const loadingDiv = document.getElementById('loading');
    const progressInfo = document.getElementById('progressInfo');
    const errorDiv = document.getElementById('error');
    const resultDiv = document.getElementById('result');
    
    // Reset UI and data
    errorDiv.textContent = '';
    resultDiv.style.display = 'none';
    loadingDiv.style.display = 'flex';
    currentSegmentPaths = [];
    segmentDurations = [];
    
    const segments = Array.from(document.querySelectorAll('.gen-text-segment'))
        .map(textarea => textarea.value.trim())
        .filter(text => text.length > 0);
    
    try {
        const results = [];
        for (let i = 0; i < segments.length; i++) {
            progressInfo.textContent = `Processing segment ${i + 1} of ${segments.length}...`;
            
            const formData = new FormData(form);
            formData.set('gen_text', segments[i]);
            formData.set('segment_index', i.toString());
            
            const response = await fetch('/generate-audio', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            
            const data = await response.json();
            results.push(data);
            currentSegmentPaths.push(data.full_path);
            
            // Extract duration from metadata
            const audioElement = new Audio(`/generated_audio_files/${data.filename}`);
            await new Promise(resolve => {
                audioElement.addEventListener('loadedmetadata', () => {
                    segmentDurations[i] = audioElement.duration;
                    resolve();
                });
            });
        }
        
        // Combine audio segments
        progressInfo.textContent = 'Combining segments...';
        const combinedResponse = await fetch('/combine-audio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paths: currentSegmentPaths })
        });
        
        if (!combinedResponse.ok) {
            throw new Error('Failed to combine audio segments');
        }
        
        const combinedData = await combinedResponse.json();
        
        // Update UI
        document.getElementById('finalAudio').src = `/generated_audio_files/${combinedData.filename}`;
        displaySegmentResults(results);
        updateTimingDisplay();
        resultDiv.style.display = 'block';
        
    } catch (error) {
        console.error('Error:', error);
        errorDiv.textContent = error.message;
    } finally {
        loadingDiv.style.display = 'none';
        progressInfo.textContent = '';
    }
}


// Add this to your client.js
async function downloadCombinedSRT() {
    try {
        if (!currentSegmentPaths.length) {
            throw new Error('No segments available to generate combined SRT');
        }

        const response = await fetch('/generate-combined-srt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ paths: currentSegmentPaths })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to generate combined SRT');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'combined.srt';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        
    } catch (error) {
        console.error('Error downloading combined SRT:', error);
        const errorDiv = document.getElementById('error');
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
        
        // Auto-hide error after 5 seconds
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 10000000);
    }
}

function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
}

function displaySegmentResults(results) {
    const container = document.getElementById('segmentResults');
    container.innerHTML = '';
    
    results.forEach((result, index) => {
        const div = document.createElement('div');
        div.className = 'segment-result';
        div.innerHTML = `
            <h3>Segment ${index + 1}</h3>
            <div class="segment-timing">
                Duration: ${segmentDurations[index]?.toFixed(3)}s
            </div>
            <audio controls src="/generated_audio_files/${result.filename}"></audio>
        `;
        container.appendChild(div);
    });
}