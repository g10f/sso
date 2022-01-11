const gulp = require('gulp');
const sass = require('gulp-sass')(require('sass'));
const sourcemaps = require('gulp-sourcemaps');
const rename = require("gulp-rename");
const {parallel} = require('gulp');

const config = {
    srcCss: ['./apps/sso/static/scss/main.scss', './apps/sso/static/scss/select2.scss'], buildCss: './apps/sso/static/css'
};

function buildStyles() {
    return gulp.src(config.srcCss)
        .pipe(sourcemaps.init())
        .pipe(sass().on('error', sass.logError))
        .pipe(sourcemaps.write('.'))
        .pipe(gulp.dest(config.buildCss))
}

function buildMinStyles() {
    return gulp.src(config.srcCss)
        .pipe(sass({outputStyle: 'compressed'}).on('error', sass.logError))
        .pipe(rename({extname: '.min.css'}))
        .pipe(gulp.dest(config.buildCss))
}

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

exports.copy = parallel(copyJavaScriptFiles, copyFontFiles);
exports.default = parallel(buildStyles);
exports.all = parallel(buildStyles, buildMinStyles, copyJavaScriptFiles, copyFontFiles);

exports.watch = function () {
    gulp.watch(config.srcCss, parallel(buildStyles, buildMinStyles));
};
