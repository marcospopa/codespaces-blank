document.addEventListener('DOMContentLoaded', () => {
    const convertBtn = document.getElementById('convert-btn');
    const urlInput = document.getElementById('youtube-url');
    const statusMessage = document.getElementById('status-message');
    const resultsContainer = document.getElementById('results-container');
    const videoTitleElement = document.getElementById('video-title');
    const downloadLinksContainer = document.getElementById('download-links');

    // Define the backend API URL. This will be the address of the Flask service
    // once orchestrated by Docker Compose.
    const API_URL = 'https://glorious-goldfish-qv5rpgpp46rhxv9q-5001.app.github.dev/api';

    const setStatus = (message, type = 'loading') => {
        statusMessage.textContent = message;
        statusMessage.className = type;
    };

    const resetUI = () => {
        convertBtn.disabled = false;
        resultsContainer.classList.add('hidden');
        downloadLinksContainer.innerHTML = '';
        videoTitleElement.textContent = '';
    };

    const showResults = (title, downloadData) => {
        videoTitleElement.textContent = title;

        // Clear previous links
        downloadLinksContainer.innerHTML = '';

        // Create and append new download links
        const qualityOrder = ['low', 'medium', 'high'];
        qualityOrder.forEach(quality => {
            if (downloadData[quality]) {
                const data = downloadData[quality];
                const button = document.createElement('a');
                button.href = `${API_URL}${data.url}`;
                button.textContent = `Download ${quality.charAt(0).toUpperCase() + quality.slice(1)} Quality MP3`;
                button.className = `download-button ${quality}`;
                button.setAttribute('download', data.filename); // Suggest a filename to the browser
                downloadLinksContainer.appendChild(button);
            }
        });

        resultsContainer.classList.remove('hidden');
    };

    convertBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) {
            setStatus('Please enter a YouTube URL.', 'error');
            return;
        }

        // Basic URL validation
        if (!/^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/.test(url)) {
            setStatus('Please enter a valid YouTube URL.', 'error');
            return;
        }

        // Reset UI and show loading state
        resetUI();
        setStatus('Converting... This may take a moment.');
        convertBtn.disabled = true;

        try {
            const response = await fetch(`${API_URL}/convert`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url }),
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'An unknown error occurred.');
            }

            setStatus('Conversion successful!', 'success');
            showResults(result.video_title, result.downloads);

        } catch (error) {
            console.error('Conversion failed:', error);
            setStatus(`Error: ${error.message}`, 'error');
        } finally {
            convertBtn.disabled = false;
        }
    });

    // Allow pressing Enter to trigger conversion
    urlInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault(); // Prevent form submission if it were in a form
            convertBtn.click();
        }
    });
});