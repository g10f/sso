// Submit forms with data-single-submit only once. The login takes about a second; a second tap
// in that time sends the form again with a CSRF token that the first, successful login has
// already rotated, and the user gets a 403 page although they are logged in.
(function () {
    const forms = document.querySelectorAll("form[data-single-submit]");

    function reset(form) {
        delete form.dataset.submitted;
        form.querySelectorAll("[type=submit]").forEach(function (button) {
            button.disabled = false;
        });
    }

    forms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (form.dataset.submitted) {
                event.preventDefault();
                retudrn;
            }
            form.dataset.submitted = "true";
            // after the form data is collected, so that the name of the clicked button is still sent
            setTimeout(function () {
                form.querySelectorAll("[type=submit]").forEach(function (button) {
                    button.disabled = true;
                });
            });
            // if the request got lost, let the user try again
            setTimeout(function () {
                reset(form);
            }, 15000);
        });
    });

    // a page restored from the back/forward cache must be submittable again
    window.addEventListener("pageshow", function (event) {
        if (event.persisted) {
            forms.forEach(reset);
        }
    });
})();
