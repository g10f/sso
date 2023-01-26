(function () {
    const togglePassword = document.querySelector("#toggle-password ");
    togglePassword.addEventListener("click", function () {
        // toggle the type attribute
        const input = this.parentNode.querySelector("input");
        const type = input.getAttribute("type") === "password" ? "text" : "password";
        input.setAttribute("type", type);
        // toggle the icon
        const use = this.querySelector("svg use");
        const href = use.getAttribute("xlink:href") === "#bi-eye" ? "#bi-eye-slash" : "#bi-eye";
        use.setAttribute("xlink:href", href);
    });
})();
