
        function showGroup(groupName) {
            const frame = document.getElementById('contentFrame');
            frame.src = `${groupName}.html`;

            document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
            const current = Array.from(document.querySelectorAll('.nav-item'))
                .find(item => item.querySelector('.group-name').textContent === groupName);
            if (current) {
                current.classList.add('active');
            }
        }
    