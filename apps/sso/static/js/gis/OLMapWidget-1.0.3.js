/*
 * look for openmap fields and initialise them
 * 
 * @author Gunnar Scherf
 * @requires jQuery 
 */

(function($) {
    function init_osm_widget(){
		/*
		 * Find all geodjango fields in active tabs and initialise them
		 */
	    var map_options = {
	    	maxExtend: new OpenLayers.Bounds(-20037508,-20037508,20037508,20037508),
	    	maxResolution: 156543.0339,
	    	numZoomLevels: 20,
	    	units: 'm'
	    };

		$(".active .geodjango-field:not(.initialised)").each(function(){
		    var options = {
		  		geom_name: $(this).data('geom_type'),
		    	id: $(this).attr('id'),
		    	map_id: $(this).attr('id') + "_map",
	    		map_options: map_options,
	    		map_srid: $(this).data('map_srid'),
	    		name: $(this).attr('name'),
	    		scale_text: true,
	    		mouse_position: true,
	    		default_lon: $(this).data('default_lon'),
	    		default_lat: $(this).data('default_lat'),
	    		base_layer: new OpenLayers.Layer.OSM.Mapnik("OpenStreetMap (Mapnik)")
	        };
            // initialise only once
            $(this).addClass("initialised");
		    /*
		     * find the clear all features button and attach the clearFeatures function
		     */
	    	var geodjango_widget = new MapWidget(options);
	    	$(this).prev(".clear_features").click(function(){geodjango_widget.clearFeatures();});

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
                        var point = new OpenLayers.Geometry.Point(data[0].lon, data[0].lat).transform(new OpenLayers.Projection("EPSG:4326"), geodjango_widget.map.getProjectionObject());
                        var feature = new OpenLayers.Feature.Vector(point);
                        geodjango_widget.layers.vector.addFeatures(feature);
                        geodjango_widget.map.setCenter([point.x, point.y]);
                        displaySuccess(formset_prefix, gettext("The map was updated with the new coordinates. Press the 'Save' button for saving the new coordinates."));
                    }
                    $btn.button('reset');
                });
            });

		});
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
    hide or display the geocoding part. geocoding is only shown for the meditation address
     */
    function address_type_changed($select_element) {
        var formset_prefix = $select_element.parents(".dynamic-organisationaddress_set").attr("id");
        if ($select_element.val() != "meditation"){
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
        var data = {
            limit: 2,
            format: "jsonv2",
            street: street,
            city: city,
            country: country,
            postalcode: postalcode,
            county: county
        }
        return data;
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

/*
 * from django gis
 */
(function() {
/**
 * Transforms an array of features to a single feature with the merged
 * geometry of geom_type
 */
OpenLayers.Util.properFeatures = function(features, geom_type) {
    if (features.constructor == Array) {
        var geoms = [];
        for (var i=0; i<features.length; i++) {
            geoms.push(features[i].geometry);
        }
        var geom = new geom_type(geoms);
        features = new OpenLayers.Feature.Vector(geom);
    }
    return features;
}

/**
 * @requires OpenLayers/Format/WKT.js
 */

/**
 * Class: OpenLayers.Format.DjangoWKT
 * Class for reading Well-Known Text, with workarounds to successfully parse
 * geometries and collections as returned by django.contrib.gis.geos.
 *
 * Inherits from:
 *  - <OpenLayers.Format.WKT>
 */

OpenLayers.Format.DjangoWKT = OpenLayers.Class(OpenLayers.Format.WKT, {
    initialize: function(options) {
        OpenLayers.Format.WKT.prototype.initialize.apply(this, [options]);
        this.regExes.justComma = /\s*,\s*/;
    },

    parse: {
        'point': function(str) {
            var coords = OpenLayers.String.trim(str).split(this.regExes.spaces);
            return new OpenLayers.Feature.Vector(
                new OpenLayers.Geometry.Point(coords[0], coords[1])
            );
        },

        'multipoint': function(str) {
            var point;
            var points = OpenLayers.String.trim(str).split(this.regExes.justComma);
            var components = [];
            for(var i=0, len=points.length; i<len; ++i) {
                point = points[i].replace(this.regExes.trimParens, '$1');
                components.push(this.parse.point.apply(this, [point]).geometry);
            }
            return new OpenLayers.Feature.Vector(
                new OpenLayers.Geometry.MultiPoint(components)
            );
        },

        'linestring': function(str) {
            var points = OpenLayers.String.trim(str).split(',');
            var components = [];
            for(var i=0, len=points.length; i<len; ++i) {
                components.push(this.parse.point.apply(this, [points[i]]).geometry);
            }
            return new OpenLayers.Feature.Vector(
                new OpenLayers.Geometry.LineString(components)
            );
        },

        'multilinestring': function(str) {
            var line;
            var lines = OpenLayers.String.trim(str).split(this.regExes.parenComma);
            var components = [];
            for(var i=0, len=lines.length; i<len; ++i) {
                line = lines[i].replace(this.regExes.trimParens, '$1');
                components.push(this.parse.linestring.apply(this, [line]).geometry);
            }
            return new OpenLayers.Feature.Vector(
                new OpenLayers.Geometry.MultiLineString(components)
            );
        },

        'polygon': function(str) {
            var ring, linestring, linearring;
            var rings = OpenLayers.String.trim(str).split(this.regExes.parenComma);
            var components = [];
            for(var i=0, len=rings.length; i<len; ++i) {
                ring = rings[i].replace(this.regExes.trimParens, '$1');
                linestring = this.parse.linestring.apply(this, [ring]).geometry;
                linearring = new OpenLayers.Geometry.LinearRing(linestring.components);
                components.push(linearring);
            }
            return new OpenLayers.Feature.Vector(
                new OpenLayers.Geometry.Polygon(components)
            );
        },

        'multipolygon': function(str) {
            var polygon;
            var polygons = OpenLayers.String.trim(str).split(this.regExes.doubleParenComma);
            var components = [];
            for(var i=0, len=polygons.length; i<len; ++i) {
                polygon = polygons[i].replace(this.regExes.trimParens, '$1');
                components.push(this.parse.polygon.apply(this, [polygon]).geometry);
            }
            return new OpenLayers.Feature.Vector(
                new OpenLayers.Geometry.MultiPolygon(components)
            );
        },

        'geometrycollection': function(str) {
            // separate components of the collection with |
            str = str.replace(/,\s*([A-Za-z])/g, '|$1');
            var wktArray = OpenLayers.String.trim(str).split('|');
            var components = [];
            for(var i=0, len=wktArray.length; i<len; ++i) {
                components.push(OpenLayers.Format.WKT.prototype.read.apply(this,[wktArray[i]]));
            }
            return components;
        }
    },

    extractGeometry: function(geometry) {
        var type = geometry.CLASS_NAME.split('.')[2].toLowerCase();
        if (!this.extract[type]) {
            return null;
        }
        if (this.internalProjection && this.externalProjection) {
            geometry = geometry.clone();
            geometry.transform(this.internalProjection, this.externalProjection);
        }
        var wktType = type == 'collection' ? 'GEOMETRYCOLLECTION' : type.toUpperCase();
        var data = wktType + '(' + this.extract[type].apply(this, [geometry]) + ')';
        return data;
    },

    /**
     * Patched write: successfully writes WKT for geometries and
     * geometrycollections.
     */
    write: function(features) {
        var collection, geometry, type, data, isCollection;
        isCollection = features.geometry.CLASS_NAME == "OpenLayers.Geometry.Collection";
        var pieces = [];
        if (isCollection) {
            collection = features.geometry.components;
            pieces.push('GEOMETRYCOLLECTION(');
            for (var i=0, len=collection.length; i<len; ++i) {
                if (i>0) {
                    pieces.push(',');
                }
                pieces.push(this.extractGeometry(collection[i]));
            }
            pieces.push(')');
        } else {
            pieces.push(this.extractGeometry(features.geometry));
        }
        return pieces.join('');
    },

    CLASS_NAME: "OpenLayers.Format.DjangoWKT"
});

function MapWidget(options) {
    this.map = null;
    this.controls = null;
    this.panel = null;
    this.layers = {};
    this.wkt_f = new OpenLayers.Format.DjangoWKT();

    // Mapping from OGRGeomType name to OpenLayers.Geometry name
    if (options['geom_name'] == 'Unknown') options['geom_type'] = OpenLayers.Geometry;
    else if (options['geom_name'] == 'GeometryCollection') options['geom_type'] = OpenLayers.Geometry.Collection;
    else options['geom_type'] = eval('OpenLayers.Geometry.' + options['geom_name']);

    // Default options
    this.options = {
        color: 'ee9900',
        default_lat: 0,
        default_lon: 0,
        default_zoom: 4,
        is_collection: new options['geom_type']() instanceof OpenLayers.Geometry.Collection,
        layerswitcher: false,
        map_options: {},
        map_srid: 4326,
        modifiable: true,
        mouse_position: false,
        opacity: 0.4,
        point_zoom: 12,
        scale_text: false,
        scrollable: true
    };

    // Altering using user-provided options
    for (var property in options) {
        if (options.hasOwnProperty(property)) {
            this.options[property] = options[property];
        }
    }

    this.map = this.create_map();

    var defaults_style = {
        'fillColor': '#' + this.options.color,
        'fillOpacity': this.options.opacity,
        'strokeColor': '#' + this.options.color
    };
    if (this.options.geom_name == 'LineString') {
        defaults_style['strokeWidth'] = 3;
    }
    var styleMap = new OpenLayers.StyleMap({'default': OpenLayers.Util.applyDefaults(defaults_style, OpenLayers.Feature.Vector.style['default'])});
    this.layers.vector = new OpenLayers.Layer.Vector(" " + this.options.name, {styleMap: styleMap});
    this.map.addLayer(this.layers.vector);
    var wkt = document.getElementById(this.options.id).value;
    if (wkt) {
        var feat = OpenLayers.Util.properFeatures(this.read_wkt(wkt), this.options.geom_type);
        this.write_wkt(feat);
        if (this.options.is_collection) {
            for (var i=0; i<this.num_geom; i++) {
                this.layers.vector.addFeatures([new OpenLayers.Feature.Vector(feat.geometry.components[i].clone())]);
            }
        } else {
            this.layers.vector.addFeatures([feat]);
        }
        this.map.zoomToExtent(feat.geometry.getBounds());
        if (this.options.geom_name == 'Point') {
            this.map.zoomTo(this.options.point_zoom);
        }
    } else {
        this.map.setCenter(this.defaultCenter(), this.options.default_zoom);
    }
    this.layers.vector.events.on({'featuremodified': this.modify_wkt, scope: this});
    this.layers.vector.events.on({'featureadded': this.add_wkt, scope: this});

    this.getControls(this.layers.vector);
    this.panel.addControls(this.controls);
    this.map.addControl(this.panel);
    this.addSelectControl();

    if (this.options.mouse_position) {
        this.map.addControl(new OpenLayers.Control.MousePosition());
    }
    if (this.options.scale_text) {
        this.map.addControl(new OpenLayers.Control.Scale());
    }
    if (this.options.layerswitcher) {
        this.map.addControl(new OpenLayers.Control.LayerSwitcher());
    }
    if (!this.options.scrollable) {
        this.map.getControlsByClass('OpenLayers.Control.Navigation')[0].disableZoomWheel();
    }
    if (wkt) {
        if (this.options.modifiable) {
            this.enableEditing();
        }
    } else {
        this.enableDrawing();
    }
}

MapWidget.prototype.create_map = function() {
    var map = new OpenLayers.Map(this.options.map_id, this.options.map_options);
    if (this.options.base_layer) this.layers.base = this.options.base_layer;
    else this.layers.base = new OpenLayers.Layer.WMS('OpenLayers WMS', 'http://vmap0.tiles.osgeo.org/wms/vmap0', {layers: 'basic'});
    map.addLayer(this.layers.base);
    return map
};

MapWidget.prototype.get_ewkt = function(feat) {
    return "SRID=" + this.options.map_srid + ";" + this.wkt_f.write(feat);
};

MapWidget.prototype.read_wkt = function(wkt) {
    var prefix = 'SRID=' + this.options.map_srid + ';'
    if (wkt.indexOf(prefix) === 0) {
        wkt = wkt.slice(prefix.length);
    }
    return this.wkt_f.read(wkt);
};

MapWidget.prototype.write_wkt = function(feat) {
    feat = OpenLayers.Util.properFeatures(feat, this.options.geom_type);
    if (this.options.is_collection) {
        this.num_geom = feat.geometry.components.length;
    } else {
        this.num_geom = 1;
    }
    document.getElementById(this.options.id).value = this.get_ewkt(feat);
};

MapWidget.prototype.add_wkt = function(event) {
    if (this.options.is_collection) {
        var feat = new OpenLayers.Feature.Vector(new this.options.geom_type());
        for (var i=0; i<this.layers.vector.features.length; i++) {
            feat.geometry.addComponents([this.layers.vector.features[i].geometry]);
        }
        this.write_wkt(feat);
    } else {
        if (this.layers.vector.features.length > 1) {
            old_feats = [this.layers.vector.features[0]];
            this.layers.vector.removeFeatures(old_feats);
            this.layers.vector.destroyFeatures(old_feats);
        }
        this.write_wkt(event.feature);
    }
};

MapWidget.prototype.modify_wkt = function(event) {
    if (this.options.is_collection) {
        if (this.options.geom_name == 'MultiPoint') {
            this.add_wkt(event);
            return;
        } else {
            var feat = new OpenLayers.Feature.Vector(new this.options.geom_type());
            for (var i=0; i<this.num_geom; i++) {
                feat.geometry.addComponents([this.layers.vector.features[i].geometry]);
            }
            this.write_wkt(feat);
        }
    } else {
        this.write_wkt(event.feature);
    }
};

MapWidget.prototype.deleteFeatures = function() {
    this.layers.vector.removeFeatures(this.layers.vector.features);
    this.layers.vector.destroyFeatures();
};

MapWidget.prototype.clearFeatures = function() {
    this.deleteFeatures();
    document.getElementById(this.options.id).value = '';
    this.map.setCenter(this.defaultCenter(), this.options.default_zoom);
};

MapWidget.prototype.defaultCenter = function() {
    var center = new OpenLayers.LonLat(this.options.default_lon, this.options.default_lat);
    if (this.options.map_srid) {
        return center.transform(new OpenLayers.Projection("EPSG:4326"), this.map.getProjectionObject());
    }
    return center;
};

MapWidget.prototype.addSelectControl = function() {
    var select = new OpenLayers.Control.SelectFeature(this.layers.vector, {'toggle': true, 'clickout': true});
    this.map.addControl(select);
    select.activate();
};

MapWidget.prototype.enableDrawing = function () {
    this.map.getControlsByClass('OpenLayers.Control.DrawFeature')[0].activate();
};

MapWidget.prototype.enableEditing = function () {
    this.map.getControlsByClass('OpenLayers.Control.ModifyFeature')[0].activate();
};

MapWidget.prototype.getControls = function(layer) {
    this.panel = new OpenLayers.Control.Panel({'displayClass': 'olControlEditingToolbar'});
    this.controls = [new OpenLayers.Control.Navigation()];
    if (!this.options.modifiable && layer.features.length)
        return;
    if (this.options.geom_name.indexOf('LineString') >= 0 || this.options.geom_name == 'GeometryCollection' || this.options.geom_name == 'Unknown') {
        this.controls.push(new OpenLayers.Control.DrawFeature(layer, OpenLayers.Handler.Path, {'displayClass': 'olControlDrawFeaturePath'}));
    }
    if (this.options.geom_name.indexOf('Polygon') >= 0 || this.options.geom_name == 'GeometryCollection' || this.options.geom_name == 'Unknown') {
        this.controls.push(new OpenLayers.Control.DrawFeature(layer, OpenLayers.Handler.Polygon, {'displayClass': 'olControlDrawFeaturePolygon'}));
    }
    if (this.options.geom_name.indexOf('Point') >= 0 || this.options.geom_name == 'GeometryCollection' || this.options.geom_name == 'Unknown') {
        this.controls.push(new OpenLayers.Control.DrawFeature(layer, OpenLayers.Handler.Point, {'displayClass': 'olControlDrawFeaturePoint'}));
    }
    if (this.options.modifiable) {
        this.controls.push(new OpenLayers.Control.ModifyFeature(layer, {'displayClass': 'olControlModifyFeature'}));
    }
};
window.MapWidget = MapWidget;
})();
