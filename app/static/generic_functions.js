function confirmCancelNoForm(redirectUrl) {
    if (confirm('Are you sure you want to cancel?')) {
        window.location.href = redirectUrl;
    }
}

/* universal confirm action function with redirect */
function confirmAction(event, redirectUrl) {
    var message = event.target.getAttribute('data-confirm-message');
    if (confirm(message)) {
        window.location.href = redirectUrl;
    } else {
        event.preventDefault();
    }
}

/* universal confirm action function for forms */
function confirmActionNoRedirect(event, message) {
    if (!confirm(message)) {
        event.preventDefault(); // Prevent the form from submitting only if the user does not confirm
    }
}

/* universal confirm cancellation message */
function cancelAction(event, redirectUrl) {
    event.preventDefault();  // Prevent form submission
    if (redirectUrl) {
        window.location.href = redirectUrl;  // Redirect to the specified URL
    } else {
        var form = event.target.closest('form');
        if (form) {
            form.reset();  // Reset the form
        }
    }
}

/* 
generic message with OK button
to be used to inform the user that the action is completed.
*/
function messageAndRedirect(message, redirectUrl) {
    if (confirm(message)) {
        window.location.href = redirectUrl;
    }
}

/* logout confirmation */
function confirmLogout() {
    if (confirm('Do you want to log out?')) {
        window.location.href = '/auth/logout';  // confirm logout & log out
    }
}

function confirmCancelPurchase() {
    if (confirm('Are you sure you want to cancel the purchase?')) {
        window.location.href = '/';  // if user confirms cancellation, go back to list of items
    }
}

function confirmCancelVerification(itemId) {
    if (confirm('Do you want to return to purchase details?')) {
        window.location.href = '/purchase/' + itemId;  // Redirect to the specific item's purchase verification page
    }
}

function confirmFinalizePurchase() {
    return confirm('Do you want to finalize the purchase?');
}

function copyTokenToClipboard(tokenId) {
    var inputElement = document.getElementById(tokenId);
    inputElement.select();
    inputElement.setSelectionRange(0, 99999); // For mobile devices

    try {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(inputElement.value)
                .then(() => console.log('Text copied to clipboard'))
                .catch(err => console.error('Failed to copy text: ', err));
        } else {
            // Fallback for browsers without Clipboard API
            var successful = document.execCommand('copy');
            if (!successful) {
                console.error('Failed to copy text using execCommand');
            }
        }
    } catch (err) {
        console.error('Error copying text: ', err);
    }
}
