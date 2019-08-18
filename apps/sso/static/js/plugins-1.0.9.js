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
 * Geo location query
 *
 *
 *
 * @author Gunnar Scherf
 * @requires jQuery
 */
(function ($) {
    function getLocation() {
        if (!$("button.geo-location").hasClass("active")) {
            navigator.geolocation.getCurrentPosition(showDistance);
        } else {
            showDistance(null);
        }
    }

    function showDistance(position) {
        var latlng = "";
        if (position) {
            latlng = position.coords.latitude + "," + position.coords.longitude;
        }
        window.location = $("button.geo-location").data("href").replace("latlng=", "latlng=" + latlng);
    }

    $(function () {
        $("button.geo-location").click(function () {
            getLocation();
        });
        $('[data-toggle="tooltip"]').tooltip();
        $('[data-toggle="popover"]').popover();
        if ($('.select2').length > 0) {
            if (typeof $('.select2').select2 !== "function") {
                console.warn("select2.js  probably not included.")
            } else {
                $('.select2').select2({theme: "bootstrap"});
                $('form .select2').select2({width: "100%"});
                $('.select2').on('select2:select', function (e) {
                    var data = e.params.data;
                    if ($(data.element).data('url')) {
                        window.location = $(data.element).data('url');
                    }
                });

            }
        }
    });
})(jQuery);
