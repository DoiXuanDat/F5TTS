const express = require('express');
const multer = require('multer');
const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');
const path = require('path');
const archiver = require('archiver');
const { getAudioDurationInSeconds } = require('get-audio-duration');

const app = express();
const upload = multer({ dest: 'uploads/' });
const PORT = process.env.PORT || 3001;

app.use(express.static('public'));
app.use(express.json());
app.use('/generated_audio_files', express.static('/app/generated_audio_files'));


// Utility function to validate audio duration
const validateAudioDuration = async (filePath) => {
    try {
        const duration = await getAudioDurationInSeconds(filePath);
        console.log(`Audio duration: ${duration} seconds`);
        // Cho phép các file có độ dài từ 0.1s đến 5 phút
        return duration >= 0.1 && duration <= 300;
    } catch (error) {
        console.error('Error validating audio duration:', error);
        return false;
    }
};

// Enhanced error handling middleware
app.use((err, req, res, next) => {
    console.error('🔴 Error:', err);
    res.status(err.status || 500).json({
        error: err.message || 'Internal server error',
        details: process.env.NODE_ENV === 'development' ? err.stack : undefined
    });
});

// Enhanced endpoint for handling multiple text segments
app.post('/generate-audio', upload.single('ref_audio'), async (req, res) => {
    const startTime = Date.now();
    let uploadedFilePath = null;
    
    try {
        console.log('🔵 Processing audio generation request');
        
        if (!req.file) {
            throw new Error('No reference audio file uploaded');
        }
        
        uploadedFilePath = req.file.path;
        
        if (!req.body.ref_text || !req.body.gen_text) {
            throw new Error('Reference text and generation text are required');
        }

        const formData = new FormData();
        formData.append('ref_audio', fs.createReadStream(req.file.path), {
            filename: 'audio.wav',
            contentType: 'audio/wav'
        });
        formData.append('ref_text', req.body.ref_text);
        formData.append('gen_text', req.body.gen_text);
        formData.append('remove_silence', req.body.remove_silence || 'false');
        formData.append('cross_fade_duration', req.body.cross_fade_duration || '0.15');
        formData.append('speed', req.body.speed || '1.0');
        formData.append('segment_index', req.body.segment_index || '0');

        console.log("🔵 Sending request to FastAPI");

        const response = await axios.post(
            'http://localhost:8000/generate-audio/',
            formData,
            { 
                headers: { ...formData.getHeaders() },
                timeout: 300000 // 5 minute timeout
            }
        );

        // Validate generated audio
        const isValidDuration = await validateAudioDuration(response.data.full_path);
        if (!isValidDuration) {
            throw new Error('Generated audio duration is invalid or file is corrupted');
        }

        // Add timing information
        const duration = await getAudioDurationInSeconds(response.data.full_path);
        response.data.duration = duration;

        // Add timing information to response
        const processTime = (Date.now() - startTime) / 1000;
        response.data.processTime = processTime;

        res.json(response.data);

    } catch (error) {
        console.error('🔴 Error:', error.message);
        handleError(error, res);
    } finally {
        // Clean up uploaded file
        if (uploadedFilePath && fs.existsSync(uploadedFilePath)) {
            fs.unlink(uploadedFilePath, (err) => {
                if (err) console.error('🔴 Error deleting uploaded file:', err);
            });
        }
    }
});

// Enhanced endpoint for combining audio segments
app.post('/combine-audio', async (req, res) => {
    try {
        const { paths } = req.body;
        
        if (!paths || !Array.isArray(paths) || paths.length === 0) {
            throw new Error('Valid array of audio paths is required');
        }

        // Validate each path exists and check duration
        let totalDuration = 0;
        for (const path of paths) {
            if (!fs.existsSync(path)) {
                throw new Error(`Audio file not found: ${path}`);
            }
            
            const duration = await getAudioDurationInSeconds(path);
            totalDuration += duration;
        }

        const response = await axios.post(
            'http://localhost:8000/combine-audio-segments/',
            paths,
            { 
                headers: { 'Content-Type': 'application/json' },
                timeout: 300000
            }
        );

        // Validate combined audio
        const finalDuration = await getAudioDurationInSeconds(response.data.full_path);
        if (Math.abs(finalDuration - totalDuration) > paths.length * 0.1) { // Allow for crossfade gaps
            console.warn(`Duration mismatch - Expected: ${totalDuration}, Actual: ${finalDuration}`);
        }

        response.data.total_duration = finalDuration;
        res.json(response.data);

    } catch (error) {
        console.error('🔴 Error combining audio:', error.message);
        handleError(error, res);
    }
});

