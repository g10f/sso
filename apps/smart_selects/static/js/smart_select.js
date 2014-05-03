(function($) {
    $(document).ready(function(){
    	$(".chained").each(function(index) {
    		var chainfield$ = $('#id_' + $(this).data('chainfield'));
    		var chainedfield$ = $(this);

    		var fill_field = function(chained$, id, val, init_value) {
    			var empty_label = chained$.data('empty_label');
    			var url = chained$.data('url');
    	        if (!val || val == '') {
    	            options = '<option value="">' + empty_label + '</option>';
    	            $(id).html(options);
    	            $(id + ' option:first').attr('selected', 'selected');
    	            $(id).trigger('change');
    	            return;
    	        }
    	        $.getJSON(url + "/" + val + "/", function(j) {
    	            var options = '<option value="">' + empty_label + '</option>';
    	            for (var i = 0; i < j.length; i++) {
    	                options += '<option value="' + j[i].value + '">' + j[i].display + '</option>';
    	            }
    	            $(id).html(options);
    	            $(id + ' option:first').attr('selected', 'selected');
    	            if(init_value) {
    	                $(id + ' option[value="' + init_value + '"]').attr('selected', 'selected');
    	            }
    	            $(id).trigger('change');
    	        })
    		}
    		/*
    		 * closure with chainedfield$
    		 */
    		var change = function() {
		        var self = $(this);
		        var curr_parts = self.attr('id').split('-');
		        var base_parts = chainedfield$.attr('id').split('-');
		        var id = '#';
		        for (var i = 0; i < curr_parts.length-1; i++) { 
		            id += curr_parts[i] + '-'; 
		        }
		        id += base_parts[base_parts.length - 1];
		        var start_value = $(id).val();
		        var val = self.val();
		        fill_field(chainedfield$, id, val, start_value);
    		}

    		chainfield$.change(change);
    		chainfield$.trigger('change');    		
    		
    	});    	
    })
})(jQuery || django.jQuery);