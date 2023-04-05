const gulp = require('gulp');
const {parallel} = require('gulp');
const {buildStyles, buildMinStyles} = require('./gulp/buildStyles.js');

global.config = {
    srcCss: [
        './apps/sso/static/scss/main.scss',
        './apps/sso/static/scss/select2.scss'],
    buildCss: './apps/sso/static/css'
};

function copyJavaScriptFiles() {
    return gulp.src([
        './node_modules/@github/webauthn-json/dist/esm/webauthn-json.browser-ponyfill.js',
        './node_modules/@github/webauthn-json/dist/esm/webauthn-json.browser-ponyfill.js.map',
        './node_modules/bootstrap/dist/js/bootstrap.bundle.min.js',
        './node_modules/bootstrap/dist/js/bootstrap.bundle.min.js.map',
        './node_modules/jquery/dist/jquery.min.js',
        './node_modules/select2/dist/js/select2.min.js'
    ]).pipe(gulp.dest('./apps/sso/static/js/vendor'))
}

function copyFontFiles() {
    return gulp.src([
        './node_modules/bootstrap-icons/font/*.css',
        './node_modules/bootstrap-icons/font/**//fonts/*.*'
    ]).pipe(gulp.dest('./apps/sso/static/font'))
}

function copyCropperFiles() {
    return gulp.src([
        './node_modules/cropperjs/dist/cropper.min.js',
        './node_modules/cropperjs/dist/cropper.min.css'
    ]).pipe(gulp.dest('./apps/sso/static/vendor'))
}

exports.default = parallel(buildStyles, buildMinStyles, copyJavaScriptFiles, copyFontFiles, copyCropperFiles);

exports.watch = function () {
    gulp.watch(['./apps/sso/static/scss/**/*.scss'], parallel(buildStyles, buildMinStyles));
};
