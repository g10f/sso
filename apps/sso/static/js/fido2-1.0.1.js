if (typeof jQuery === 'undefined') {
    throw new Error('u2f\'s JavaScript requires jQuery.');
}

(function ($) {
    'use strict';

    $(function () {
        // Check if WebAuthn is supported by this browser
        if (!window.PublicKeyCredential) {
            $(".u2f-login-text").addClass('hidden');
            $(".browser-not-supported").removeClass('hidden');
        } else {
            $(".u2f-login-text").removeClass('hidden');
            $(".browser-not-supported").addClass('hidden');
        }

        if ($('#u2f_register_form').length) {
            const form = $('#u2f_register_form');
            const data = JSON.parse($("input[name='u2f_request']", form).val());
            const req = base64ToArrayBuffer(data.req);
            const options = CBOR.decode(req);
            const state = data.state;
            navigator.credentials.create(options)
                .then(function (attestation) {
                    const response = arrayBufferToBase64(CBOR.encode({
                      "attestationObject": new Uint8Array(attestation.response.attestationObject),
                      "clientDataJSON": new Uint8Array(attestation.response.clientDataJSON),
                    }))
                    console.log(response);
                    $("input[name='state']", form).val(state);
                    $("input[name='u2f_response']", form).val(response);
                    displaySucess("Registration successful.");
                    document.getElementById("id_name").focus();
                    //form.submit();
                })
                .catch((err) => {
                    displayError(err)
                });
        } else if ($('#u2f_sign_form').length) {
            const form = $('#u2f_sign_form');
            const data = JSON.parse($("input[name='challenges']", form).val());
            const req = base64ToArrayBuffer(data.req);
            const state = data.state
            const options = CBOR.decode(req);
            navigator.credentials.get(options)
                .then(function (assertion) {
                    const response = arrayBufferToBase64(CBOR.encode({
                        "credentialId": new Uint8Array(assertion.rawId),
                        "authenticatorData": new Uint8Array(assertion.response.authenticatorData),
                        "clientDataJSON": new Uint8Array(assertion.response.clientDataJSON),
                        "signature": new Uint8Array(assertion.response.signature)
                    }))
                    console.log(response);
                    $("input[name='state']", form).val(state);
                    $("input[name='response']", form).val(response);
                    form.submit();
                })
                .catch((err) => {
                    displayError(err)
                });
        }
    });

    function arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        const len = bytes.byteLength;
        for (let i = 0; i < len; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return window.btoa(binary);
    }

    function base64ToArrayBuffer(base64) {
        const binary_string = window.atob(base64);
        const len = binary_string.length;
        let bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binary_string.charCodeAt(i);
        }
        return bytes.buffer;
    }

    function displayError(text) {
        const status = $("#u2f-status");
        status.text(text);
        status.addClass('alert');
        status.addClass('alert-danger');
        $(".u2f-login-text").addClass('hidden');
    }
    function displaySucess(text) {
        const status = $("#u2f-status");
        status.text(text);
        status.append(" <i class=\"bi bi-person-check fs-4\"></i>");
        status.addClass('alert');
        status.addClass('alert-success');
        $(".u2f-login-text").addClass('hidden');
    }
}(jQuery));
