const gulp = require('gulp');
const sass = require('gulp-sass')(require('sass'));
const sourcemaps = require('gulp-sourcemaps');
const rename = require("gulp-rename");
const {parallel} = require('gulp');
const {buildStyles, buildMinStyles} = require('./gulp/buildStyles.js');

global.config = {
    srcCss: ['./apps/sso/static/scss/main.scss', './apps/sso/static/scss/select2.scss'], buildCss: './apps/sso/static/css'
};

function copyJavaScriptFiles() {
    return gulp.src([
        './node_modules/bootstrap/dist/js/*.*',
        './node_modules/jquery/dist/*.*'])
        .pipe(gulp.dest('./apps/sso/static/js/vendor'))
}

function copyFontFiles() {
    return gulp.src([
        './node_modules/bootstrap-icons/font/*.css',
        './node_modules/bootstrap-icons/font/**//fonts/*.*',
    ]).pipe(gulp.dest('./apps/sso/static/font'))
}

exports.default = parallel(buildStyles, buildMinStyles, copyJavaScriptFiles, copyFontFiles);

exports.watch = function () {
    gulp.watch(['./apps/sso/static/scss/**/*.scss'], parallel(buildStyles, buildMinStyles));
};