// Enhanced SRT generation endpoint
app.post('/generate-srt', async (req, res) => {
    try {
        const { audioPath } = req.body;
        
        if (!audioPath || !fs.existsSync(audioPath)) {
            throw new Error('Valid audio path is required');
        }

        // Create FormData for FastAPI request
        const formData = new FormData();
        formData.append('audio_path', audioPath);

        const response = await axios.post(
            'http://localhost:8000/generate-srt/',
            formData,
            {
                headers: { ...formData.getHeaders() },
                responseType: 'arraybuffer',
                timeout: 60000
            }
        );

        // Read metadata file if exists
        const metadataPath = audioPath.replace('.wav', '.json');
        if (fs.existsSync(metadataPath)) {
            const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf-8'));
            res.setHeader('X-Audio-Duration', metadata.actual_duration);
            res.setHeader('X-Scale-Factor', metadata.scale_factor);
        }

        // Set appropriate headers for SRT file download
        res.setHeader('Content-Type', 'application/x-subrip');
        res.setHeader('Content-Disposition', 'attachment; filename=generated.srt');
        res.send(Buffer.from(response.data));

    } catch (error) {
        console.error('🔴 Error generating SRT:', error.message);
        handleError(error, res);
    }
});

// Enhanced endpoint for combined SRT generation
app.post('/generate-combined-srt', async (req, res) => {
    try {
        const { paths } = req.body;
        
        if (!paths || !Array.isArray(paths) || paths.length === 0) {
            throw new Error('Valid array of audio paths is required');
        }

        // Validate all paths exist
        for (const path of paths) {
            if (!fs.existsSync(path)) {
                throw new Error(`Audio file not found: ${path}`);
            }
        }

        const response = await axios.post(
            'http://localhost:8000/generate-combined-srt/',
            paths,
            {
                headers: { 'Content-Type': 'application/json' },
                responseType: 'arraybuffer',
                timeout: 120000
            }
        );

        // Set appropriate headers for SRT file download
        res.setHeader('Content-Type', 'application/x-subrip');
        res.setHeader('Content-Disposition', 'attachment; filename=combined.srt');
        res.send(Buffer.from(response.data));

    } catch (error) {
        console.error('🔴 Error generating combined SRT:', error.message);
        handleError(error, res);
    }
});

// Enhanced endpoint for downloading all SRTs as ZIP
app.post('/generate-all-srt', async (req, res) => {
    try {
        const { paths } = req.body;
        
        if (!paths || !Array.isArray(paths) || paths.length === 0) {
            throw new Error('Valid array of audio paths is required');
        }

        const archive = archiver('zip', { zlib: { level: 9 } });
        
        // Set appropriate headers for ZIP file download
        res.setHeader('Content-Type', 'application/zip');
        res.setHeader('Content-Disposition', 'attachment; filename=all_segments.zip');
        
        archive.pipe(res);

        // Process each audio file
        for (let i = 0; i < paths.length; i++) {
            const formData = new FormData();
            formData.append('audio_path', paths[i]);

            try {
                const response = await axios.post(
                    'http://localhost:8000/generate-srt/',
                    formData,
                    {
                        headers: { ...formData.getHeaders() },
                        responseType: 'arraybuffer',
                        timeout: 60000
                    }
                );

                // Add SRT file to ZIP
                archive.append(Buffer.from(response.data), { name: `segment_${i + 1}.srt` });

                // Include metadata if available
                const metadataPath = paths[i].replace('.wav', '.json');
                if (fs.existsSync(metadataPath)) {
                    const metadata = fs.readFileSync(metadataPath);
                    archive.append(metadata, { name: `segment_${i + 1}_metadata.json` });
                }
            } catch (error) {
                console.error(`🔴 Error processing segment ${i + 1}:`, error.message);
            }
        }

        await archive.finalize();

    } catch (error) {
        console.error('🔴 Error generating SRT ZIP:', error.message);
        handleError(error, res);
    }
});

// Enhanced error handling utility
function handleError(error, res) {
    if (error.response) {
        const status = error.response.status || 500;
        const message = error.response.data?.detail || error.response.data || error.message;
        const errorResponse = {
            error: message,
            status: status,
            timestamp: new Date().toISOString()
        };
        res.status(status).json(errorResponse);
    } else {
        res.status(500).json({
            error: error.message,
            status: 500,
            timestamp: new Date().toISOString()
        });
    }
}

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});