if (typeof jQuery === 'undefined') {
    throw new Error('base64_image_upload\'s JavaScript requires jQuery.');
}

(function ($) {
    'use strict';

    $(function () {
        var max_file_size = $('#base64-image').data("max-file-size");
        var max_size = $('#base64-image').data("max-size");

        options.maxHeight = options.maxWidth = max_size;
        options.maxFileSizeKb = max_file_size/1024;

        $('.btn-file input[type="file"]').on('change', function () {
            if (this.files.length > 0) {
                submitImage(this.files[0]);
            }
        });

        $('#base64-image .btn-remove').on('click', function () {
            var style = 'height: ' + options.maxHeight + '; width: ' + options.maxHeight + ';'
            $('#base64-image img').replaceWith('<img class="img-thumbnail" style="' + style + '">');
            $('.btn-file input[type="file"]').val('');
            $('[name="base64_picture"]').val('');
            hideDeleteButton();
        });
        // initialize the img field from base64 data if available
        if ($('[name="base64_picture"]').val()) {
            var style = 'max-height: ' + options.maxHeight + '; max-width: ' + options.maxHeight + ';'
            $('#base64-image img').replaceWith('<img src="' + $('[name="base64_picture"]').val() + '" alt="Image preview" class="img-thumbnail" style="' + style + '">');
            showDeleteButton();
        }
    });

    var options = {
        allowedFormats: ['jpg', 'jpeg', 'png', 'gif'],
        maxWidth: '250px',
        maxHeight: '250px',
        maxFileSizeKb: 6184
    }

    function updateThumbnail(data) {
        var style = 'max-height: ' + options.maxHeight + '; max-width: ' + options.maxHeight + ';'
        $('#base64-image img').replaceWith('<img src="' + data + '" alt="Image preview" class="img-thumbnail" style="' + style + '">');
        $('[name="base64_picture"]').val(data);
    }

    function displayMessage(message, type) {
        var type = (typeof type !== 'undefined') ? type : 'alert-danger';
        $('<div class="alert ' + type + '" role="alert">' + message + '</div>').insertAfter("#base64-image img");
    }

    function removeMessage() {
        $("#base64-image div.alert").remove();
    }

    function showDeleteButton() {
        $("#base64-image .btn-remove").removeClass('hidden');
    }

    function hideDeleteButton() {
        $("#base64-image .btn-remove").addClass('hidden');
    }


    function isValidImageFile(file) {
        // Check file size.
        if (file.size / 1024 > options.maxFileSizeKb) {
            var message = gettext("Image is too large (max %skB).")
            message = interpolate(message, [options.maxFileSizeKb])
            return {result: false, message: message};
        }
        // Check image format by file extension.
        var fileExtension = getFileExtension(file.name);
        if ($.inArray(fileExtension, options.allowedFormats) > -1) {
            return {result: true};
        }
        else {
            return {result: false, message: gettext("Image type is not allowed.")};
        }
    }

    function submitImage(file) {
        var isValid = isValidImageFile(file);
        if (isValid.result) {
            var fileReader = new FileReader();
            fileReader.onload = function (e) {
                updateThumbnail(e.target.result);
                removeMessage();
                showDeleteButton();
            };
            fileReader.onerror = function () {
                displayMessage(gettext("Error loading image file."));
            };
            fileReader.readAsDataURL(file);
        } else {
            var message = (typeof isValid.message !== 'undefined') ? isValid.message : 'unknown Error';
            displayMessage(message);
        }
    }

    function getFileExtension(path) {
        return path.substr(path.lastIndexOf('.') + 1).toLowerCase();
    }
}(jQuery));
