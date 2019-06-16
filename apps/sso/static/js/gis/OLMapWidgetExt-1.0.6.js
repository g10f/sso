/* global ol */
(function($) {
    var jsonFormat = new ol.format.GeoJSON();

    function init_osm_widget(){
		$(".active .geodjango-field:not(.initialised)").each(function(){
            var map_options = {};
            var base_layer = new ol.layer.Tile({source: new ol.source.OSM()});
            var options = {
                base_layer: base_layer,
                geom_name: $(this).data('geom_type'),
                id: $(this).attr('id'),
                map_id: $(this).attr('id') + "_map",
                map_options: map_options,
                map_srid: $(this).data('map_srid'),
                name: $(this).attr('name'),
	    		default_lon: $(this).data('default_lon'),
	    		default_lat: $(this).data('default_lat'),
            };
            // initialise only once
            $(this).addClass("initialised");

            var geodjango_widget = new MapWidget(options);

	    	$(".clear_features").click(function(){geodjango_widget.clearFeatures();});

            $("button.geocode").on('click', function() {
                var $btn = $(this).button('loading');
                var formset_prefix = $(this).parents(".dynamic-organisationaddress_set").attr("id");
                var data = getAddressData(formset_prefix);
                var request = $.ajax({
                    url: 'https://nominatim.openstreetmap.org/search',
                    dataType: "jsonp",
                    jsonp: "json_callback",
                    data: data
                });
                request.done(function(data) {
                    if (data.length == 0){
                        displayError(formset_prefix, gettext("No location found"));
                    }
                    else{
                        create_or_update_point(geodjango_widget, data);
                        displaySuccess(formset_prefix, gettext("The map was updated with the new coordinates. Press the 'Save' button for saving the new coordinates."));
                    }
                    $btn.button('reset');
                });
            });

		});
    }
    function create_or_update_point (geodjango_widget, data) {
        /*
        create or update the point from lon lat
         */
        var lon = parseFloat(data[0].lon);
        var lat = parseFloat(data[0].lat);
        var coord = ol.proj.transform([lon, lat], 'EPSG:4326', 'EPSG:3857');
        var features = geodjango_widget.featureOverlay.getSource().getFeatures();
        var feature = null;
        if (features[0]) {
            feature = features[0];
            feature.getGeometry().setCoordinates(coord);
        } else {
            feature = new ol.Feature({geometry: new ol.geom.Point(coord)});
            geodjango_widget.featureOverlay.getSource().addFeature(feature);
        }
        var extent = ol.extent.createEmpty();
        ol.extent.extend(extent, feature.getGeometry().getExtent());
        // Center/zoom the map
        geodjango_widget.map.getView().fit(extent, {maxZoom: geodjango_widget.options.default_zoom});
    }
	$(function() {
        $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
            init_osm_widget();
        });
        init_osm_widget();
        $(".address_type").change(function() {
            address_type_changed($(this));
        });
    });
    /*
    hide or display the geocoding part. geocoding is only shown for the physical address
     */
    function address_type_changed($select_element) {
        var formset_prefix = $select_element.parents(".dynamic-organisationaddress_set").attr("id");
        if ($select_element.val() != "physical"){
            $("#" + formset_prefix).find("div.form-group.geocode").addClass("hidden");

        } else {
            $("#" + formset_prefix).find("div.form-group.geocode").removeClass("hidden");
        }
    }
    /*
    get the address information from the html form
     */
    function getAddressData(formset_prefix) {
        var postalcode = $("#id_" + formset_prefix + "-postal_code").val();
        var street = $("#id_" + formset_prefix + "-street_address").val();
        var city = $("#id_" + formset_prefix + "-city").val();
        var country = $("#id_" + formset_prefix + "-country").val();
        var county = $("#id_" + formset_prefix + "-region").val();
        return {
            limit: 2,
            format: "jsonv2",
            street: street,
            city: city,
            country: country,
            postalcode: postalcode,
            county: county
        };
    }
    function displaySuccess(formset_prefix, message) {
        var msg_id = "#" + formset_prefix + "-js_message";
        var html = '<div id="' + msg_id + '" class="alert alert-success alert-dismissible fade in" role="alert">' +
            '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">×</span></button><p>' +
            message + '</p></div>';
        $(msg_id).empty().append(html);
    }
    function displayError(formset_prefix, message) {
        var msg_id = "#" + formset_prefix + "-js_message";
        var html = '<div id="' + msg_id + '" class="message alert alert-danger alert-dismissible fade in" role="alert">' +
            '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">×</span></button><p>' +
            message + '</p></div>';
        $(msg_id).empty().append(html);
    }
})(jQuery);
