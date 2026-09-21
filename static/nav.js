// Mobile sidebar toggle. Silently does nothing on pages that don't have
// these elements (there aren't any right now, but harmless either way).
document.addEventListener("DOMContentLoaded", () => {
    const shell = document.querySelector(".app-shell");
    const toggle = document.querySelector(".menu-toggle");
    const backdrop = document.querySelector(".sidebar-backdrop");

    if (!shell || !toggle) return;

    toggle.addEventListener("click", () => {
        shell.classList.toggle("sidebar-open");
    });

    if (backdrop) {
        backdrop.addEventListener("click", () => {
            shell.classList.remove("sidebar-open");
        });
    }
});
