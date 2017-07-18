if (typeof jQuery === 'undefined') {
    throw new Error('u2f\'s JavaScript requires jQuery.');
}
if (typeof bowser === 'undefined') {
    throw new Error('u2f\'s JavaScript requires bowser.');
}

(function ($) {
    'use strict';

    $(function () {
        if ((bowser.chrome && bowser.version >= 41)) {
            $(".browser-not-supported").hide();
        }
        if ($('#u2f_register_form').length) {
            var form = $('#u2f_register_form');
            var data = JSON.parse($("input[name='u2f_request']", form).val());
            u2f.register(data['appId'], data['registerRequests'], data['registeredKeys'], function (resp) {
                $("input[name='u2f_response']", form).val(JSON.stringify(resp));
                if (!handleU2FError(resp)) {
                    form.submit();
                }
            })
        } else if ($('#u2f_sign_form').length) {
            var form = $('#u2f_sign_form');
            var data = JSON.parse($("input[name='challenges']", form).val());
            u2f.sign(data["appId"], data["challenge"], data["registeredKeys"], function (resp) {
                $("input[name='response']", form).val(JSON.stringify(resp));
                if (!handleU2FError(resp)) {
                    form.submit();
                }
            })
        }
    });
    function displayError(text) {
        var status = document.getElementById('u2f-status');
        status.textContent = text;
        status.classList.add('alert');
        status.classList.add('alert-danger');
    }

    function handleU2FError(resp) {
        if (resp.errorCode) {
            var message = "Unexpected U2F error";
            switch (resp.errorCode) {
                case 2:
                    message = "Bad request";
                    break;
                case 3:
                    message = "Client configuration is not supported.";
                    break;
                case 4:
                    if ($('#u2f_registration_form').length) {
                        message = "The presented device is not eligible for this request. This may mean that the " +
                            "token is already registered.";

                    } else {
                        message = "The presented device is not eligible for this request. This may mean that the " +
                            "token does not know the presented key handle.";
                    }
                    break;
                case 5:
                    message = "Timeout reached before request could be satisfied.";
                    break;
            }
            displayError(message);
            return true;
        } else {
            return false;
        }
    }
}(jQuery));
