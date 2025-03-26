<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apply for Jobs - InstantApply</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/auto_apply.css') }}">
</head>
<body>
    <header class="top-header">
        <div class="brand">INSTANTAPPLY</div>
        <nav>
            <ul>
                <li><a href="/profile">Profile</a></li>
                <li><a href="/dashboard">Dashboard</a></li>
                <li><a href="/applications">My Applications</a></li>
                <li><a href="/logout">Log Out</a></li>
            </ul>
        </nav>
    </header>

    <main>
        <section class="apply-section">
            <p class="description">One button is all you need!</p>

            <div class="action-container">
                <button class="big-apply-button">APPLY TO JOBS</button>
                <div id="status" class="status-message"></div>
            </div>
        </section>
    </main>

    <footer>
        <p>&copy; 2025 InstantApply</p>
    </footer>

    <script>
        document.querySelector('.big-apply-button').addEventListener('click', function() {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = "Applying to jobs... This may take a few moments.";
            statusDiv.className = "status-message processing";

            this.disabled = true;
            this.style.opacity = '0.5';

            fetch('/api/auto-apply', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                this.disabled = false;
                this.style.opacity = '1';
                if (data.message) {
                    statusDiv.textContent = data.message;
                    statusDiv.className = "status-message success";
                } else if (data.error) {
                    statusDiv.textContent = 'Error: ' + data.error;
                    statusDiv.className = "status-message error";
                } else {
                    statusDiv.textContent = 'Unexpected response.';
                    statusDiv.className = "status-message error";
                }
            })
            .catch(error => {
                this.disabled = false;
                this.style.opacity = '1';
                statusDiv.textContent = 'Error during auto-apply: ' + error;
                statusDiv.className = "status-message error";
            });
        });
    </script>
</body>
</html>
