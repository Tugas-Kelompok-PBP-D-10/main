(function () {
    "use strict";

    function initRecipeModal() {
        const grid = document.querySelector(".recipe-grid");
        const overlay = document.getElementById("nutritionModal");
        const modal = overlay && overlay.querySelector(".recipe-modal");
        const closeButton = document.getElementById("btnCloseModal");
        if (!grid || !overlay || !modal || !closeButton || overlay.dataset.initialized) {
            return;
        }
        overlay.dataset.initialized = "true";

        for (const actionArea of grid.querySelectorAll(".recipe-card-actions[data-login-url]")) {
            const loginAnchor = actionArea.querySelector(".vote-login");
            if (loginAnchor) loginAnchor.href = actionArea.dataset.loginUrl;
        }
        for (const cardImage of grid.querySelectorAll(".recipe-img")) {
            cardImage.addEventListener("error", function () {
                cardImage.hidden = true;
                const placeholder = cardImage.parentElement.querySelector(".recipe-img-placeholder");
                if (placeholder) placeholder.hidden = false;
            }, { once: true });
        }

        const title = document.getElementById("modalTitle");
        const status = document.getElementById("recipeModalStatus");
        const error = document.getElementById("recipeModalError");
        const details = document.getElementById("recipeModalDetails");
        const image = document.getElementById("modalImage");
        const imagePlaceholder = document.getElementById("modalImagePlaceholder");
        const description = document.getElementById("modalDescription");
        const source = document.getElementById("modalSource");
        const preparationTime = document.getElementById("modalPreparationTime");
        const cookingTime = document.getElementById("modalCookingTime");
        const ingredientsSection = document.getElementById("ingredientsSection");
        const ingredientsList = document.getElementById("modalIngredients");
        const instructionsSection = document.getElementById("instructionsSection");
        const instructionsList = document.getElementById("modalInstructions");
        const instructionsEmpty = document.getElementById("instructionsEmpty");
        const nutritionEmpty = document.getElementById("nutritionEmpty");
        const nutritionAdditional = document.getElementById("nutritionAdditional");
        const nutritionBasisLabel = document.getElementById("nutritionBasisLabel");
        const nutritionTotalsSection = document.getElementById("nutritionTotalsSection");
        const nutritionTotalsHeading = document.getElementById("nutritionTotalsHeading");
        const nutritionTotals = document.getElementById("nutritionTotals");
        const servingCalculator = document.getElementById("servingCalculator");
        const servingsInput = document.getElementById("recipeServings");
        const originalServingsLabel = document.getElementById("originalServingsLabel");
        const completionPanel = document.getElementById("recipeCompletionPanel");
        const completionConfirm = document.getElementById("recipeCompletionConfirm");
        const completionButton = document.getElementById("recipeCompletionButton");
        const completionStatus = document.getElementById("recipeCompletionStatus");
        const loginPrompt = document.getElementById("recipeLoginPrompt");
        const loginLink = document.getElementById("recipeLoginLink");

        let activeCard = null;
        let previousFocus = null;
        let savedBodyOverflow = "";
        let closeTimer = null;
        let currentIngredients = [];
        let currentNutrition = {};
        let originalServings = null;

        function getCookie(name) {
            const cookies = document.cookie ? document.cookie.split(";") : [];
            for (const cookie of cookies) {
                const trimmed = cookie.trim();
                if (trimmed.startsWith(name + "=")) {
                    return decodeURIComponent(trimmed.slice(name.length + 1));
                }
            }
            return "";
        }

        async function requestJson(url, options) {
            const response = await fetch(url, {
                credentials: "same-origin",
                ...options,
                headers: {
                    Accept: "application/json",
                    ...(options && options.headers ? options.headers : {}),
                },
            });
            let payload = {};
            try {
                payload = await response.json();
            } catch (_error) {
                payload = {};
            }
            if (!response.ok) {
                const message =
                    payload.error && payload.error.message
                        ? payload.error.message
                        : "Permintaan belum berhasil.";
                const requestError = new Error(message);
                requestError.status = response.status;
                requestError.loginUrl = payload.login_url || "";
                throw requestError;
            }
            return payload;
        }

        function setStatus(message) {
            status.textContent = message || "";
        }

        function resetModal() {
            title.textContent = "";
            error.hidden = true;
            error.textContent = "";
            details.hidden = true;
            image.hidden = true;
            image.removeAttribute("src");
            imagePlaceholder.hidden = false;
            image.alt = "";
            description.hidden = true;
            description.textContent = "";
            source.hidden = true;
            source.textContent = "";
            preparationTime.hidden = true;
            preparationTime.textContent = "";
            cookingTime.hidden = true;
            cookingTime.textContent = "";
            ingredientsSection.hidden = true;
            ingredientsList.replaceChildren();
            servingCalculator.hidden = true;
            servingsInput.value = "";
            originalServingsLabel.textContent = "";
            currentIngredients = [];
            currentNutrition = {};
            originalServings = null;
            instructionsSection.hidden = true;
            instructionsList.replaceChildren();
            instructionsEmpty.hidden = true;
            nutritionAdditional.hidden = true;
            nutritionAdditional.replaceChildren();
            nutritionBasisLabel.textContent = "";
            nutritionTotalsSection.hidden = true;
            nutritionTotalsHeading.textContent = "";
            nutritionTotals.replaceChildren();
            nutritionEmpty.hidden = true;
            completionPanel.hidden = true;
            completionConfirm.checked = false;
            completionConfirm.disabled = false;
            completionButton.disabled = true;
            completionButton.textContent = "Tandai sudah dimasak";
            completionStatus.textContent = "";
            loginPrompt.hidden = true;
            for (const rowId of [
                "nutritionCaloriesRow",
                "nutritionProteinRow",
                "nutritionCarbsRow",
                "nutritionFatRow",
            ]) {
                document.getElementById(rowId).hidden = true;
            }
            for (const valueId of [
                "nutritionCaloriesValue",
                "nutritionProteinValue",
                "nutritionCarbsValue",
                "nutritionFatValue",
            ]) {
                document.getElementById(valueId).textContent = "";
            }
            setStatus("Memuat detail resep…");
        }

        function updateCardIndicators(recipeId, interaction) {
            for (const card of grid.querySelectorAll(".recipe-card-open")) {
                if (card.dataset.recipeId !== String(recipeId)) {
                    continue;
                }
                const viewed = card.querySelector(".recipe-status-viewed");
                const completed = card.querySelector(".recipe-status-completed");
                if (viewed) {
                    viewed.hidden = !interaction.viewed;
                }
                if (completed) {
                    completed.hidden = !interaction.completed;
                }
            }
        }

            
        function renderInteraction(recipeId, interaction) {
            const state = interaction || {};
            const isAuthenticated = Boolean(state.authenticated);

            completionPanel.hidden = !isAuthenticated;
            loginPrompt.hidden = isAuthenticated;

            updateCardIndicators(recipeId, state);

            // Setiap aktivitas memasak harus dikonfirmasi ulang.
            completionConfirm.checked = false;
            completionConfirm.disabled = !isAuthenticated;

            // Tombol aktif hanya setelah checkbox dicentang.
            completionButton.disabled = true;

            completionButton.textContent = "Tandai sudah dimasak";

            if (state.completed) {
                completionStatus.textContent =
                    "Resep ini pernah dimasak. Kamu bisa memasaknya lagi.";
            } else {
                completionStatus.textContent =
                    "Centang konfirmasi setelah selesai memasak resep.";
            }
        }

        function formatNumber(value) {
            return Number(value.toFixed(3)).toString();
        }

        function selectedServings() {
            const value = Number.parseInt(servingsInput.value, 10);
            return Number.isInteger(value) && value > 0 ? value : originalServings;
        }

        function renderNutrition(nutrition) {
            const rows = [
                ["calories", "nutritionCaloriesRow", "nutritionCaloriesValue"],
                ["protein", "nutritionProteinRow", "nutritionProteinValue"],
                ["carbohydrates", "nutritionCarbsRow", "nutritionCarbsValue"],
                ["fat", "nutritionFatRow", "nutritionFatValue"],
            ];
            let hasNutrition = false;
            const allNutrients = [];
            for (const [key, rowId, valueId] of rows) {
                const nutrient = nutrition && nutrition[key];
                const row = document.getElementById(rowId);
                const value = document.getElementById(valueId);
                if (nutrient && nutrient.value !== null && nutrient.value !== undefined) {
                    value.textContent =
                        String(nutrient.value) + (nutrient.unit ? " " + nutrient.unit : "");
                    row.hidden = false;
                    hasNutrition = true;
                    allNutrients.push({
                        name: row.querySelector("dt").textContent,
                        value: Number(nutrient.value),
                        unit: nutrient.unit || "",
                    });
                } else {
                    row.hidden = true;
                    value.textContent = "";
                }
            }

            const additional = nutrition && Array.isArray(nutrition.additional)
                ? nutrition.additional
                : [];
            for (const nutrient of additional) {
                if (!nutrient || nutrient.value === null || nutrient.value === undefined) {
                    continue;
                }
                const item = document.createElement("li");
                item.textContent =
                    String(nutrient.name || "Nutrisi") +
                    ": " +
                    String(nutrient.value) +
                    (nutrient.unit ? " " + nutrient.unit : "");
                nutritionAdditional.appendChild(item);
                hasNutrition = true;
                allNutrients.push({
                    name: String(nutrient.name || "Nutrisi"),
                    value: Number(nutrient.value),
                    unit: nutrient.unit || "",
                });
            }
            nutritionAdditional.hidden = nutritionAdditional.childElementCount === 0;
            nutritionEmpty.hidden = hasNutrition;

            const basis = nutrition && nutrition.basis ? nutrition.basis : "unknown";
            const basisLabels = {
                per_serving: "Nilai dasar ditampilkan per porsi.",
                whole_recipe: "Nilai dasar merupakan total resep awal.",
                mixed: "Sumber nutrisi bercampur; total tidak dihitung agar tidak menyesatkan.",
                unknown: "Dasar perhitungan nutrisi belum diketahui; total tidak dihitung.",
            };
            nutritionBasisLabel.textContent = basisLabels[basis] || basisLabels.unknown;
            nutritionTotals.replaceChildren();
            nutritionTotalsSection.hidden = true;
            const servings = selectedServings();
            if (!hasNutrition || !servings || !originalServings) {
                return;
            }

            let multiplier;
            if (basis === "per_serving") {
                multiplier = servings;
                nutritionTotalsHeading.textContent =
                    "Perkiraan total untuk " + servings + " porsi";
            } else if (basis === "whole_recipe") {
                multiplier = servings / originalServings;
                nutritionTotalsHeading.textContent =
                    "Perkiraan total untuk " + servings + " porsi";
            } else {
                return;
            }

            for (const nutrient of allNutrients) {
                if (!Number.isFinite(nutrient.value)) {
                    continue;
                }
                const row = document.createElement("div");
                row.className = "recipe-nutrition-row";
                const name = document.createElement("dt");
                name.textContent = nutrient.name;
                const value = document.createElement("dd");
                value.textContent =
                    formatNumber(nutrient.value * multiplier) +
                    (nutrient.unit ? " " + nutrient.unit : "");
                row.append(name, value);
                nutritionTotals.appendChild(row);
            }
            nutritionTotalsSection.hidden = nutritionTotals.childElementCount === 0;
        }

        function renderIngredients() {
            ingredientsList.replaceChildren();
            const servings = selectedServings();
            for (const ingredient of currentIngredients) {
                if (!ingredient || typeof ingredient !== "object") {
                    continue;
                }
                const item = document.createElement("li");
                const amount = Number(ingredient.amount);
                if (Number.isFinite(amount) && amount >= 0 && originalServings && servings) {
                    const scaledAmount = amount * (servings / originalServings);
                    item.textContent =
                        formatNumber(scaledAmount) +
                        (ingredient.unit ? " " + ingredient.unit : "") +
                        (ingredient.name ? " " + ingredient.name : "");
                } else {
                    item.textContent = String(ingredient.original || ingredient.name || "").trim();
                }
                if (item.textContent) {
                    ingredientsList.appendChild(item);
                }
            }
            ingredientsSection.hidden = ingredientsList.childElementCount === 0;
        }

        function renderTextList(container, values) {
            container.replaceChildren();
            if (!Array.isArray(values)) {
                return 0;
            }
            for (const value of values) {
                const text = String(value || "").trim();
                if (!text) {
                    continue;
                }
                const item = document.createElement("li");
                item.textContent = text;
                container.appendChild(item);
            }
            return container.childElementCount;
        }

        function renderDetails(payload) {
            const recipe = payload.recipe || {};
            title.textContent = recipe.title || "Detail resep";
            if (recipe.image && /^https?:\/\//i.test(recipe.image)) {
                image.onerror = function () {
                    image.hidden = true;
                    imagePlaceholder.hidden = false;
                };
                image.src = recipe.image;
                image.alt = recipe.title ? "Foto " + recipe.title : "Foto resep";
                image.hidden = false;
                imagePlaceholder.hidden = true;
            } else {
                image.hidden = true;
                imagePlaceholder.hidden = false;
            }
            const cardImage = activeCard.querySelector(".recipe-img");
            if (recipe.image && /^https?:\/\//i.test(recipe.image) && !cardImage) {
                const nextImage = document.createElement("img");
                const media = activeCard.querySelector(".recipe-card-media");
                const placeholder = media.querySelector(".recipe-img-placeholder");
                nextImage.className = "recipe-img";
                nextImage.addEventListener("error", function () {
                    nextImage.remove();
                    if (placeholder) placeholder.hidden = false;
                }, { once: true });
                nextImage.alt = recipe.title ? "Foto " + recipe.title : "Foto resep";
                if (placeholder) placeholder.hidden = true;
                media.prepend(nextImage);
                nextImage.src = recipe.image;
            }
            if (recipe.description) {
                description.textContent = recipe.description;
                description.hidden = false;
            }
            if (recipe.source_name) {
                source.textContent = "Sumber resep: " + recipe.source_name;
                source.hidden = false;
            }
            if (recipe.preparation_time) {
                preparationTime.textContent =
                    "Waktu persiapan: " + recipe.preparation_time + " menit";
                preparationTime.hidden = false;
            }
            if (recipe.cooking_time) {
                cookingTime.textContent = "Waktu memasak: " + recipe.cooking_time + " menit";
                cookingTime.hidden = false;
            }

            originalServings = Number(recipe.servings);
            if (!Number.isInteger(originalServings) || originalServings < 1) {
                originalServings = null;
            }
            currentIngredients = Array.isArray(payload.ingredients) ? payload.ingredients : [];
            currentNutrition = payload.nutrition || {};
            if (originalServings) {
                servingsInput.value = String(originalServings);
                servingsInput.max = "1000";
                originalServingsLabel.textContent = "Resep awal: " + originalServings + " porsi.";
                servingCalculator.hidden = false;
            }
            renderNutrition(currentNutrition);
            renderIngredients();
            instructionsSection.hidden = false;
            instructionsEmpty.hidden =
                renderTextList(instructionsList, payload.instructions) > 0;
            details.hidden = false;

            const external = payload.external || {};
            if (external.status === "ok") {
                setStatus("Detail resep berhasil dimuat.");
            } else if (external.status === "local") {
                setStatus("Detail resep lokal berhasil dimuat.");
            } else if (external.status === "not_configured") {
                setStatus("Data lokal ditampilkan. Spoonacular belum dikonfigurasi.");
            } else if (external.status === "not_found") {
                setStatus("Data lokal ditampilkan; resep ini belum ditemukan di Spoonacular.");
            } else {
                setStatus("Data lokal tetap ditampilkan karena Spoonacular sedang tidak tersedia.");
            }
            if (activeCard) {
                const actionArea = activeCard.parentElement.querySelector(".recipe-card-actions");
                const anonymousLoginLink = actionArea && actionArea.querySelector(".vote-login");
                const loginUrl = actionArea && actionArea.dataset.loginUrl;
                if (anonymousLoginLink && loginUrl) anonymousLoginLink.href = loginUrl;
            }
            renderInteraction(recipe.id, payload.interaction);
        }

        async function markViewed(card) {
            try {
                const interaction = await requestJson(card.dataset.viewUrl, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCookie("csrftoken"),
                    },
                });
                updateCardIndicators(card.dataset.recipeId, interaction);
                if (activeCard === card) {
                    renderInteraction(card.dataset.recipeId, interaction);
                }
            } catch (requestError) {
                if (activeCard === card && requestError.status === 401) {
                    setStatus("Masuk untuk menyimpan status resep yang sudah dilihat.");
                    loginPrompt.hidden = false;
                    if (requestError.loginUrl) loginLink.href = requestError.loginUrl;
                } else if (activeCard === card) {
                    setStatus("Detail terbuka, tetapi status dilihat belum tersimpan.");
                }
            }
        }

        async function loadRecipe(card) {
            try {
                const payload = await requestJson(card.dataset.detailUrl, { method: "GET" });
                if (activeCard !== card) {
                    return;
                }
                renderDetails(payload);
                await markViewed(card);
            } catch (requestError) {
                if (activeCard !== card) {
                    return;
                }
                details.hidden = true;
                error.textContent = requestError.message || "Detail resep gagal dimuat.";
                error.hidden = false;
                setStatus("");
            }
        }

        function openModal(card) {
            if (closeTimer) {
                window.clearTimeout(closeTimer);
                closeTimer = null;
            }
            overlay.classList.remove("is-closing");
            resetModal();
            activeCard = card;
            previousFocus = document.activeElement;
            savedBodyOverflow = document.body.style.overflow;
            document.body.style.overflow = "hidden";
            overlay.hidden = false;
            overlay.setAttribute("aria-hidden", "false");
            window.requestAnimationFrame(function () {
                overlay.classList.add("is-open");
            });
            closeButton.focus();
            loadRecipe(card);
        }

        function closeModal() {
            if (overlay.hidden) {
                return;
            }
            overlay.classList.remove("is-open");
            overlay.classList.add("is-closing");
            overlay.setAttribute("aria-hidden", "true");
            document.body.style.overflow = savedBodyOverflow;
            activeCard = null;
            closeTimer = window.setTimeout(function () {
                overlay.hidden = true;
                overlay.classList.remove("is-closing");
                closeTimer = null;
            }, 180);
            if (previousFocus && typeof previousFocus.focus === "function") {
                previousFocus.focus();
            }
        }

        function visibleFocusTargets() {
            return Array.from(
                modal.querySelectorAll(
                    "button:not(:disabled), input:not(:disabled), a[href], [tabindex]:not([tabindex='-1'])"
                )
            ).filter(function (element) {
                return !element.closest("[hidden]");
            });
        }

        grid.addEventListener("click", function (event) {
            const card = event.target.closest(".recipe-card-open");
            if (card && grid.contains(card)) {
                openModal(card);
            }
        });

        closeButton.addEventListener("click", closeModal);
        overlay.addEventListener("click", function (event) {
            if (event.target === overlay) {
                closeModal();
            }
        });

        document.addEventListener("keydown", function (event) {
            if (overlay.hidden) {
                return;
            }
            if (event.key === "Escape") {
                event.preventDefault();
                closeModal();
                return;
            }
            if (event.key !== "Tab") {
                return;
            }
            const targets = visibleFocusTargets();
            if (!targets.length) {
                event.preventDefault();
                modal.focus();
                return;
            }
            const first = targets[0];
            const last = targets[targets.length - 1];
            if (event.shiftKey && (document.activeElement === first || document.activeElement === modal)) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        });

        completionConfirm.addEventListener("change", function () {
            completionButton.disabled =
                !completionConfirm.checked || completionConfirm.disabled;
        });

        servingsInput.addEventListener("input", function () {
            if (!servingsInput.value) return;
            const servings = Number.parseInt(servingsInput.value, 10);
            if (!Number.isInteger(servings) || servings < 1) return;
            renderIngredients();
            renderNutrition(currentNutrition);
        });

    let pendingCookingRequest = null;

    completionButton.addEventListener("click", async function () {
        if (!activeCard || !completionConfirm.checked || completionButton.disabled) {
            return;
        }

        const card = activeCard;

        
        const recipeId = card.dataset.recipeId;

        if (
            !pendingCookingRequest ||
            pendingCookingRequest.recipeId !== recipeId
        ) {
            pendingCookingRequest = {
                recipeId: recipeId,
                requestId: crypto.randomUUID()
            };
        }

        const requestId = pendingCookingRequest.requestId;

    
        completionButton.disabled = true;
        completionStatus.textContent = "Menyimpan aktivitas memasak…";

        try {
            const interaction = await requestJson(card.dataset.completeUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: JSON.stringify({
                    confirmed: true,
                    request_id: requestId
                }),
            });

        
            pendingCookingRequest = null;

            updateCardIndicators(recipeId, interaction);

            if (activeCard === card) {
                renderInteraction(recipeId, interaction);
                completionStatus.textContent = "Resep berhasil dicatat di Tracker!";
            }

        } catch (requestError) {
            if (activeCard === card) {
                completionStatus.textContent =
                    requestError.message || "Aktivitas memasak belum dapat disimpan.";

                if (requestError.status === 401) {
                    loginPrompt.hidden = false;
                    if (requestError.loginUrl) {
                        loginLink.href = requestError.loginUrl;
                    }
                }

                completionButton.disabled = false;
            }
        }
    });

        }

        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", initRecipeModal, { once: true });
        } else {
            initRecipeModal();
        }
    })();
