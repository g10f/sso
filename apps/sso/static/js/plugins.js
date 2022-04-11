// Avoid `console` errors in browsers that lack a console.
(function () {
    var method;
    var noop = function () {
    };
    var methods = [
        'assert', 'clear', 'count', 'debug', 'dir', 'dirxml', 'error',
        'exception', 'group', 'groupCollapsed', 'groupEnd', 'info', 'log',
        'markTimeline', 'profile', 'profileEnd', 'table', 'time', 'timeEnd',
        'timeStamp', 'trace', 'warn'
    ];
    var length = methods.length;
    var console = (window.console = window.console || {});

    while (length--) {
        method = methods[length];

        // Only stub undefined methods.
        if (!console[method]) {
            console[method] = noop;
        }
    }
}());

/**
 * Tab handling
 *
 * If the form has a data-active != "" attribute then the server has set the active tab.
 * Otherwise
 *
 *
 * @author Gunnar Scherf
 * @requires jQuery
 */

function showFirstTab() {
    showTab('#myTab li:first-child a')
}

function showTab(selector) {
    const el = document.querySelector(selector);
    if (el !== null) {
        const tab = new bootstrap.Tab(el);
        tab.show();
        return true;
    } else {
        console.debug(`tab with selector "${selector}" not found`);
        return false;
    }
}

(function ($) {
    $(function () {
        if ($("#myTab").length) {
            const active = $("#myTab").data("active");
            let activeTab = ""
            if (active) {
                // server set active tab
                if (location.hash !== "#" + active) {
                    history.pushState({}, "", "#" + active);
                }
                activeTab = `#myTab li a[href="#${active}"]`;
            } else {
                // client side handling of active tab
                if (location.hash !== "") {
                    activeTab = `#myTab li a[href="${location.hash}"]`;
                }
            }
            if (activeTab !== "") {
                const res = showTab(activeTab);
                if (!res) {
                    // error in location hash?
                    showFirstTab();
                }
            } else {
                showFirstTab();
            }
            $("a[data-bs-toggle='tab']").on("shown.bs.tab", function (e) {
                const hash = $(e.target).attr("href");
                if (hash.startsWith('#')) {
                    history.pushState({}, "", hash)
                }
            });
        }
    });
})(jQuery);

/**
 * Geo location query
 *
 *
 *
 * @author Gunnar Scherf
 * @requires jQuery
 */
(function ($) {
    function error(err) {
        console.warn(`ERROR(${err.code}): ${err.message}`);
    }

    function showDistance(position) {
        var latlng = "";
        if (position) {
            latlng = position.coords.latitude + "," + position.coords.longitude;
        }
        window.location = $("button.geo-location").data("href").replace("latlng=", "latlng=" + latlng);
    }

    function getLocation() {
        if (!$("button.geo-location").hasClass("active")) {
            navigator.geolocation.getCurrentPosition(showDistance, error);
        } else {
            showDistance(null);
        }
    }
    function toggleOIDCClientFields(type) {
        if (type === 'service') {
            // disable redirect_uris post_logout_redirect_uris and
            // enable can_access_all_users client_secret
            $(".oidc-client [name='redirect_uris']").parent().parent().addClass('hidden')
            $(".oidc-client [name='post_logout_redirect_uris']").parent().parent().addClass('hidden')
            $(".oidc-client [name='can_access_all_users']").parent().parent().removeClass('hidden')
            $(".oidc-client [name='client_secret']").parent().parent().removeClass('hidden')
        }
        else if (type === 'web') {
            $(".oidc-client [name='redirect_uris']").parent().parent().removeClass('hidden')
            $(".oidc-client [name='post_logout_redirect_uris']").parent().parent().removeClass('hidden')
            $(".oidc-client [name='can_access_all_users']").parent().parent().addClass('hidden')
            $(".oidc-client [name='client_secret']").parent().parent().removeClass('hidden')
        }
        else if (type === 'native') {
            $(".oidc-client [name='redirect_uris']").parent().parent().removeClass('hidden')
            $(".oidc-client [name='post_logout_redirect_uris']").parent().parent().removeClass('hidden')
            $(".oidc-client [name='can_access_all_users']").parent().parent().addClass('hidden')
            $(".oidc-client [name='client_secret']").parent().parent().addClass('hidden')
        }
    }

    $(function () {
        $("button.geo-location").click(function () {
            getLocation();
        });
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl)
        });
        var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
        var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl)
        });
        var theme = "bootstrap-5";
        $("select.select2").each(function () {
            $(this).select2({
                theme: theme,
                width: $(this).data("width") ? $(this).data("width") : $(this).hasClass("w-100") ? "100%" : "resolve",
                closeOnSelect: !$(this).attr("multiple")
            });
            // check if this is a select box inside a nav-item
            if ($(this).parents(".nav-item").length === 1) {
                $(this).on('select2:select', function (e) {
                    var data = e.params.data;
                    if ($(data.element).data('url')) {
                        window.location = $(data.element).data('url');
                    }
                });
            }
        });
        $('form:has(.tab-pane)').find('[type="submit"]').click(function () {
            $('input:invalid, select:invalid').each(function () {
                // Find the tab-pane that this element is inside, and get the id
                var $closest = $(this).closest('.tab-pane');
                var id = $closest.attr('id');
                // Find the link that corresponds to the pane and have it show
                $('.nav a[href="#' + id + '"]').tab('show');
                // Only want to do it once
                return false;
            });
        });
        // oidc client configuration page
        $("button.client-secret-delete").click(function () {
            $(this).siblings("input").val('');
        });
        $("button.client-secret-renew").click(function () {
            const url = $(this).data('url');
            const input = $(this).siblings("input");
            $.get(url, function (data) {
                input.val(data);
            });
        });
        $(".oidc-client select[name='type']").change(function () {
            toggleOIDCClientFields(this.value);
        });
        $(".oidc-client select[name='type']").trigger("change");
    });
})(jQuery);
