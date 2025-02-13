const express = require('express');
const multer = require('multer');
const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');
const path = require('path');

const app = express();
const upload = multer({ dest: 'uploads/' });
const PORT = process.env.PORT || 3001;

app.use(express.static('public'));

// Add endpoint to serve generated audio files
app.use('/generated_audio_files', express.static('/app/generated_audio_files'));

app.post('/generate-audio', upload.single('ref_audio'), async (req, res) => {
    try {
        console.log('🔵 File:', req.file);
        console.log('🔵 Body:', req.body);

        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }   
        if (!req.body.ref_text || !req.body.gen_text) {
            return res.status(400).json({ error: 'Both reference and generation texts are required' });
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

        console.log("🔵 Sending request to FastAPI...");

        const response = await axios.post('http://localhost:8000/generate-audio/', 
            formData, 
            {
                headers: {
                    ...formData.getHeaders()
                }
            }
        );

        // Return the audio file path from FastAPI response
        res.json(response.data);

    } catch (error) {
        console.error('🔴 Error:', error.message);
        if (error.response) {
            console.error('🔴 Response data:', error.response.data);
            console.error('🔴 Response status:', error.response.status);
            res.status(error.response.status).json({ 
                error: 'Failed to generate audio',
                details: error.response.data
            });
        } else {
            res.status(500).json({ 
                error: 'Failed to generate audio',
                details: error.message
            });
        }
    } finally {
        // Clean up uploaded file
        if (req.file) {
            fs.unlink(req.file.path, (err) => {
                if (err) console.error('🔴 Error deleting file:', err);
            });
        }
    }
});

app.post('/generate-srt', express.json(), async (req, res) => {
    try {
        const { audioPath } = req.body;
        
        if (!audioPath) {
            return res.status(400).json({
                error: 'Audio path is required'
            });
        }

        // Create form data
        const formData = new FormData();
        formData.append('audio_path', audioPath);

        // Make request to FastAPI
        const response = await axios.post('http://localhost:8000/generate-srt/',
            formData,
            {
                headers: {
                    ...formData.getHeaders()
                },
                responseType: 'arraybuffer',  // Changed from 'blob' to 'arraybuffer'
                validateStatus: false
            }
        );

        // Handle error responses
        if (response.status !== 200) {
            // Convert arraybuffer to string for error messages
            const errorText = Buffer.from(response.data).toString('utf-8');
            let errorMessage;
            try {
                const errorJson = JSON.parse(errorText);
                errorMessage = errorJson.detail || 'Unknown error occurred';
            } catch {
                errorMessage = errorText || 'Unknown error occurred';
            }
            return res.status(response.status).json({
                error: 'Failed to generate SRT file',
                details: errorMessage
            });
        }

        // Success response
        res.setHeader('Content-Type', 'text/srt');
        res.setHeader('Content-Disposition', 'attachment; filename=generated.srt');
        res.send(Buffer.from(response.data));

    } catch (error) {
        console.error('🔴 Error generating SRT:', error.message);
        res.status(500).json({
            error: 'Failed to generate SRT file',
            details: error.message
        });
    }
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});