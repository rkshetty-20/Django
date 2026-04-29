setInterval(() => {
    fetch('/')
    .then(res => res.text())
    .then(data => {
        document.getElementById('course-list').innerHTML = data;
    });
}, 5000);