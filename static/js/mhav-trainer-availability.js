(() => {
    "use strict";

    const form = document.getElementById("availability-form");
    if (!form) return;

    const tiles = Array.from(form.querySelectorAll(".mhav-availability-tile"));
    const help = document.getElementById("date-help");
    const summary = document.getElementById("availability-summary");
    const symbols = { yes: "✓", no: "✕", maybe: "?", unset: "○" };
    const names = {
        yes: "Beschikbaar",
        no: "Niet beschikbaar",
        maybe: "Weet ik nog niet",
        unset: "Nog niet ingevuld"
    };

    function mode() {
        return form.querySelector('input[name="response"]:checked')?.value || "partial";
    }

    function render() {
        const currentMode = mode();
        const totals = { yes: 0, no: 0, maybe: 0, unset: 0 };

        for (const tile of tiles) {
            const input = tile.querySelector('input[type="hidden"]');
            const state = currentMode === "all" ? "yes"
                : currentMode === "none" ? "no" : input.value;
            tile.dataset.state = state;
            tile.querySelector(".mhav-date-symbol").textContent = symbols[state];
            tile.querySelector(".mhav-date-symbol").setAttribute("title", names[state]);
            tile.querySelectorAll("[data-set-state]").forEach(button => {
                button.disabled = currentMode !== "partial";
                button.setAttribute("aria-pressed", String(button.dataset.setState === state));
            });
            totals[state] += 1;
        }

        help.textContent = currentMode === "all"
            ? "Je bevestigt dat je op alle lesdagen beschikbaar bent."
            : currentMode === "none"
                ? "Je geeft aan dat je op geen enkele lesdag beschikbaar bent."
                : "Grijze lesdagen zijn nog niet ingevuld. Kies per lesdag ✓, ✕ of ?.";
        summary.textContent = `${totals.yes} beschikbaar · ${totals.no} niet beschikbaar · ` +
            `${totals.maybe} onzeker · ${totals.unset} nog niet ingevuld`;
    }

    for (const tile of tiles) {
        tile.querySelectorAll("[data-set-state]").forEach(button => {
            button.addEventListener("click", () => {
                const input = tile.querySelector('input[type="hidden"]');
                input.value = input.value === button.dataset.setState
                    ? "unset" : button.dataset.setState;
                render();
            });
        });
    }

    form.querySelectorAll('input[name="response"]').forEach(radio => {
        radio.addEventListener("change", () => {
            if (radio.checked && radio.value === "partial") {
                tiles.forEach(tile => {
                    tile.querySelector('input[type="hidden"]').value = "unset";
                });
            }
            render();
        });
    });

    form.addEventListener("submit", () => {
        const currentMode = mode();
        if (currentMode === "all" || currentMode === "none") {
            const state = currentMode === "all" ? "yes" : "no";
            tiles.forEach(tile => {
                tile.querySelector('input[type="hidden"]').value = state;
            });
        }
    });

    render();
})();
