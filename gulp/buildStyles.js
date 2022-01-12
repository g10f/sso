const gulp = require('gulp');
const sass = require('gulp-sass')(require('sass'));
const sourcemaps = require('gulp-sourcemaps');
const rename = require("gulp-rename");

function buildStyles() {
    return gulp.src(global.config.srcCss)
        .pipe(sourcemaps.init())
        .pipe(sass().on('error', sass.logError))
        .pipe(sourcemaps.write('.'))
        .pipe(gulp.dest(global.config.buildCss))
}

function buildMinStyles() {
    return gulp.src(global.config.srcCss)
        .pipe(sass({outputStyle: 'compressed'}).on('error', sass.logError))
        .pipe(rename({extname: '.min.css'}))
        .pipe(gulp.dest(global.config.buildCss))
}

module.exports = {buildStyles, buildMinStyles}
