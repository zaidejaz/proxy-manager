document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token
    const getCsrfToken = () => {
        const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (!token) {
            console.error('CSRF token not found');
        }
        return token;
    };

    // Helper function to show flash messages
    const showFlashMessage = (message, type = 'success') => {
        const flashMessage = document.createElement('div');
        flashMessage.className = `alert rounded-md p-4 mb-3 ${type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'} transition-opacity duration-500`;
        flashMessage.textContent = message;

        // Find the container to insert the flash message
        const container = document.querySelector('.px-6.py-3');
        if (container) {
            container.insertAdjacentElement('beforeend', flashMessage);
            setTimeout(() => {
                flashMessage.style.opacity = '0';
                setTimeout(() => flashMessage.remove(), 500);
            }, 3000);
        }
    };

    // Elements
    const selectAllCheckbox = document.getElementById('selectAll');
    const deleteSelectedButton = document.getElementById('deleteSelected');
    const selectedCountSpan = document.getElementById('selectedCount');
    const proxyCheckboxes = document.querySelectorAll('.proxy-select');

    // Update selected count and button state
    const updateSelectedState = () => {
        const checkedBoxes = document.querySelectorAll('.proxy-select:checked');
        const count = checkedBoxes.length;
        
        selectedCountSpan.textContent = count;
        deleteSelectedButton.disabled = count === 0;
        
        // Update select all checkbox state
        if (selectAllCheckbox) {
            const totalCheckboxes = document.querySelectorAll('.proxy-select').length;
            selectAllCheckbox.checked = count === totalCheckboxes && totalCheckboxes > 0;
            selectAllCheckbox.indeterminate = count > 0 && count < totalCheckboxes;
        }
    };

    // Handle form submissions
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Select all checkbox functionality
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const proxyCheckboxes = document.querySelectorAll('.proxy-select');
            proxyCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateSelectedState();
        });
    }

    // Individual checkbox change handler
    proxyCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedState);
    });

    // Delete selected proxies
    if (deleteSelectedButton) {
        deleteSelectedButton.addEventListener('click', async function() {
            const selectedProxies = Array.from(document.querySelectorAll('.proxy-select:checked'))
                .map(checkbox => checkbox.value);

            if (selectedProxies.length === 0) {
                showFlashMessage('Please select proxies to delete', 'danger');
                return;
            }

            if (confirm(`Are you sure you want to delete ${selectedProxies.length} proxies?`)) {
                try {
                    const response = await fetch('/proxies/bulk-delete', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCsrfToken()
                        },
                        body: JSON.stringify({ proxy_ids: selectedProxies }),
                        credentials: 'same-origin'
                    });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.message || 'Failed to delete proxies');
                    }

                    // Remove selected rows
                    selectedProxies.forEach(proxyId => {
                        const checkbox = document.querySelector(`.proxy-select[value="${proxyId}"]`);
                        if (checkbox) {
                            checkbox.closest('tr').remove();
                        }
                    });
                    updateSelectedState();
                    showFlashMessage(`Successfully deleted ${selectedProxies.length} proxies`);
                } catch (error) {
                    console.error('Error:', error);
                    showFlashMessage(error.message || 'An error occurred while deleting proxies', 'danger');
                }
            }
        });
    }

    // Individual proxy deletion
    document.querySelectorAll('.delete-proxy').forEach(button => {
        button.addEventListener('click', async function() {
            const proxyId = this.dataset.proxyId;
            if (confirm('Are you sure you want to delete this proxy?')) {
                try {
                    const response = await fetch(`/proxies/${proxyId}/delete`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCsrfToken()
                        },
                        credentials: 'same-origin'
                    });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.message || 'Failed to delete proxy');
                    }

                    this.closest('tr').remove();
                    updateSelectedState();
                    showFlashMessage('Proxy deleted successfully');
                } catch (error) {
                    console.error('Error:', error);
                    showFlashMessage(error.message || 'An error occurred while deleting the proxy', 'danger');
                }
            }
        });
    });

    // Initial state update
    updateSelectedState();
});