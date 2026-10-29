(function () {
    "use strict";

    function initRecipeModal() {
        const grid = document.querySelector(".recipe-grid");
        const searchForm = document.getElementById("recipeSearchForm");
        const searchInput = document.getElementById("recipeSearchInput");
        const searchStatus = document.getElementById("recipeSearchStatus");
        const searchLoadMore = document.getElementById("recipeSearchLoadMore");
        const overlay = document.getElementById("nutritionModal");
        const modal = overlay && overlay.querySelector(".recipe-modal");
        const closeButton = document.getElementById("btnCloseModal");
        const submissionOverlay = document.getElementById("recipeSubmissionOverlay");
        const submissionModal = submissionOverlay && submissionOverlay.querySelector(".recipe-modal");
        const submissionForm = document.getElementById("recipeSubmissionForm");
        const toastRegion = document.getElementById("recipeToastRegion");
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
        const cookingTime = document.getElementById("modalCookingTime");
        const ingredientsSection = document.getElementById("ingredientsSection");
        const ingredientsList = document.getElementById("modalIngredients");
        const instructionsSection = document.getElementById("instructionsSection");
        const instructionsList = document.getElementById("modalInstructions");
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
        const submissionOpenButton = document.getElementById("openRecipeSubmission");
        const submissionCloseButton = document.getElementById("closeRecipeSubmission");
        const submissionCancelButton = document.getElementById("cancelRecipeSubmission");
        const submissionIdInput = document.getElementById("recipeSubmissionId");
        const submissionIngredientsInput = document.getElementById("recipeSubmissionIngredients");
        const submissionInstructionsInput = document.getElementById("recipeSubmissionInstructions");
        const submissionErrors = document.getElementById("recipeSubmissionErrors");
        const submissionStatus = document.getElementById("recipeSubmissionStatus");
        const submissionButton = document.getElementById("submitRecipeButton");
        const ingredientRows = document.getElementById("recipeIngredientRows");
        const cookingSteps = document.getElementById("recipeCookingSteps");
        const addIngredientButton = document.getElementById("addRecipeIngredient");
        const addStepButton = document.getElementById("addRecipeStep");
        const imageInput = document.getElementById("submissionImage");
        const imagePreview = document.getElementById("submissionImagePreview");

        let activeCard = null;
        let previousFocus = null;
        let savedBodyOverflow = "";
        let closeTimer = null;
        let currentIngredients = [];
        let currentNutrition = {};
        let originalServings = null;
        let submissionInProgress = false;
        let previewObjectUrl = "";
        let toastTimer = null;
        let submissionCloseTimer = null;
        let submissionPreviousFocus = null;
        let submissionSavedBodyOverflow = "";
        let recipeSearchTimer = null;
        let recipeSearchController = null;
        let recipeSearchToken = 0;
        let recipeSearchNextOffset = null;
        let recipeSearchHasMore = false;
        const pendingCookingRequests = new Map();

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
                requestError.payload = payload;
                throw requestError;
            }
            return payload;
        }

        function setStatus(message) {
            status.textContent = message || "";
        }

        function createRequestId() {
            if (window.crypto && typeof window.crypto.randomUUID === "function") {
                return window.crypto.randomUUID();
            }
            const bytes = new Uint8Array(16);
            window.crypto.getRandomValues(bytes);
            bytes[6] = (bytes[6] & 0x0f) | 0x40;
            bytes[8] = (bytes[8] & 0x3f) | 0x80;
            const hex = Array.from(bytes, function (byte) {
                return byte.toString(16).padStart(2, "0");
            }).join("");
            return hex.slice(0, 8) + "-" + hex.slice(8, 12) + "-" +
                hex.slice(12, 16) + "-" + hex.slice(16, 20) + "-" + hex.slice(20);
        }

        function showToast(heading, message) {
            if (!toastRegion) return;
            if (toastTimer) window.clearTimeout(toastTimer);
            const toast = document.createElement("div");
            toast.className = "recipe-toast";
            const titleText = document.createElement("strong");
            const bodyText = document.createElement("span");
            titleText.textContent = heading;
            bodyText.textContent = message || "";
            toast.append(titleText, bodyText);
            toastRegion.replaceChildren(toast);
            toastTimer = window.setTimeout(function () {
                toast.classList.add("is-leaving");
                window.setTimeout(function () { toast.remove(); }, 220);
            }, 3600);
        }

        function safeRecipeImageUrl(value) {
            if (typeof value !== "string") return "";
            const candidate = value.trim();
            if (!candidate || /[\\\s\u0000-\u001f\u007f]/.test(candidate)) return "";
            if (candidate.startsWith("/")) return candidate.startsWith("//") ? "" : candidate;
            try {
                const parsed = new URL(candidate);
                if ((parsed.protocol !== "http:" && parsed.protocol !== "https:") ||
                    !parsed.hostname || parsed.username || parsed.password) return "";
                return parsed.href;
            } catch (_error) {
                return "";
            }
        }

        function renderCardImage(card, imageUrl, imageTitle) {
            const media = card && card.querySelector(".recipe-card-media");
            if (!media) return;
            const placeholder = media.querySelector(".recipe-img-placeholder");
            let cardImage = media.querySelector(".recipe-img");
            if (!imageUrl) {
                if (cardImage) {
                    cardImage.hidden = true;
                    cardImage.removeAttribute("src");
                }
                if (placeholder) placeholder.hidden = false;
                return;
            }
            if (!cardImage) {
                cardImage = document.createElement("img");
                cardImage.className = "recipe-img";
                media.prepend(cardImage);
            }
            cardImage.onerror = function () {
                cardImage.hidden = true;
                if (placeholder) placeholder.hidden = false;
            };
            cardImage.alt = imageTitle ? "Foto " + imageTitle : "Foto resep";
            cardImage.src = imageUrl;
            cardImage.hidden = false;
            if (placeholder) placeholder.hidden = true;
        }

        function setRecipeSearchStatus(message, state) {
            if (!searchStatus) return;
            searchStatus.textContent = message || "";
            searchStatus.hidden = !message;
            searchStatus.dataset.state = state || "";
            searchStatus.setAttribute("role", state === "error" ? "alert" : "status");
        }

        function clearSearchCards() {
            grid.querySelectorAll('.recipe-card-open[data-external-recipe="true"]')
                .forEach(function (cardButton) {
                    const card = cardButton.closest(".recipe-card");
                    if (card) card.remove();
                });
            const emptyState = grid.querySelector(".recipe-empty-state");
            if (emptyState) {
                emptyState.hidden = Boolean(grid.querySelector(".recipe-card"));
            }
        }

        function createSpoonacularSearchCard(item) {
            const recipeId = Number(item && item.id);
            if (!Number.isInteger(recipeId) || recipeId < 1 || !item.detail_url) return null;
            let detailUrl;
            try {
                detailUrl = new URL(item.detail_url, window.location.origin);
            } catch (_error) {
                return null;
            }
            if (detailUrl.origin !== window.location.origin) return null;

            const article = document.createElement("article");
            article.className = "recipe-card";
            const button = document.createElement("button");
            button.type = "button";
            button.className = "recipe-card-open";
            button.setAttribute("aria-haspopup", "dialog");
            button.dataset.recipeId = "spoonacular-" + recipeId;
            button.dataset.detailUrl = detailUrl.pathname + detailUrl.search;
            button.dataset.externalRecipe = "true";
            button.dataset.completeUrl = detailUrl.pathname.replace(/\/$/, "") + "/complete/";

            const media = document.createElement("div");
            media.className = "recipe-card-media";
            const imageUrl = safeRecipeImageUrl(item.image);
            if (imageUrl) {
                const recipeImage = document.createElement("img");
                recipeImage.className = "recipe-img";
                recipeImage.alt = item.title ? "Foto " + item.title : "Foto resep";
                recipeImage.src = imageUrl;
                recipeImage.addEventListener("error", function () {
                    recipeImage.hidden = true;
                    placeholder.hidden = false;
                }, { once: true });
                media.appendChild(recipeImage);
            }
            const placeholder = document.createElement("div");
            placeholder.className = "recipe-img-placeholder";
            placeholder.setAttribute("aria-hidden", "true");
            placeholder.textContent = "Foto belum tersedia";
            placeholder.hidden = Boolean(imageUrl);
            media.appendChild(placeholder);

            const content = document.createElement("div");
            content.className = "recipe-card-content";
            const titleText = document.createElement("h3");
            titleText.className = "recipe-card-title";
            titleText.textContent = String(item.title || "Resep Spoonacular");
            const meta = document.createElement("p");
            meta.className = "recipe-card-meta";
            const details = [];
            const cookingTime = Number(item.cooking_time);
            const servings = Number(item.servings);
            const protein = Number(item.protein);
            if (Number.isInteger(cookingTime) && cookingTime > 0) {
                details.push("Masak " + cookingTime + " menit");
            }
            if (Number.isInteger(servings) && servings > 0) {
                details.push(servings + " porsi");
            }
            if (Number.isFinite(protein) && protein >= 0) {
                details.push(String(protein) + " g protein");
            }
            meta.textContent = details.join(" • ");
            content.append(titleText, meta);
            button.append(media, content);
            article.appendChild(button);
            return article;
        }

        function appendSpoonacularSearchResults(items) {
            const emptyState = grid.querySelector(".recipe-empty-state");
            if (emptyState && Array.isArray(items) && items.length) emptyState.hidden = true;
            let lastSearchCard = grid.querySelector(
                '.recipe-card-open[data-external-recipe="true"]'
            );
            if (lastSearchCard) lastSearchCard = lastSearchCard.closest(".recipe-card");
            for (const item of Array.isArray(items) ? items : []) {
                const card = createSpoonacularSearchCard(item);
                if (!card) continue;
                if (lastSearchCard && lastSearchCard.parentElement === grid) {
                    lastSearchCard.after(card);
                } else {
                    grid.prepend(card);
                }
                lastSearchCard = card;
            }
        }

        async function runRecipeSearch(append) {
            if (!searchForm || !searchInput || !searchStatus) return;
            const query = searchInput.value.trim();
            if (query.length < 2) {
                if (!append) {
                    clearSearchCards();
                    setRecipeSearchStatus(query ? "Ketik minimal 2 karakter untuk mencari." : "", "");
                    searchLoadMore.hidden = true;
                }
                return;
            }
            if (append && !recipeSearchHasMore) return;

            if (recipeSearchController) recipeSearchController.abort();
            recipeSearchController = new AbortController();
            const controller = recipeSearchController;
            const token = ++recipeSearchToken;
            const offset = append ? recipeSearchNextOffset : 0;
            if (!append) {
                clearSearchCards();
                recipeSearchNextOffset = null;
                recipeSearchHasMore = false;
                searchLoadMore.hidden = true;
            }
            setRecipeSearchStatus(
                append ? "Memuat resep berikutnya…" : "Mencari resep…",
                "loading"
            );
            searchLoadMore.disabled = true;

            const url = new URL(searchForm.dataset.searchUrl, window.location.origin);
            url.searchParams.set("q", query);
            url.searchParams.set("offset", String(offset || 0));
            try {
                const payload = await requestJson(url.pathname + url.search, {
                    method: "GET",
                    signal: controller.signal,
                });
                if (token !== recipeSearchToken) return;
                const results = Array.isArray(payload.results) ? payload.results : [];
                appendSpoonacularSearchResults(results);
                recipeSearchHasMore = Boolean(payload.has_more);
                recipeSearchNextOffset = payload.next_offset;
                searchLoadMore.hidden = !recipeSearchHasMore;
                searchLoadMore.disabled = !recipeSearchHasMore;
                if (!results.length && !append) {
                    setRecipeSearchStatus("Tidak ada resep yang cocok. Coba kata kunci lain.", "empty");
                } else if (!results.length) {
                    setRecipeSearchStatus("Tidak ada hasil tambahan untuk kata kunci ini.", "empty");
                } else {
                    const totalShown = grid.querySelectorAll(
                        '.recipe-card-open[data-external-recipe="true"]'
                    ).length;
                    setRecipeSearchStatus(
                        totalShown + " hasil Spoonacular ditampilkan; urutan memprioritaskan protein.",
                        "success"
                    );
                }
            } catch (requestError) {
                if (requestError.name === "AbortError" || token !== recipeSearchToken) return;
                searchLoadMore.disabled = false;
                searchLoadMore.hidden = !recipeSearchHasMore;
                setRecipeSearchStatus(
                    requestError.message || "Pencarian resep gagal. Coba lagi sebentar.",
                    "error"
                );
            } finally {
                if (token === recipeSearchToken) recipeSearchController = null;
            }
        }

        function setSubmissionError(message) {
            submissionErrors.textContent = message || "";
            submissionErrors.hidden = !message;
        }

        function visibleFocusTargets(dialog) {
            return Array.from(dialog.querySelectorAll(
                "button:not(:disabled), input:not(:disabled), select:not(:disabled), " +
                "textarea:not(:disabled), a[href], [tabindex]:not([tabindex='-1'])"
            )).filter(function (element) {
                return !element.closest("[hidden]");
            });
        }

        function trapFocus(event, dialog) {
            const targets = visibleFocusTargets(dialog);
            if (!targets.length) {
                event.preventDefault();
                dialog.focus();
                return;
            }
            const first = targets[0];
            const last = targets[targets.length - 1];
            if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }

        function updateStepNumbers() {
            const rows = Array.from(cookingSteps.querySelectorAll("[data-step-row]"));
            rows.forEach(function (row, index) {
                row.querySelector(".recipe-step-number").textContent = (index + 1) + ".";
                row.querySelector("textarea").setAttribute("aria-label", "Langkah " + (index + 1));
                const removeButton = row.querySelector("[data-remove-step]");
                removeButton.disabled = rows.length === 1;
            });
        }

        function updateIngredientRows() {
            const rows = Array.from(ingredientRows.querySelectorAll("[data-ingredient-row]"));
            rows.forEach(function (row) {
                row.querySelector("[data-remove-ingredient]").disabled = rows.length === 1;
            });
        }

        function openSubmissionModal() {
            if (!submissionOverlay || submissionInProgress) return;
            if (submissionCloseTimer) {
                window.clearTimeout(submissionCloseTimer);
                submissionCloseTimer = null;
            }
            submissionOverlay.classList.remove("is-closing");
            submissionPreviousFocus = document.activeElement;
            submissionSavedBodyOverflow = document.body.style.overflow;
            document.body.style.overflow = "hidden";
            submissionOverlay.hidden = false;
            submissionOverlay.setAttribute("aria-hidden", "false");
            if (!submissionIdInput.value) submissionIdInput.value = createRequestId();
            updateIngredientRows();
            updateStepNumbers();
            window.requestAnimationFrame(function () { submissionOverlay.classList.add("is-open"); });
            submissionCloseButton.focus();
        }

        function closeSubmissionModal() {
            if (!submissionOverlay || submissionOverlay.hidden || submissionInProgress) return;
            submissionOverlay.classList.remove("is-open");
            submissionOverlay.classList.add("is-closing");
            submissionOverlay.setAttribute("aria-hidden", "true");
            document.body.style.overflow = submissionSavedBodyOverflow;
            submissionCloseTimer = window.setTimeout(function () {
                submissionOverlay.hidden = true;
                submissionOverlay.classList.remove("is-closing");
                submissionCloseTimer = null;
            }, 180);
            if (submissionPreviousFocus && typeof submissionPreviousFocus.focus === "function") {
                submissionPreviousFocus.focus();
            }
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
                    completed.textContent = interaction.completed
                        ? "✓ Sudah dimasak " + Number(interaction.cooking_count || 1) + " kali"
                        : "";
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

            completionButton.textContent = state.cooking_count ? "+ Masak Lagi" : "Tandai sudah dimasak";

            if (state.completed) {
                completionStatus.textContent =
                    "Sudah dimasak " + Number(state.cooking_count || 1) +
                    " kali. Kamu bisa mencatat masak lagi kapan saja.";
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
            const imageUrl = safeRecipeImageUrl(recipe.image);
            renderCardImage(activeCard, imageUrl, recipe.title);
            if (imageUrl) {
                image.onerror = function () {
                    image.hidden = true;
                    imagePlaceholder.hidden = false;
                };
                image.src = imageUrl;
                image.alt = recipe.title ? "Foto " + recipe.title : "Foto resep";
                image.hidden = false;
                imagePlaceholder.hidden = true;
            } else {
                image.hidden = true;
                imagePlaceholder.hidden = false;
            }
            if (recipe.description) {
                description.textContent = recipe.description;
                description.hidden = false;
            }
            if (recipe.source_name) {
                source.textContent = "Sumber: " + recipe.source_name;
                source.hidden = false;
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
            instructionsSection.hidden =
                renderTextList(instructionsList, payload.instructions) === 0;
            details.hidden = false;

            const external = payload.external || {};
            if (payload.translation_status === "unavailable") {
                setStatus("Resep dari Spoonacular ditampilkan dalam bahasa sumber; layanan terjemahan Indonesia belum tersedia.");
            } else if (external.status === "ok") {
                setStatus("Detail resep berhasil dimuat.");
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
            if (card.dataset.externalRecipe === "true" || !card.dataset.viewUrl) {
                return;
            }
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
            const params = new URLSearchParams(window.location.search);

                if (
                    params.get("from") === "tracker" &&
                    params.has("recipe_id")
                ) {
                    window.location.href = "/tracker/";
                    return;
                }
        }

        grid.addEventListener("click", function (event) {
            const card = event.target.closest(".recipe-card-open");
            if (card && grid.contains(card)) {
                openModal(card);
            }
        });

        if (searchForm && searchInput && searchStatus && searchLoadMore) {
            searchInput.addEventListener("input", function () {
                if (recipeSearchTimer) window.clearTimeout(recipeSearchTimer);
                if (recipeSearchController) {
                    recipeSearchController.abort();
                    recipeSearchController = null;
                }
                recipeSearchToken += 1;
                recipeSearchHasMore = false;
                recipeSearchNextOffset = null;
                searchLoadMore.hidden = true;
                searchLoadMore.disabled = false;

                const query = searchInput.value.trim();
                clearSearchCards();
                if (!query) {
                    setRecipeSearchStatus("", "");
                    return;
                }
                if (query.length < 2) {
                    setRecipeSearchStatus("Ketik minimal 2 karakter untuk mencari.", "");
                    return;
                }
                setRecipeSearchStatus("Pencarian dimulai setelah jeda singkat…", "loading");
                recipeSearchTimer = window.setTimeout(function () {
                    recipeSearchTimer = null;
                    runRecipeSearch(false);
                }, 450);
            });

            searchForm.addEventListener("submit", function (event) {
                event.preventDefault();
                if (recipeSearchTimer) window.clearTimeout(recipeSearchTimer);
                recipeSearchTimer = null;
                runRecipeSearch(false);
            });

            searchLoadMore.addEventListener("click", function () {
                runRecipeSearch(true);
            });
        }

        // Membuka detail resep otomatis dari link Bookmark Tracker
            const params = new URLSearchParams(window.location.search);
            const recipeIdFromUrl = params.get("recipe_id");

            if (recipeIdFromUrl) {
                const targetCard = Array.from(
                    grid.querySelectorAll(".recipe-card-open")
                ).find(function (card) {
                    return card.dataset.recipeId === recipeIdFromUrl;
                });

                if (targetCard) {
                    openModal(targetCard);
                }
            }

        closeButton.addEventListener("click", closeModal);
        if (submissionOpenButton) submissionOpenButton.addEventListener("click", openSubmissionModal);
        if (submissionCloseButton) submissionCloseButton.addEventListener("click", closeSubmissionModal);
        if (submissionCancelButton) submissionCancelButton.addEventListener("click", closeSubmissionModal);
        overlay.addEventListener("click", function (event) {
            if (event.target === overlay) {
                closeModal();
            }
        });
        if (submissionOverlay) {
            submissionOverlay.addEventListener("click", function (event) {
                if (event.target === submissionOverlay) closeSubmissionModal();
            });
        }

        document.addEventListener("keydown", function (event) {
            if (submissionOverlay && !submissionOverlay.hidden) {
                if (event.key === "Escape") {
                    event.preventDefault();
                    closeSubmissionModal();
                    return;
                }
                if (event.key === "Tab") trapFocus(event, submissionModal);
                return;
            }
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
            trapFocus(event, modal);
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


        if (addIngredientButton && ingredientRows) {
            addIngredientButton.addEventListener("click", function () {
                const rows = ingredientRows.querySelectorAll("[data-ingredient-row]");
                if (rows.length >= 50) {
                    setSubmissionError("Maksimal 50 bahan untuk satu resep.");
                    return;
                }
                const row = rows[0].cloneNode(true);
                row.querySelector("[data-ingredient-name]").value = "";
                row.querySelector("[data-ingredient-amount]").value = "";
                const unit = row.querySelector("[data-ingredient-unit]");
                unit.value = "";
                const other = row.querySelector("[data-ingredient-unit-other]");
                other.value = "";
                other.hidden = true;
                other.required = false;
                ingredientRows.appendChild(row);
                updateIngredientRows();
                row.querySelector("[data-ingredient-name]").focus();
                showToast("Bahan baru berhasil ditambahkan!", "Lengkapi nama, jumlah, dan satuannya.");
            });

            ingredientRows.addEventListener("click", function (event) {
                const removeButton = event.target.closest("[data-remove-ingredient]");
                if (!removeButton || ingredientRows.querySelectorAll("[data-ingredient-row]").length <= 1) return;
                removeButton.closest("[data-ingredient-row]").remove();
                updateIngredientRows();
            });
            ingredientRows.addEventListener("change", function (event) {
                const unit = event.target.closest("[data-ingredient-unit]");
                if (!unit) return;
                const other = unit.parentElement.querySelector("[data-ingredient-unit-other]");
                other.hidden = unit.value !== "lainnya";
                other.required = unit.value === "lainnya";
                if (!other.required) other.value = "";
                if (other.required) other.focus();
            });
        }

        if (addStepButton && cookingSteps) {
            addStepButton.addEventListener("click", function () {
                const rows = cookingSteps.querySelectorAll("[data-step-row]");
                if (rows.length >= 50) {
                    setSubmissionError("Maksimal 50 langkah untuk satu resep.");
                    return;
                }
                const row = rows[0].cloneNode(true);
                row.querySelector("textarea").value = "";
                cookingSteps.appendChild(row);
                updateStepNumbers();
                row.querySelector("textarea").focus();
            });
            cookingSteps.addEventListener("click", function (event) {
                const removeButton = event.target.closest("[data-remove-step]");
                if (!removeButton || cookingSteps.querySelectorAll("[data-step-row]").length <= 1) return;
                removeButton.closest("[data-step-row]").remove();
                updateStepNumbers();
            });
        }

        if (imageInput && imagePreview) {
            imageInput.addEventListener("change", function () {
                const file = imageInput.files && imageInput.files[0];
                setSubmissionError("");
                if (previewObjectUrl) {
                    URL.revokeObjectURL(previewObjectUrl);
                    previewObjectUrl = "";
                }
                imagePreview.hidden = true;
                imagePreview.removeAttribute("src");
                if (!file) return;
                if (!file.type.startsWith("image/")) {
                    imageInput.value = "";
                    setSubmissionError("Pilih berkas gambar yang valid.");
                    return;
                }
                if (file.size > 5 * 1024 * 1024) {
                    imageInput.value = "";
                    setSubmissionError("Ukuran foto maksimal 5 MB.");
                    return;
                }
                previewObjectUrl = URL.createObjectURL(file);
                imagePreview.src = previewObjectUrl;
                imagePreview.hidden = false;
            });
        }

        if (submissionForm) {
            submissionForm.addEventListener("input", function () {
                if (!submissionErrors.hidden) setSubmissionError("");
            });
            submissionForm.addEventListener("submit", async function (event) {
                event.preventDefault();
                if (submissionInProgress) return;
                setSubmissionError("");

                const ingredients = [];
                let firstInvalid = null;
                for (const row of ingredientRows.querySelectorAll("[data-ingredient-row]")) {
                    const nameInput = row.querySelector("[data-ingredient-name]");
                    const amountInput = row.querySelector("[data-ingredient-amount]");
                    const unitInput = row.querySelector("[data-ingredient-unit]");
                    const otherInput = row.querySelector("[data-ingredient-unit-other]");
                    const name = nameInput.value.trim();
                    const amount = Number(amountInput.value);
                    const unit = unitInput.value === "lainnya" ? otherInput.value.trim() : unitInput.value;
                    nameInput.setCustomValidity(name ? "" : "Isi nama bahan.");
                    amountInput.setCustomValidity(
                        amountInput.value && Number.isFinite(amount) && amount > 0 && amount <= 1e12
                            ? "" : "Jumlah harus berupa angka lebih besar dari nol."
                    );
                    otherInput.hidden = unitInput.value !== "lainnya";
                    otherInput.required = unitInput.value === "lainnya";
                    otherInput.setCustomValidity(
                        unitInput.value !== "lainnya" || (unit && unit.length <= 40)
                            ? "" : "Isi satuan lain (maksimal 40 karakter)."
                    );
                    if (!firstInvalid && (!nameInput.checkValidity() || !amountInput.checkValidity() ||
                        !unitInput.checkValidity() || !otherInput.checkValidity())) {
                        firstInvalid = !nameInput.checkValidity() ? nameInput :
                            !amountInput.checkValidity() ? amountInput :
                            !unitInput.checkValidity() ? unitInput : otherInput;
                    }
                    ingredients.push({ name: name, amount: amountInput.value, unit: unit });
                }

                const steps = Array.from(cookingSteps.querySelectorAll("[data-cooking-step]"))
                    .map(function (step) { return step.value.trim().replace(/\s+/g, " "); });
                const nonemptySteps = steps.filter(Boolean);
                if (!ingredients.length || ingredients.some(function (ingredient) {
                    return !ingredient.name || !ingredient.unit || !Number.isFinite(Number(ingredient.amount)) ||
                        Number(ingredient.amount) <= 0 || Number(ingredient.amount) > 1e12;
                })) {
                    if (firstInvalid) firstInvalid.focus();
                    else setSubmissionError("Periksa kembali nama, jumlah, dan satuan bahan.");
                    if (firstInvalid) firstInvalid.reportValidity();
                    return;
                }
                if (!nonemptySteps.length) {
                    setSubmissionError("Tambahkan sedikitnya satu langkah memasak.");
                    cookingSteps.querySelector("[data-cooking-step]").focus();
                    return;
                }
                if (!submissionForm.checkValidity()) {
                    submissionForm.reportValidity();
                    return;
                }
                if (imageInput.files && imageInput.files[0] &&
                    (!imageInput.files[0].type.startsWith("image/") || imageInput.files[0].size > 5 * 1024 * 1024)) {
                    setSubmissionError("Foto harus berupa gambar dengan ukuran maksimal 5 MB.");
                    imageInput.focus();
                    return;
                }

                submissionIngredientsInput.value = JSON.stringify(ingredients);
                submissionInstructionsInput.value = nonemptySteps.join("\n");
                if (!submissionIdInput.value) submissionIdInput.value = createRequestId();
                submissionInProgress = true;
                submissionButton.disabled = true;
                submissionButton.textContent = "Mengirim…";
                submissionStatus.textContent = "Resep sedang dikirim…";
                try {
                    const payload = await requestJson(submissionForm.dataset.submitUrl, {
                        method: "POST",
                        headers: { "X-CSRFToken": getCookie("csrftoken") },
                        body: new FormData(submissionForm),
                    });
                    if (!payload.success) throw new Error("Resep belum berhasil disimpan.");
                    try { window.sessionStorage.setItem("recipeSubmissionSuccess", "1"); } catch (_error) { }
                    window.location.reload();
                } catch (requestError) {
                    const serverErrors = requestError.payload && requestError.payload.errors;
                    const messages = serverErrors
                        ? Object.values(serverErrors).reduce(function (all, value) {
                            return all.concat(Array.isArray(value) ? value : [String(value)]);
                        }, [])
                        : [];
                    setSubmissionError(messages.length ? messages.join(" ") :
                        (requestError.message || "Resep belum berhasil dikirim. Coba lagi, ya."));
                    submissionStatus.textContent = "Isian tetap tersimpan di formulir agar mudah diperbaiki.";
                    if (requestError.status === 401 && requestError.loginUrl) {
                        submissionStatus.textContent = "Silakan masuk, lalu kirim kembali resep ini.";
                    }
                } finally {
                    submissionInProgress = false;
                    submissionButton.disabled = false;
                    submissionButton.textContent = "Kirim Resep!";
                }
            });
        }

        completionButton.addEventListener("click", async function () {
            if (!activeCard || !completionConfirm.checked || completionButton.disabled) return;
            const card = activeCard;
            const recipeId = card.dataset.recipeId;
            if (!pendingCookingRequests.has(recipeId)) {
                pendingCookingRequests.set(recipeId, createRequestId());
            }
            const requestId = pendingCookingRequests.get(recipeId);
            completionButton.disabled = true;
            completionStatus.textContent = "Menyimpan aktivitas memasak…";
            try {
                const interaction = await requestJson(card.dataset.completeUrl, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCookie("csrftoken"),
                    },
                    body: JSON.stringify({ confirmed: true, request_id: requestId }),
                });
                pendingCookingRequests.delete(recipeId);
                updateCardIndicators(recipeId, interaction);
                if (activeCard === card) renderInteraction(recipeId, interaction);
                showToast("Mantap!", "Resep berhasil ditandai sudah dimasak.");
            } catch (requestError) {
                if (activeCard === card) {
                    completionStatus.textContent = requestError.message ||
                        "Aktivitas memasak belum dapat disimpan.";
                    if (requestError.status === 401) {
                        loginPrompt.hidden = false;
                        if (requestError.loginUrl) loginLink.href = requestError.loginUrl;
                    }
                    completionButton.disabled = false;
                }
            }
        });

        if (submissionCloseButton || submissionCancelButton) updateStepNumbers();
        try {
            if (window.sessionStorage.getItem("recipeSubmissionSuccess") === "1") {
                window.sessionStorage.removeItem("recipeSubmissionSuccess");
                showToast("Resep berhasil dikirim!", "Terima kasih sudah berbagi resep favoritmu.");
            }
        } catch (_error) { }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initRecipeModal, { once: true });
    } else {
        initRecipeModal();
    }
})();
