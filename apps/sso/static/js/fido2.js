if (typeof jQuery === 'undefined') {
    throw new Error('u2f\'s JavaScript requires jQuery.');
}
import {create, get, parseRequestOptionsFromJSON, parseCreationOptionsFromJSON, supported} from './vendor/webauthn-json.browser-ponyfill.js';

(function ($) {
    'use strict';

    $(function () {
        // Check if WebAuthn is supported by this browser
        if (supported()) {
            $(".u2f-login-text").removeClass('hidden');
            $(".browser-not-supported").addClass('hidden');
        } else {
            $(".u2f-login-text").addClass('hidden');
            $(".browser-not-supported").removeClass('hidden');
        }

        if ($('#u2f_register_form').length) {
            const form = $('#u2f_register_form');
            const data = JSON.parse($("input[name='u2f_request']", form).val());
            const state = data.state
            const options = parseCreationOptionsFromJSON(data.req);
            create(options).then(function (result) {
                $("input[name='u2f_response']", form).val(JSON.stringify(result));
                $("input[name='state']", form).val(state);
                displaySucess();
            }).catch((err) => {
                displayError(err)
            });
        } else if ($('#u2f_sign_form').length) {
            const form = $('#u2f_sign_form');
            const data = JSON.parse($("input[name='challenges']", form).val());
            const state = data.state
            const options = parseRequestOptionsFromJSON(data.req);
            get(options).then(function (result) {
                $("input[name='response']", form).val(JSON.stringify(result));
                $("input[name='state']", form).val(state);
                form.submit();
            }).catch((err) => {
                displayError(err)
            });
        }
    });

    function displayError(text) {
        const status = $("#u2f-status");
        status.text(text);
        status.addClass('alert');
        status.addClass('alert-danger');
        $(".u2f-login-text").addClass('hidden');
    }

    function displaySucess() {
        const status = $("#u2f-status");
        const message = gettext("Registration successful.")
        status.text(message);
        status.append(" <i class=\"bi bi-person-check fs-4\"></i>");
        status.addClass('alert');
        status.addClass('alert-success');
        $(".u2f-login-text").addClass('hidden');
    }
}(jQuery));
