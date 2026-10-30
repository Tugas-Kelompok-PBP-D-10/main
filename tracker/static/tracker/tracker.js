const badgeIcons = {
    FIRST_COOK: "chef-hat",
    STREAK_3: "flame",
    TOTAL_10: "trophy"
};

const nutrientIcons = {
    Protein: "trending-up",
    Carbs: "chart-no-axes-column-increasing",
    Fat: "activity"
};

document.addEventListener("DOMContentLoaded", () => {
    loadTrackerDashboard();
    loadCookingHistory();
});

async function loadTrackerDashboard() {
    const dashboard = document.getElementById(
        "tracker-dashboard"
    );

    if (!dashboard) return;

    const apiUrl = dashboard.dataset.apiUrl;

    let data;

    try {
        const response = await fetch(apiUrl, {
            method: "GET",
            credentials: "same-origin",
            headers: {
                "Accept": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(
                `Dashboard API: HTTP ${response.status}`
            );
        }

        data = await response.json();

    } catch (error) {
        console.error("DASHBOARD API ERROR:", error);
        return;
    }


    try {
        renderNutrition(data.nutrients || []);
    } catch (error) {
        console.error("NUTRITION ERROR:", error);
    }


    try {
        renderBadges(
            data.badges || [],
            data.badges_earned || 0
        );
    } catch (error) {
        console.error("BADGES ERROR:", error);
    }

    
    if (typeof renderStreak === "function") {
        try {
            renderStreak(data.streak, data.week);
        } catch (error) {
            console.error("STREAK ERROR:", error);
        }
    }
}

// =======================
// NUTRITION TRACKING
// =======================
function renderNutrition(nutrients) {
    const container = document.getElementById(
        "nutrition-container"
    );

    if (!container) return;

    const nutrientIcons = {
        Protein: "trending-up",
        Carbs: "chart-no-axes-column-increasing",
        Fat: "activity"
    };

    const nutrientColors = {
        Protein: "#80B088",
        Carbs: "#EE8252",
        Fat: "#E8CC63"
    };

    // Siapkan elemen baru sebelum mengganti isi container
    const fragment = document.createDocumentFragment();

    nutrients.forEach((nutrient) => {
        const card = document.createElement("article");
        card.className = "tracker-card tracker-progress-card";

        // HEADER
        const header = document.createElement("div");
        header.className = "tracker-progress-top";

        const iconBox = document.createElement("div");
        iconBox.className = "tracker-progress-icon";
        iconBox.classList.add(
            `icon-${nutrient.name.toLowerCase()}`
        );

        const icon = document.createElement("i");
        icon.setAttribute(
            "data-lucide",
            nutrientIcons[nutrient.name] || "activity"
        );

        iconBox.appendChild(icon);

        const title = document.createElement("h4");
        title.className = "tracker-progress-name";
        title.textContent = nutrient.name;

        header.append(iconBox, title);

        // NUTRITION PERCENT
        const hasTarget =
            nutrient.target !== null &&
            nutrient.target !== undefined &&
            Number(nutrient.target) > 0;

        const percent = hasTarget
            ? Math.max(
                0,
                Math.min(100, Number(nutrient.percent) || 0)
            )
            : 0;

        // PROGRESS RING
        const ringWrap = document.createElement("div");
        ringWrap.className = "tracker-progress-ring-wrap";

        const ring = document.createElement("div");
        ring.className = "tracker-progress-ring";

        ring.style.setProperty("--percent", percent);
        ring.style.setProperty(
            "--ring-color",
            nutrientColors[nutrient.name] || "#03695E"
        );

        const ringText = document.createElement("span");

        ringText.textContent = hasTarget
            ? `${percent}%`
            : "—";

        ring.appendChild(ringText);
        ringWrap.appendChild(ring);

        // NUTRITION VALUES
        const meta = document.createElement("div");
        meta.className = "tracker-progress-meta";

        const value = document.createElement("p");
        value.className = "tracker-progress-value";
        value.textContent =
            `${nutrient.current}${nutrient.unit}`;

        // Buat elemen target SEBELUM menggunakannya
        const target = document.createElement("p");
        target.className = "tracker-progress-target";

        target.textContent = hasTarget
            ? `Target: ${nutrient.target}${nutrient.unit}`
            : "Target not set";

        meta.append(value, target);

        // GABUNGKAN CARD
        card.append(header, ringWrap, meta);
        fragment.appendChild(card);
    });

    // Ganti isi container setelah seluruh kartu berhasil dibuat
    container.replaceChildren(fragment);

    // Aktifkan icon Lucide
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

// =======================
// ACHIEVEMENT BADGES
// =======================

function renderBadges(badges, earnedCount) {
    const container = document.getElementById("badges-container");
    const summary = document.getElementById("badge-summary");

    if (!container) return;

    if (summary) {
        summary.textContent = `${earnedCount} badge unlocked`;
    }

    container.replaceChildren();

    const badgeIcons = {
        FIRST_COOK: "chef-hat",
        STREAK_3: "flame",
        TOTAL_10: "trophy"
    };

    if (!badges || badges.length === 0) {
        const empty = document.createElement("p");
        empty.className = "tracker-placeholder-text";
        empty.textContent = "Belum ada achievement tersedia.";

        container.appendChild(empty);
        return;
    }

    badges.forEach((badge) => {

       
        const item = document.createElement("article");
        item.className = "tracker-badge-item";

       
        const iconBox = document.createElement("div");
        iconBox.className = "tracker-badge-icon";

        const iconElement = document.createElement("i");
        iconElement.setAttribute(
            "data-lucide",
            badgeIcons[badge.code] || "award"
        );

        iconBox.appendChild(iconElement);

        
        const content = document.createElement("div");
        content.className = "tracker-badge-content";

        const name = document.createElement("h4");
        name.textContent = badge.name;

        const description = document.createElement("p");
        description.textContent = badge.description;

        const status = document.createElement("span");
        status.className = badge.earned
            ? "tracker-badge-status unlocked"
            : "tracker-badge-status locked";

        status.textContent = badge.earned
            ? "Unlocked"
            : `Progress ${badge.progress}%`;

        content.append(name, description, status);

       
        item.append(iconBox, content);

       
        container.appendChild(item);
    });


    if (window.lucide) {
        window.lucide.createIcons();
    }
}

async function loadCookingHistory() {
    const dashboard = document.getElementById(
        "tracker-dashboard"
    );

    const container = document.getElementById(
        "history-container"
    );

    if (!dashboard || !container) return;

    try {
        const response = await fetch(
            dashboard.dataset.historyUrl,
            {
                method: "GET",
                credentials: "same-origin",
                headers: {
                    "Accept": "application/json"
                }
            }
        );

        if (!response.ok) {
            throw new Error(
                `History API: HTTP ${response.status}`
            );
        }

        const data = await response.json();

        console.log("COOKING HISTORY:", data);

        if (!data.success) {
            throw new Error("Gagal mengambil riwayat.");
        }

        renderCookingHistory(data.history || []);

    } catch (error) {
        console.error("COOKING HISTORY ERROR:", error);

        container.textContent =
            "Gagal memuat riwayat memasak.";
    }
}

// Format tanggal
function formatCookingDate(dateString) {
    const [year, month, day] = dateString
        .split("-")
        .map(Number);

    const date = new Date(year, month - 1, day);

    return new Intl.DateTimeFormat("id-ID", {
        day: "numeric",
        month: "short",
        year: "numeric"
    }).format(date);
}


function renderCookingHistory(history) {
    const container = document.getElementById("history-container");

    if (!container) return;

    container.replaceChildren();

    if (history.length === 0) {
        const empty = document.createElement("p");
        empty.className = "tracker-placeholder-text";
        empty.textContent =
            "Belum ada aktivitas memasak. Yuk mulai masak!";

        container.appendChild(empty);
        return;
    }

    history.forEach((log) => {
        const item = document.createElement("article");
        item.className = "tracker-history-item";

        const iconBox = document.createElement("div");
        iconBox.className = "tracker-history-icon";

        const icon = document.createElement("i");
        icon.setAttribute("data-lucide", "chef-hat");
        iconBox.appendChild(icon);

        const content = document.createElement("div");
        content.className = "tracker-history-content";

        const title = document.createElement("h4");
        title.textContent = log.recipe_name || "Cooking";

        const date = document.createElement("p");
        date.className = "tracker-history-date";
        date.textContent = log.cooked_on;

        const nutrients = document.createElement("p");
        nutrients.className = "tracker-history-nutrients";
        nutrients.textContent =
            `${log.calories} kcal · ` +
            `P ${log.protein}g · ` +
            `C ${log.carbs}g · ` +
            `F ${log.fat}g`;

        content.append(title, date, nutrients);

        const status = document.createElement("span");
        status.className = "tracker-history-status";
        status.textContent = "Completed";

        item.append(iconBox, content, status);
        container.appendChild(item);
    });

    if (window.lucide) {
        window.lucide.createIcons();
    }
}


/* ==========================================
   SET WEEKLY NUTRITION TARGET — AJAX
========================================== */
document.addEventListener("DOMContentLoaded", () => {
    const dashboard = document.getElementById("tracker-dashboard");
    const openBtn = document.getElementById("tracker-set-target-btn");
    const deleteBtn = document.getElementById("delete-target-btn");
    const dialog = document.getElementById("tracker-target-dialog");
    const closeBtn = document.getElementById("tracker-target-close");
    const cancelBtn = document.getElementById("tracker-target-cancel");
    const form = document.getElementById("tracker-target-form");
    const saveBtn = document.getElementById("tracker-target-save");
    const message = document.getElementById("tracker-target-message");

    const proteinInput = document.getElementById("tracker-target-protein");
    const carbsInput = document.getElementById("tracker-target-carbs");
    const fatInput = document.getElementById("tracker-target-fat");

    if (
        !dashboard || !openBtn || !dialog ||
        !closeBtn || !cancelBtn || !form ||
        !saveBtn || !message ||
        !proteinInput || !carbsInput || !fatInput
    ) {
        console.error("Nutrition Target: elemen HTML tidak lengkap.");
        return;
    }

    const targetUrl = dashboard.dataset.nutritionTargetUrl;
    const dashboardUrl = dashboard.dataset.apiUrl;

    const csrfToken = form.querySelector(
        'input[name="csrfmiddlewaretoken"]'
    )?.value;

    function showMessage(text, isError = false) {
        message.textContent = text;
        message.classList.toggle("is-error", isError);
    }

    function closeDialog() {
        dialog.close();
        showMessage("");
    }

    // Buka modal dan tampilkan target yang sudah tersimpan
    openBtn.addEventListener("click", async () => {
        showMessage("");

        dialog.showModal();

        try {
            const response = await fetch(targetUrl, {
                method: "GET",
                credentials: "same-origin"
            });

            if (!response.ok) {
                throw new Error("Gagal mengambil target nutrisi.");
            }

            const result = await response.json();

            proteinInput.value = result.target?.protein_g ?? "";
            carbsInput.value = result.target?.carbs_g ?? "";
            fatInput.value = result.target?.fat_g ?? "";

        } catch (error) {
            console.error(error);
            showMessage(error.message, true);
        }
    });

    closeBtn.addEventListener("click", closeDialog);
    cancelBtn.addEventListener("click", closeDialog);


    // DELETE NUTRITION TARGET
    if (deleteBtn) {
        deleteBtn.addEventListener("click", async () => {
            const confirmed = window.confirm(
                "Yakin ingin menghapus Nutrition Target?"
            );

            if (!confirmed) return;

            if (!csrfToken) {
                showMessage("CSRF token tidak ditemukan.", true);
                return;
            }

            deleteBtn.disabled = true;
            showMessage("");

            try {
                const response = await fetch(targetUrl, {
                    method: "DELETE",
                    credentials: "same-origin",
                    headers: {
                        "X-CSRFToken": csrfToken
                    }
                });

                const result = await response.json();

                if (!response.ok || !result.success) {
                    throw new Error(
                        result.message || "Gagal menghapus target."
                    );
                }

                // Kosongkan form target
                proteinInput.value = "";
                carbsInput.value = "";
                fatInput.value = "";

                // Tutup dialog
                closeDialog();

                // Ambil ulang dashboard setelah target dihapus
                await loadTrackerDashboard();

            } catch (error) {
                console.error(error);
                showMessage(error.message, true);
            } finally {
                deleteBtn.disabled = false;
            }
        });
    }

    // Simpan target menggunakan AJAX
    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        showMessage("");

        const protein = Number(proteinInput.value);
        const carbs = Number(carbsInput.value);
        const fat = Number(fatInput.value);

        const values = [protein, carbs, fat];

        if (
            values.some(
                (value) =>
                    !Number.isInteger(value) ||
                    value < 1 ||
                    value > 10000
            )
        ) {
            showMessage(
                "Target harus berupa angka bulat antara 1–10000.",
                true
            );
            return;
        }

        if (!csrfToken) {
            showMessage("CSRF token tidak ditemukan.", true);
            return;
        }

        saveBtn.disabled = true;
        saveBtn.textContent = "Saving...";

        try {
            const response = await fetch(targetUrl, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                body: JSON.stringify({
                    protein_g: protein,
                    carbs_g: carbs,
                    fat_g: fat
                })
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(
                    result.message || "Gagal menyimpan target."
                );
            }

            // Refresh data Nutrition Tracking tanpa reload
            const dashboardResponse = await fetch(dashboardUrl, {
                method: "GET",
                credentials: "same-origin"
            });

            if (!dashboardResponse.ok) {
                throw new Error(
                    "Target tersimpan, tetapi grafik gagal diperbarui."
                );
            }

            const dashboardData = await dashboardResponse.json();

            renderNutrition(dashboardData.nutrients);
            closeDialog();

        } catch (error) {
            console.error(error);
            showMessage(error.message, true);
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = "Save Target";
        }
    });
});


