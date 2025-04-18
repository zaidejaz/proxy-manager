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

    // Listen for close-modal events and ensure modals are properly hidden
    window.addEventListener('close-modal', function(event) {
        if (event && event.detail && event.detail.id) {
            const modalId = event.detail.id;
            console.log(`Modal close event received for ${modalId}`);
            
            // Ensure Alpine.js modal state is reset
            if (window.Alpine) {
                try {
                    const modalRoot = document.querySelector('[x-data="{ openModals: {} }"]');
                    if (modalRoot) {
                        const scope = window.Alpine.$data(modalRoot);
                        if (scope && scope.openModals) {
                            scope.openModals[modalId] = false;
                            console.log(`Set ${modalId} to false in Alpine data`);
                        }
                    }
                } catch (err) {
                    console.error('Error updating Alpine.js modal state:', err);
                }
            }
            
            // Reset form if exists
            try {
                const modalElement = document.querySelector(`[x-show="openModals['${modalId}']"]`);
                if (modalElement) {
                    // Reset any forms in the modal
                    const forms = modalElement.querySelectorAll('form');
                    forms.forEach(form => {
                        form.reset();
                    });
                    
                    // Force hide the modal
                    modalElement.style.display = 'none';
                }
            } catch (err) {
                console.error('Error handling modal close:', err);
            }
            
            // Add a small delay to prevent any potential race conditions
            setTimeout(() => {
                // Double check the modal is closed in Alpine data
                if (window.Alpine) {
                    try {
                        const modalRoot = document.querySelector('[x-data="{ openModals: {} }"]');
                        if (modalRoot) {
                            const scope = window.Alpine.$data(modalRoot);
                            if (scope && scope.openModals && scope.openModals[modalId]) {
                                scope.openModals[modalId] = false;
                                console.log(`Force reset ${modalId} to false`);
                            }
                        }
                    } catch (err) {
                        // Ignore any errors in the delayed check
                    }
                }
            }, 100);
        }
    });

    // Add backup click handler for modal buttons in case Alpine.js isn't working properly
    document.querySelectorAll('[data-modal-target]').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const modalId = this.dataset.modalTarget;
            const modalEvent = new CustomEvent('open-modal', { 
                detail: { id: modalId } 
            });
            window.dispatchEvent(modalEvent);
            console.log(`Modal open event triggered for ${modalId}`);
            
            // As a last resort, try to show the modal directly
            const modalElement = document.querySelector(`[x-show="openModals['${modalId}']"]`);
            if (modalElement && window.Alpine) {
                try {
                    // Try to access Alpine's data and manipulate it
                    const Alpine = window.Alpine;
                    const scopeEl = Alpine.closestRoot(modalElement);
                    if (scopeEl) {
                        const scope = Alpine.$data(scopeEl);
                        if (scope && scope.openModals) {
                            scope.openModals[modalId] = true;
                        }
                    }
                } catch (err) {
                    console.error('Alpine.js modal manipulation error:', err);
                }
            }
        });
    });

    // Add a click handler for the "Add Proxy" button specifically
    const addProxyButton = document.querySelector('button[type="button"][class*="bg-indigo-600"]');
    if (addProxyButton) {
        addProxyButton.addEventListener('click', function() {
            const modalEvent = new CustomEvent('open-modal', { 
                detail: { id: 'add-proxy-modal' } 
            });
            window.dispatchEvent(modalEvent);
            console.log('Add proxy modal event triggered');
        });
    }

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