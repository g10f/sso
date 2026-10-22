const gulp = require('gulp');
const sass = require('gulp-sass')(require('sass'));
const sourcemaps = require('gulp-sourcemaps');
const rename = require("gulp-rename");

// loadPaths '.': the theme scss imports node_modules/... and ../sso/... relative to the repo root, which the
// modern Sass API (gulp-sass 6), unlike the legacy one, doesn't search by itself.
// quietDeps: no deprecation warnings from Bootstrap's scss. silenceDeprecations 'import': Bootstrap 5
// only works with @import; sass is limited to ^1 in package.json, Dart Sass 3 removes @import.
function buildStyles() {
    return gulp.src(global.config.srcCss)
        .pipe(sourcemaps.init())
        .pipe(sass({loadPaths: ['node_modules', '.'], quietDeps: true, silenceDeprecations: ['import']}).on('error', sass.logError))
        .pipe(sourcemaps.write('.'))
        .pipe(gulp.dest(global.config.buildCss))
}

function buildMinStyles() {
    return gulp.src(global.config.srcCss)
        .pipe(sass({loadPaths: ['node_modules', '.'], quietDeps: true, silenceDeprecations: ['import'], style: 'compressed'}).on('error', sass.logError))
        .pipe(rename({extname: '.min.css'}))
        .pipe(gulp.dest(global.config.buildCss))
}

module.exports = {buildStyles, buildMinStyles}
