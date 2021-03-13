if (typeof jQuery === 'undefined') {
    throw new Error('u2f\'s JavaScript requires jQuery.');
}

(function ($) {
    'use strict';

    $(function () {
        if ('u2f' in window) {
            $(".browser-not-supported").hide();
        } else {
            $(".login-text").hide();
        }
        if ($('#u2f_register_form').length) {
            const form = $('#u2f_register_form');
            const data = JSON.parse($("input[name='u2f_request']", form).val());
            u2f.register(data['appId'], data['registerRequests'], data['registeredKeys'], function (resp) {
                $("input[name='u2f_response']", form).val(JSON.stringify(resp));
                if (!handleU2FError(resp)) {
                    form.submit();
                }
            })
        } else if ($('#u2f_sign_form').length) {
            const form = $('#u2f_sign_form');
            const data = JSON.parse($("input[name='challenges']", form).val());
            u2f.sign(data["appId"], data["challenge"], data["registeredKeys"], function (resp) {
                $("input[name='response']", form).val(JSON.stringify(resp));
                if (!handleU2FError(resp)) {
                    form.submit();
                }
            })
        }
    });

    function displayError(text) {
        const status = $("#u2f-status");
        status.text(text + " See: ");
        const element = $("<strong><a href='https://developers.yubico.com/U2F/Libraries/" +
            "Client_error_codes.html'>Client error codes</a></strong>");
        status.append(element);
        status.addClass('alert');
        status.addClass('alert-danger');

        $("#u2f-login-text").hide();
    }

    function handleU2FError(resp) {
        if (resp.errorCode) {
            let message = "1 - Unexpected U2F error";
            switch (resp.errorCode) {
                case 2:
                    message = "2 - Bad request.";
                    break;
                case 3:
                    message = "3 - Client configuration is not supported.";
                    break;
                case 4:
                    if ($('#u2f_register_form').length) {
                        message = "4 - The presented device is not eligible for this request. This may mean that the " +
                            "token is already registered.";

                    } else {
                        message = "The presented device is not eligible for this request. This may mean that the " +
                            "token does 4 - not know the presented key handle.";
                    }
                    break;
                case 5:
                    message = "5 - Timeout reached before request could be satisfied.";
                    break;
            }
            displayError(message);
            return true;
        } else {
            return false;
        }
    }
}(jQuery));
