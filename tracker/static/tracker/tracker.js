
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
                `HTTP Error: ${response.status}`
            );
        }

        const data = await response.json();

        renderNutrition(data.nutrients);
        renderBadges(data.badges, data.badges_earned);

    } catch (error) {
        console.error("Tracker error:", error);

        document.getElementById(
            "nutrition-container"
        ).textContent = "Gagal memuat data nutrisi.";

        document.getElementById(
            "badges-container"
        ).textContent = "Gagal memuat achievement.";
    }
}


// =======================
// NUTRITION TRACKING
// =======================

function renderNutrition(nutrients) {
    const container = document.getElementById("nutrition-container");
    if (!container) return;

    container.replaceChildren();

   
    const metaMap = {
        Protein: {
            icon: "↗",
            iconClass: "icon-protein",
            ringColor: "#80B088"
        },
        Carbs: {
            icon: "↗",
            iconClass: "icon-carbs",
            ringColor: "#EE8252"
        },
        Fat: {
            icon: "↗",
            iconClass: "icon-fat",
            ringColor: "#E8CC63"
        }
    };


    nutrients.forEach((nutrient) => {
        const meta = metaMap[nutrient.name] || {
            icon: "•",
            iconClass: "",
            ringColor: "#EE8252"
        };

        const percent = Math.max(0, Math.min(100, Number(nutrient.percent) || 0));

        const card = document.createElement("article");
        card.className = "tracker-card tracker-progress-card";

        card.innerHTML = `
            <div class="tracker-progress-top">
                <div class="tracker-progress-icon ${meta.iconClass}">
                    ${meta.icon}
                </div>
                <h4 class="tracker-progress-name">${nutrient.name}</h4>
            </div>

            <div class="tracker-progress-ring-wrap">
                <div class="tracker-progress-ring"
                     style="--percent:${percent}; --ring-color:${meta.ringColor};">
                    <span>${percent}%</span>
                </div>
            </div>

            <div class="tracker-progress-meta">
                <p class="tracker-progress-value">${nutrient.current}${nutrient.unit}</p>
                <p class="tracker-progress-target">Target: ${nutrient.target}${nutrient.unit}</p>
            </div>
        `;

        container.appendChild(card);
    });
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

    if (!badges || badges.length === 0) {
        const empty = document.createElement("p");
        empty.className = "tracker-placeholder-text";
        empty.textContent = "Belum ada achievement tersedia.";
        container.appendChild(empty);
        return;
    }

    badges.forEach((badge) => {
        const item = document.createElement("div");
        item.className = "tracker-badge-item";

        item.innerHTML = `
            <div class="tracker-badge-icon">
                ${badge.icon || "🏆"}
            </div>
            <div class="tracker-badge-content">
                <h4>${badge.name}</h4>
                <p>${badge.description}</p>
                <span class="tracker-badge-status ${badge.earned ? "unlocked" : "locked"}">
                    ${badge.earned ? "Unlocked" : `Progress ${badge.progress}%`}
                </span>
            </div>
        `;

        container.appendChild(item);
    });
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
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        renderCookingHistory(data.history);

    } catch (error) {
        console.error("History error:", error);

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


// Render Cooking History
function renderCookingHistory(history) {
    const container = document.getElementById(
        "history-container"
    );

    if (!container) return;

    container.replaceChildren();

    if (!history || history.length === 0) {
        const empty = document.createElement("p");

        empty.className = "tracker-placeholder-text";
        empty.textContent =
            "Belum ada aktivitas memasak. Yuk mulai masak!";

        container.appendChild(empty);
        return;
    }

    history.forEach((item) => {
        const card = document.createElement("article");
        card.className = "tracker-history-item";

        const icon = document.createElement("div");
        icon.className = "tracker-history-icon";
        icon.textContent = "🍳";

        const content = document.createElement("div");
        content.className = "tracker-history-content";

        const title = document.createElement("h4");
        title.textContent =
            item.recipe_name || "Resep tanpa nama";

        const date = document.createElement("p");
        date.className = "tracker-history-date";
        date.textContent = formatCookingDate(
            item.cooked_on
        );

        const nutrients = document.createElement("p");
        nutrients.className = "tracker-history-nutrients";
        nutrients.textContent =
            `${item.calories} kcal • ` +
            `${item.protein}g protein`;

        content.append(title, date, nutrients);

        const status = document.createElement("span");
        status.className = "tracker-history-status";
        status.textContent = "Done";

        card.append(icon, content, status);
        container.appendChild(card);
    });
}

