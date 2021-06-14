$(function () {
    let cropper;
    let $base64_modal;
    let $base64_image;
    let $base64_input;
    let maxFileSize = $('input[type="text"].base64-image').data("max-file-size");
    let width = $('input[type="text"].base64-image').data("width");
    let height = $('input[type="text"].base64-image').data("height");
    maxFileSize = maxFileSize === '' ? 1048576 : maxFileSize;  // defaultt 1 MB
    width = width === '' ? 550 : width;
    height = height === '' ? 550 : height;

    // initialize the image from the input field, so we don't need to transfer the same data twice
    $('img.base64-image').each(function (index) {
        if ($(this).data('id') !== undefined) {
            $input = $('#' + $(this).data('id'));
            if ($input.val()) {
                $(this).attr('src', $input.val());
            }
        }
    });

    const displayMessage = function(message, type) {
        type = (typeof type !== 'undefined') ? type : 'alert-danger';
        $alert = $base64_modal.find('.alert');
        $alert.text(message);
        $alert.addClass(type);
        $alert.removeClass('hidden');
    }

    $('[data-method="rotate"]').on('click', function () {
        if (cropper) {
            cropper.rotate($(this).data('option'));
        }
    });

    $('#crop').on('click', function () {
        if (cropper) {
            let canvas = cropper.getCroppedCanvas({
                width: width,
                height: height,
            });
            const dataUrl = canvas.toDataURL();
            if (dataUrl.length > maxFileSize * 1.37) {
                var message = gettext("Image is too large (max %skB).")
                message = interpolate(message, [parseInt(maxFileSize/1024)])
                displayMessage(message);
                return;
            }
            $base64_image.attr('src', dataUrl);
            $base64_input.val(dataUrl);
        }
        $base64_modal.modal('hide');
    });

    $('input[type="file"].base64-image').on('change', function () {
        const files = this.files;
        const $this = $(this);
        $base64_image = $this.siblings("img");
        $base64_input = $('#' + $this.data('id'));
        $base64_modal = $('#' + $this.data('modal-id'));

        const done = function (url) {
            $this.val('');
            $('img', $base64_modal).attr('src', url);
            $base64_modal.modal('show');
        };

        if (files && files.length > 0) {
            const file = files[0];
            if (URL) {
                done(URL.createObjectURL(file));
            } else if (FileReader) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    done(reader.result);
                };
                reader.readAsDataURL(file);
            }
        }
    });

    $('.modal.base64-image').on('shown.bs.modal', function () {
        cropper = new Cropper($('img', this)[0], {
            dragMode: 'move',
            aspectRatio: 1,
            viewMode: 3,
        });
    }).on('hidden.bs.modal', function () {
        cropper.destroy();
        cropper = null;
        $('img', this).attr('src', '');
        $base64_modal.find('.alert').addClass('hidden');
    });
});
