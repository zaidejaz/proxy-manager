document.addEventListener('DOMContentLoaded', function() {
    // Select all checkbox functionality
    const selectAllCheckbox = document.getElementById('selectAll');
    const proxyCheckboxes = document.querySelectorAll('.proxy-select');

    selectAllCheckbox?.addEventListener('change', function() {
        proxyCheckboxes.forEach(checkbox => {
            checkbox.checked = selectAllCheckbox.checked;
        });
    });

    // Delete selected proxies
    const deleteSelectedButton = document.getElementById('deleteSelected');
    deleteSelectedButton?.addEventListener('click', async function() {
        const selectedProxies = Array.from(proxyCheckboxes)
            .filter(checkbox => checkbox.checked)
            .map(checkbox => checkbox.value);

        if (selectedProxies.length === 0) {
            alert('Please select proxies to delete');
            return;
        }

        if (confirm('Are you sure you want to delete the selected proxies?')) {
            try {
                const response = await fetch('/api/proxies/bulk-delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ proxy_ids: selectedProxies }),
                });

                if (response.ok) {
                    window.location.reload();
                } else {
                    alert('Failed to delete proxies');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while deleting proxies');
            }
        }
    });

    // Individual proxy deletion
    document.querySelectorAll('.delete-proxy').forEach(button => {
        button.addEventListener('click', async function() {
            const proxyId = this.dataset.proxyId;
            
            if (confirm('Are you sure you want to delete this proxy?')) {
                try {
                    const response = await fetch(`/proxies/${proxyId}/delete`, {
                        method: 'POST',
                    });

                    if (response.ok) {
                        window.location.reload();
                    } else {
                        alert('Failed to delete proxy');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    alert('An error occurred while deleting the proxy');
                }
            }
        });
    });

    // Edit proxy functionality
    document.querySelectorAll('.edit-proxy').forEach(button => {
        button.addEventListener('click', function() {
            const proxyId = this.dataset.proxyId;
            const row = this.closest('tr');
            
            const ip = row.cells[1].textContent;
            const port = row.cells[2].textContent;
            const username = row.cells[3].textContent;

            // Populate the edit modal
            document.querySelector('#editProxyModal input[name="ip"]').value = ip;
            document.querySelector('#editProxyModal input[name="port"]').value = port;
            document.querySelector('#editProxyModal input[name="username"]').value = username;
            document.querySelector('#editProxyModal input[name="proxy_id"]').value = proxyId;

            // Show the modal
            const editModal = new bootstrap.Modal(document.getElementById('editProxyModal'));
            editModal.show();
        });
    });
});