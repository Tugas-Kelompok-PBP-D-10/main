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
    const container = document.getElementById(
        "nutrition-container"
    );

    if (!container) return;

    container.replaceChildren();

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

    nutrients.forEach((nutrient) => {
        const card = document.createElement("article");
        card.className = "tracker-card tracker-progress-card";

        
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

       
        const percent = Math.max(
            0,
            Math.min(100, Number(nutrient.percent) || 0)
        );

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
        ringText.textContent = `${percent}%`;

        ring.appendChild(ringText);
        ringWrap.appendChild(ring);

       
        const meta = document.createElement("div");
        meta.className = "tracker-progress-meta";

        const value = document.createElement("p");
        value.className = "tracker-progress-value";
        value.textContent =
            `${nutrient.current}${nutrient.unit}`;

        const target = document.createElement("p");
        target.className = "tracker-progress-target";
        target.textContent =
            `Target: ${nutrient.target}${nutrient.unit}`;

        meta.append(value, target);

       
        card.append(header, ringWrap, meta);
        container.appendChild(card);
    });

    
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
        icon.className = "tracker-badge-icon";

        if (badge.icon) {
            const image = document.createElement("img");

            image.src = badge.icon;
            image.alt = badge.name;
            image.loading = "lazy";

            icon.appendChild(image);
        } else {
            icon.textContent = "🏆";
        }
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

