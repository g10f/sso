(() => {
    'use strict';

    function initTheme() {
        // set theme defined in localStorage if there is one, or fallback to auto mode
        const currentTheme = localStorage.getItem("theme");
        if (currentTheme) {
            setTheme(currentTheme);
        } else {
            const default_theme = document.documentElement.getAttribute('data-default-theme');
            setTheme(default_theme);
        }
    }

    function setTheme(mode) {
        if (mode !== "light" && mode !== "dark" && mode !== "auto") {
            console.error(`Got invalid theme mode: ${mode}. Resetting to auto.`);
            mode = "auto";
        }
        // set data-bs-color-mode, that we know what color mode icon is active
        document.documentElement.setAttribute('data-theme', mode)
        // data-bs-theme for bootstrap
        if (mode === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.documentElement.setAttribute('data-bs-theme', 'dark')
        } else {
            document.documentElement.setAttribute('data-bs-theme', mode)
        }
        localStorage.setItem("theme", mode);
    }

    function cycleTheme() {
        const currentTheme = localStorage.getItem("theme") || "auto";
        const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

        if (prefersDark) {
            // Auto (dark) -> Light -> Dark
            if (currentTheme === "auto") {
                setTheme("light");
            } else if (currentTheme === "light") {
                setTheme("dark");
            } else {
                setTheme("auto");
            }
        } else {
            // Auto (light) -> Dark -> Light
            if (currentTheme === "auto") {
                setTheme("dark");
            } else if (currentTheme === "dark") {
                setTheme("light");
            } else {
                setTheme("auto");
            }
        }
    }

    function setupTheme() {
        // Attach event handlers for toggling themes
        const buttons = document.getElementsByClassName("theme-toggle");
        Array.from(buttons).forEach((btn) => {
            btn.addEventListener("click", cycleTheme);
        });
    }

    window.addEventListener('DOMContentLoaded', function (e) {
        setupTheme();
    });

    initTheme();
})();
