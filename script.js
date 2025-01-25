document.getElementById('fetch-formats').addEventListener('click', async () => {
    const url = document.getElementById('url').value;
    const formatsDropdown = document.getElementById('formats');
    
    if (!url) {
        alert('Please enter a URL first');
        return;
    }

    try {
        const response = await fetch(`http://localhost:5000/api/fetch-formats?url=${encodeURIComponent(url)}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch formats');
        }

        formatsDropdown.innerHTML = '';
        
        data.formats.forEach(format => {
            const option = document.createElement('option');
            option.value = format.format_id;
            option.textContent = `${format.resolution} (${format.ext.toUpperCase()}) - ${format.requires_ffmpeg ? 'Needs FFmpeg' : 'Direct download'}`;
            formatsDropdown.appendChild(option);
        });

    } catch (error) {
        alert(`Error: ${error.message}`);
    }
});

const downloadFile = async () => {
    const url = document.getElementById('url').value;
    const formatId = document.getElementById('formats').value;

    if (!url || !formatId) {
        alert('Please select a format before downloading.');
        return;
    }

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);

        const response = await fetch('http://localhost:5000/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url,
                format_id: formatId
            }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
            const error = await response.text();
            throw new Error(error || 'Download failed');
        }

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `video.${formatId.split('/').pop() || 'mp4'}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);

    } catch (error) {
        alert(error.name === 'AbortError' 
            ? 'Download timed out (30 seconds)' 
            : `Download failed: ${error.message}`);
    }
};

document.getElementById('download-file').addEventListener('click', downloadFile);