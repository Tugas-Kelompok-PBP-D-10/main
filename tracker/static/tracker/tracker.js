
document.addEventListener("DOMContentLoaded", () => {
    loadTrackerDashboard();
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
