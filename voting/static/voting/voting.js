(function () {
    if (window.__votingInit) return;
    window.__votingInit = true;

    // ---------- Toast (pola showToast Tutorial 5) ----------
    let toastTimer;

    function ensureToast() {
        let toast = document.getElementById("voting-toast");
        if (toast) return toast;

        toast = document.createElement("div");
        toast.id = "voting-toast";
        toast.className = "vtoast vtoast-hidden";
        toast.setAttribute("popover", "manual");
        toast.innerHTML =
            '<div class="vtoast__content">' +
            '<h3 class="vtoast__title"></h3>' +
            '<p class="vtoast__message"></p>' +
            "</div>";
        document.body.appendChild(toast);
        return toast;
    }

    function votingToast(title, message, type = "normal", duration = 3000) {
        const toast = ensureToast();

        toast.classList.remove("vtoast-success", "vtoast-error", "vtoast-normal");
        if (type === "success") toast.classList.add("vtoast-success");
        else if (type === "error") toast.classList.add("vtoast-error");
        else toast.classList.add("vtoast-normal");

        // textContent (bukan innerHTML) supaya pesan dari server tidak pernah ditafsirkan sebagai HTML
        toast.querySelector(".vtoast__title").textContent = title;
        toast.querySelector(".vtoast__message").textContent = message;

        clearTimeout(toastTimer);

        if (typeof toast.showPopover === "function" && !toast.matches(":popover-open")) {
            toast.showPopover();
            void toast.offsetHeight; // paksa browser menghitung style agar transisi berjalan
        }
        toast.classList.remove("vtoast-hidden");
        toast.classList.add("vtoast-show");

        toastTimer = setTimeout(() => {
            toast.classList.remove("vtoast-show");
            toast.classList.add("vtoast-hidden");
            toastTimer = setTimeout(() => {
                if (typeof toast.hidePopover === "function" && toast.matches(":popover-open")) {
                    toast.hidePopover();
                }
            }, 300);
        }, duration);
    }

    // ---------- CSRF + fetch (pola getCookie Tutorial 4 dan 5) ----------
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === name + "=") {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    async function post(url, data, csrfFallback) {
        const response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": getCookie("csrftoken") || csrfFallback || "",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            },
            body: data instanceof FormData ? data : new URLSearchParams(data || {}),
        });

        const body = await response.json().catch(() => ({}));

        if (response.status === 401) {
            const next = encodeURIComponent(window.location.pathname + window.location.search);
            window.location.assign((body.login_url || "/accounts/login/") + "?next=" + next);
            return null;
        }
        if (!response.ok) {
            const error = new Error(
                body.message || body.error || "Terjadi kesalahan (status " + response.status + ")."
            );
            error.status = response.status;
            error.payload = body;
            throw error;
        }
        return body;
    }

    function setBookmarkCount(total) {
        document.querySelectorAll("[data-bookmark-count]").forEach((el) => {
            el.textContent = total;
        });
    }

    // ---------- Klik vote dan bookmark (event delegation) ----------
    document.addEventListener("click", async (event) => {
        const voteButton = event.target.closest(".vote__btn");
        if (voteButton) {
            const box = voteButton.closest(".vote");
            const status = box.closest(".vote-actions").querySelector("[data-status]");
            const buttons = box.querySelectorAll(".vote__btn");
            buttons.forEach((b) => { b.disabled = true; });

            try {
                const data = await post(
                    box.dataset.voteUrl,
                    { value: voteButton.dataset.value },
                    box.dataset.csrf
                );
                if (!data) return;

                // Event bisa dibatalkan (preventDefault) oleh halaman yang ingin menangani sendiri
                const proceed = document.dispatchEvent(
                    new CustomEvent("voting:vote-changed", { detail: data, cancelable: true })
                );

                if (data.deleted) {
                    votingToast(
                        "Resep dihapus",
                        "Resep ini mencapai 100 downvote dan dihapus otomatis.",
                        "error",
                        4000
                    );
                    if (proceed) {
                        setTimeout(() => window.location.assign(box.dataset.listUrl), 1500);
                    }
                    return;
                }

                box.querySelector(".vote__count").textContent = data.score;
                box.classList.toggle("is-up", data.user_vote === 1);
                box.classList.toggle("is-down", data.user_vote === -1);
                box.title = data.upvotes + " upvote, " + data.downvotes + " downvote";
                buttons.forEach((b) =>
                    b.setAttribute("aria-pressed", String(Number(b.dataset.value) === data.user_vote))
                );
                status.textContent = "";
            } catch (error) {
                status.textContent = error.message;
                votingToast("Gagal memberi vote", error.message, "error");
            } finally {
                buttons.forEach((b) => { b.disabled = false; });
            }
            return;
        }

        const bookmark = event.target.closest(".bookmark");
        if (bookmark) {
            const status = bookmark.closest(".vote-actions").querySelector("[data-status]");
            bookmark.disabled = true;

            try {
                const data = await post(bookmark.dataset.url, {}, bookmark.dataset.csrf);
                if (!data) return;

                bookmark.classList.toggle("is-saved", data.bookmarked);
                bookmark.setAttribute("aria-pressed", String(data.bookmarked));
                setBookmarkCount(data.bookmark_count);
                status.textContent = "";
                votingToast(
                    data.bookmarked ? "Disimpan" : "Dilepas",
                    data.bookmarked ? "Resep masuk ke bookmark kamu." : "Resep dihapus dari bookmark.",
                    "success",
                    2000
                );
                document.dispatchEvent(new CustomEvent("voting:bookmark-changed", { detail: data }));
            } catch (error) {
                status.textContent = error.message;
                votingToast("Gagal menyimpan bookmark", error.message, "error");
            } finally {
                bookmark.disabled = false;
            }
        }
    });

    // Dipakai script halaman bookmark (dan modul lain kalau perlu)
    window.votingKit = { toast: votingToast, post: post, getCookie: getCookie };
})();