// This file handles real-time seat availability updates using asynchronous API calls (AJAX)
// It fetches the latest seat counts from the Django backend without reloading the page.

document.addEventListener('DOMContentLoaded', () => {
    function loadAllSeats() {
        // Find all elements displaying a seat counter
        const seatCounters = document.querySelectorAll('.seat-counter');
        
        seatCounters.forEach(counter => {
            const courseId = counter.dataset.courseId;
            if (courseId) {
                // Fetch the latest seat data from the backend API
                fetch(`/api/seats/${courseId}/`)
                    .then(response => response.json())
                    .then(data => {
                        // Update the text dynamically
                        counter.innerText = data.available_seats;
                        
                        // Optional: Add visual cues if seats are running out
                        if (data.available_seats < 2) {
                            counter.classList.add('text-danger', 'animate-pulse');
                            counter.classList.remove('text-success');
                        } else {
                            counter.classList.add('text-success');
                            counter.classList.remove('text-danger', 'animate-pulse');
                        }
                        
                        // Disable the button if fully booked
                        if (data.available_seats <= 0) {
                            const button = counter.closest('.card').querySelector('button[type="submit"]');
                            if (button) {
                                button.disabled = true;
                                button.innerText = 'Fully Booked';
                            }
                        }
                    })
                    .catch(error => console.error('Error fetching seat data:', error));
            }
        });
    }

    // Call it once immediately when the page loads
    loadAllSeats();
    
    // Set up a recurring call every 5 seconds to keep data fresh (Real-time updates)
    setInterval(loadAllSeats, 5000);
});
