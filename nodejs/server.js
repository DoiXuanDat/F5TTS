const express = require('express');
const multer = require('multer');
const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');

const app = express();
const upload = multer({ dest: 'uploads/' });
const PORT = process.env.PORT || 3001;

app.use(express.static('public'));

app.post('/generate', upload.single('referenceAudio'), async (req, res) => {
    try {
        console.log('🔵 File:', req.file);
        console.log('🔵 Body:', req.body);

        // Validate inputs
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }   
        if (!req.body.ref_text || !req.body.gen_text) {
            return res.status(400).json({ error: 'Both reference and generation texts are required' });
        }

        // Create FormData with correct field names
        const formData = new FormData();
        formData.append('ref_audio', fs.createReadStream(req.file.path), {
            filename: 'audio.wav',
            contentType: 'audio/wav'
        });
        formData.append('ref_text', req.body.ref_text);
        formData.append('gen_text', req.body.gen_text);

        console.log("🔵 Sending request to FastAPI...");

        const response = await axios.post('http://localhost:8000/generate-audio/', 
            formData, 
            {
                headers: {
                    ...formData.getHeaders(),
                    'Accept': 'application/json'
                },
                responseType: 'arraybuffer',
                maxContentLength: Infinity,
                maxBodyLength: Infinity
            }
        );

        // Send audio response
        res.contentType('audio/wav');
        res.send(response.data);

    } catch (error) {
        console.error('🔴 Error:', error.message);
        if (error.response) {
            console.error('🔴 Response data:', error.response.data);
            console.error('🔴 Response status:', error.response.status);
        }
        res.status(500).json({ 
            error: 'Failed to generate audio',
            details: error.message
        });
    } finally {
        // Clean up uploaded file
        if (req.file) {
            fs.unlink(req.file.path, (err) => {
                if (err) console.error('🔴 Error deleting file:', err);
            });
        }
    }
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});