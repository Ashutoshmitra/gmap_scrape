document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const uploadForm = document.getElementById('uploadForm');
    const uploadButton = document.getElementById('uploadButton');
    const progressLog = document.getElementById('progressLog');
    const downloadSection = document.getElementById('downloadSection');
    const downloadButton = document.getElementById('downloadButton');
    
    let processedFile = null;

    socket.on('progress', (data) => {
        const messageElement = document.createElement('div');
        messageElement.textContent = data.message;
        progressLog.appendChild(messageElement);
        progressLog.scrollTop = progressLog.scrollHeight;
    });

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const fileInput = document.getElementById('fileInput');
        const file = fileInput.files[0];
        
        if (!file) {
            alert('Please select a file first.');
            return;
        }

        if (!file.name.endsWith('.xlsx')) {
            alert('Please upload an Excel (.xlsx) file.');
            return;
        }

        // Clear previous logs and hide download section
        progressLog.innerHTML = '';
        downloadSection.classList.add('hidden');
        uploadButton.disabled = true;
        uploadButton.textContent = 'Processing...';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const blob = await response.blob();
                processedFile = new File([blob], 'processed_addresses.xlsx', {
                    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                });
                
                downloadSection.classList.remove('hidden');
                progressLog.innerHTML += '<div>Processing completed! You can now download the processed file.</div>';
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Processing failed');
            }
        } catch (error) {
            progressLog.innerHTML += `<div style="color: red;">Error: ${error.message}</div>`;
        } finally {
            uploadButton.disabled = false;
            uploadButton.textContent = 'Process Addresses';
        }
    });

    downloadButton.addEventListener('click', () => {
        if (processedFile) {
            const url = URL.createObjectURL(processedFile);
            const a = document.createElement('a');
            a.href = url;
            a.download = processedFile.name;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    });
});
