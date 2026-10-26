
document.addEventListener("DOMContentLoaded", () => {
    const openBtn = document.getElementById("tracker-share-btn");
    const dialog = document.getElementById("tracker-share-dialog");
    const closeBtn = document.getElementById("tracker-share-close");
    const canvas = document.getElementById("tracker-share-canvas");
    const message = document.getElementById("tracker-share-message");

    if (!openBtn || !dialog || !canvas) return;

    const downloadBtn = document.getElementById("tracker-download-share");
    const nativeBtn = document.getElementById("tracker-native-share");
    const whatsappBtn = document.getElementById("tracker-whatsapp-share");
    const copyBtn = document.getElementById("tracker-copy-share");

    function getProgress() {
        const streak = Number(
            document.getElementById("streak-current")?.textContent.trim()
        ) || 0;

        const badgeText =
            document.getElementById("badge-summary")?.textContent || "";

        const unlocked = Number(badgeText.match(/\d+/)?.[0]) || 0;

        return { streak, unlocked };
    }

    function roundedRect(ctx, x, y, w, h, r, color) {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.roundRect(x, y, w, h, r);
        ctx.fill();
    }

   
function renderShareCard() {
    const ctx = canvas.getContext("2d");

    if (!ctx) {
        throw new Error("Canvas tidak tersedia.");
    }

    const { streak } = getProgress();

    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    // OLAHRASA COLOR PALETTE
    const colors = {
        green: "#03695E",
        softGreen: "#80B088",
        orange: "#EE8252",
        yellow: "#E8CC63",
        white: "#FFFEFE",
        cream: "#FFF7F1",
        gray: "#DADFDA",
        muted: "#7A746F"
    };

    // BACKGROUND
    ctx.fillStyle = colors.white;
    ctx.fillRect(0, 0, width, height);

    // BORDER TOP
    ctx.fillStyle = colors.green;
    ctx.fillRect(0, 0, width, 24);

    // BRAND
    ctx.textAlign = "center";

    ctx.fillStyle = colors.green;
    ctx.font = "800 70px Sen, sans-serif";
    ctx.fillText("OlahRasa", width / 2, 120);

    ctx.fillStyle = colors.muted;
    ctx.font = "700 27px Sen, sans-serif";
    ctx.fillText(
        "MY COOKING JOURNEY",
        width / 2,
        175
    );

    // STREAK ICON
    ctx.font = "150px sans-serif";
    ctx.fillText("🔥", width / 2, 370);

    // STREAK NUMBER
    ctx.fillStyle = colors.orange;
    ctx.font = "800 190px Sen, sans-serif";
    ctx.fillText(
        String(streak),
        width / 2,
        585
    );

    // STREAK LABEL
    ctx.font = "800 52px Sen, sans-serif";
    ctx.fillText(
        streak === 1 ? "day streak" : "days streak",
        width / 2,
        660
    );

    // WEEKLY ACTIVITY TITLE
    ctx.fillStyle = colors.green;
    ctx.font = "800 32px Sen, sans-serif";
    ctx.fillText(
        "THIS WEEK'S ACTIVITY",
        width / 2,
        765
    );

    // WEEKLY STREAK DOTS
    const labels = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

    const startX = 155;
    const gap = 128;
    const dotY = 865;
    const radius = 38;

    const chart = document.getElementById("week-chart");

    const activeDays = chart
        ? Array.from(chart.querySelectorAll(
            ".tracker-week-bar"
        )).map((bar) => !bar.classList.contains("is-empty"))
        : [];

    labels.forEach((label, index) => {
        const x = startX + index * gap;
        const active = activeDays[index] || false;

        // DAY LABEL
        ctx.fillStyle = active
            ? colors.orange
            : colors.muted;

        ctx.font = "700 26px Sen, sans-serif";
        ctx.fillText(label, x, 805);

        // CIRCLE
        ctx.beginPath();
        ctx.arc(x, dotY, radius, 0, Math.PI * 2);

        ctx.fillStyle = active
            ? colors.softGreen
            : colors.gray;

        ctx.fill();

        // CHECKMARK
        if (active) {
            ctx.strokeStyle = colors.white;
            ctx.lineWidth = 8;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";

            ctx.beginPath();
            ctx.moveTo(x - 16, dotY);
            ctx.lineTo(x - 3, dotY + 13);
            ctx.lineTo(x + 20, dotY - 15);
            ctx.stroke();
        }
    });

    // MOTIVATIONAL MESSAGE
    const message = streak > 0
        ? `You've cooked ${streak} day${streak === 1 ? "" : "s"} in a row!`
        : "Your cooking journey starts here.";

    ctx.fillStyle = colors.green;
    ctx.font = "800 38px Sen, sans-serif";
    ctx.fillText(message, width / 2, 1030);

    ctx.fillStyle = colors.muted;
    ctx.font = "30px Sen, sans-serif";
    ctx.fillText(
        "Keep cooking and make every ingredient count.",
        width / 2,
        1100
    );

    // FOOTER
    ctx.fillStyle = colors.orange;
    ctx.fillRect(390, 1190, 300, 5);

    ctx.fillStyle = colors.green;
    ctx.font = "700 27px Sen, sans-serif";
    ctx.fillText(
        "Shared from OlahRasa",
        width / 2,
        1255
    );

    ctx.textAlign = "left";
}

      

    function getImageBlob() {
        return new Promise((resolve, reject) => {
            canvas.toBlob(
                (blob) => blob
                    ? resolve(blob)
                    : reject(new Error("Gagal membuat gambar.")),
                "image/png"
            );
        });
    }

    openBtn.addEventListener("click", async () => {
        message.textContent = "";

        try {
            // Pastikan font siap sebelum menggambar canvas
            await document.fonts.load("800 70px Sen");

            renderShareCard();
            dialog.showModal();

            if (window.lucide) {
                window.lucide.createIcons();
            }
        } catch (error) {
            console.error(error);
            message.textContent = error.message;
        }
    });

    closeBtn.addEventListener("click", () => {
        dialog.close();
    });

    // Klik area luar dialog untuk menutup
    dialog.addEventListener("click", (event) => {
        if (event.target === dialog) {
            dialog.close();
        }
    });

    downloadBtn.addEventListener("click", async () => {
        try {
            const blob = await getImageBlob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");

            link.href = url;
            link.download = "olahrasa-my-progress.png";
            link.click();

            setTimeout(() => URL.revokeObjectURL(url), 1000);
            message.textContent = "Gambar berhasil disiapkan.";
        } catch (error) {
            message.textContent = error.message;
        }
    });

    nativeBtn.addEventListener("click", async () => {
        try {
            const blob = await getImageBlob();
            const file = new File(
                [blob],
                "olahrasa-my-progress.png",
                { type: "image/png" }
            );

            const shareData = {
                files: [file],
                title: "My OlahRasa Progress",
                text: "My cooking journey with OlahRasa!"
            };

            if (
                !navigator.share ||
                !navigator.canShare?.(shareData)
            ) {
                message.textContent =
                    "Browser belum mendukung share gambar. Gunakan Download PNG.";
                return;
            }

            await navigator.share(shareData);

        } catch (error) {
            if (error.name !== "AbortError") {
                console.error(error);
                message.textContent = "Gagal membagikan gambar.";
            }
        }
    });

    whatsappBtn.addEventListener("click", () => {
        const { streak, unlocked } = getProgress();

        const text =
            `My OlahRasa Progress!\n` +
            `Cooking Streak: ${streak} hari\n` +
            `Badges Unlocked: ${unlocked}\n` +
            `Cooking more, wasting less.`;

        window.open(
            `https://wa.me/?text=${encodeURIComponent(text)}`,
            "_blank",
            "noopener,noreferrer"
        );
    });

    copyBtn.addEventListener("click", async () => {
        try {
            await navigator.clipboard.writeText(window.location.href);

            message.textContent =
                "Link halaman Tracker tersalin. Penerima mungkin perlu login.";
        } catch (error) {
            message.textContent =
                "Gagal menyalin link. Pastikan browser mengizinkan clipboard.";
        }
    });
});
