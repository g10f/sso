$(function () {
    let cropper;
    let $base64_modal;
    let $base64_image;
    let $base64_input;

    $('[data-method="rotate"]').on('click', function () {
        if (cropper) {
            cropper.rotate($(this).data('option'));
        }
    });

    $('#crop').on('click', function () {
        if (cropper) {
            let canvas = cropper.getCroppedCanvas({
                width: 480,
                height: 480,
            });
            const dataUrl = canvas.toDataURL();
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
    });
});
