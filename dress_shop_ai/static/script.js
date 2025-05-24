const userInput = document.getElementById('user-input').value;

fetch('/predict', {
    method: 'POST',
    body: new URLSearchParams({user_input: userInput}),
    headers: {'Content-Type': 'application/x-www-form-urlencoded'}
})
.then(response => response.json())
.then(data => {
    // Append the response to the chat area
    const chatArea = document.getElementById('chat-area');
    const msgDiv = document.createElement('div');
    msgDiv.textContent = data.response;
    chatArea.appendChild(msgDiv);
});

function updateChart() {
    const date = document.getElementById('sales-date').value;
    const groupBy = document.getElementById('group-by').value;
    if (!date) {
        alert('Please select a date!');
        return;
    }
    fetch(`/update_chart?date=${date}&group_by=${groupBy}`)
        .then(response => response.json())
        .then(data => {
            // ... (rest of your code)
        });
}
