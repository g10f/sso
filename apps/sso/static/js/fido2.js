if (typeof jQuery === 'undefined') {
    throw new Error('u2f\'s JavaScript requires jQuery.');
}
import {
    create,
    get,
    parseCreationOptionsFromJSON,
    parseRequestOptionsFromJSON,
    supported
} from './vendor/webauthn-json.browser-ponyfill.js';

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
            $(document).on("keypress", 'form', function (e) {
                const code = e.keyCode || e.which;
                if (code == 13) {
                    e.preventDefault();
                    start_registration();
                    return false;
                }
            });
            $(".start-registration").click(function () {
                start_registration();
            });
        } else if ($('#u2f_sign_form').length) {
            $(".start-authentication").removeClass('hidden');
            $(document).on("keypress", function (e) {
                if (e.which == 13) {
                    e.preventDefault();
                    start_authentication();
                    return false;
                }
            });
            $(".start-authentication").click(function () {
                start_authentication();
            });
        }
    });

    function start_authentication() {
        const form = $('#u2f_sign_form');
        const data = JSON.parse($("input[name='challenges']", form).val());
        const state = data.state
        let options = parseRequestOptionsFromJSON(data.req);
        get(options).then(function (result) {
            $("input[name='response']", form).val(JSON.stringify(result));
            $("input[name='state']", form).val(state);
            form.submit();
        }).catch((err) => {
            displayError(err)
        });
    }

    function start_registration() {
        const form = $('#u2f_register_form');
        const data = JSON.parse($("input[name='u2f_request']", form).val());
        const state = data.state;
        let options = parseCreationOptionsFromJSON(data.req);
        console.log(options)
        create(options).then(function (result) {
            $("input[name='u2f_response']", form).val(JSON.stringify(result));
            $("input[name='state']", form).val(state);
            form.submit();
        }).catch((err) => {
            displayError(err);
        });
    }

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
