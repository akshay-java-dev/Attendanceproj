
document.addEventListener("DOMContentLoaded", () => {
    // Responsive sidebar
    const sidebar = document.getElementById("sidebar");
    const menuToggle = document.getElementById("menuToggle");

    if (sidebar && menuToggle) {
        menuToggle.addEventListener("click", () => {
            const open = sidebar.classList.toggle("open");
            menuToggle.setAttribute("aria-expanded", String(open));
        });

        document.addEventListener("click", event => {
            if (
                window.innerWidth <= 850 &&
                sidebar.classList.contains("open") &&
                !sidebar.contains(event.target) &&
                !menuToggle.contains(event.target)
            ) {
                sidebar.classList.remove("open");
                menuToggle.setAttribute("aria-expanded", "false");
            }
        });
    }

    // Face-photo preview
    const photoInput = document.getElementById("photoInput");
    const photoPreview = document.getElementById("photoPreview");
    let previewUrl = null;

    if (photoInput && photoPreview) {
        photoInput.addEventListener("change", () => {
            if (previewUrl) URL.revokeObjectURL(previewUrl);
            previewUrl = null;

            const file = photoInput.files?.[0];
            if (!file) {
                photoPreview.hidden = true;
                photoPreview.removeAttribute("src");
                return;
            }

            if (!["image/jpeg", "image/png"].includes(file.type)) {
                photoInput.value = "";
                photoPreview.hidden = true;
                alert("Please select a JPG or PNG image.");
                return;
            }

            if (file.size > 5 * 1024 * 1024) {
                photoInput.value = "";
                photoPreview.hidden = true;
                alert("Maximum image size is 5 MB.");
                return;
            }

            previewUrl = URL.createObjectURL(file);
            photoPreview.src = previewUrl;
            photoPreview.hidden = false;
        });
    }

    // Accessible student deletion confirmation
    const modal = document.getElementById("deleteModal");
    const cancelDelete = document.getElementById("cancelDelete");
    const confirmDelete = document.getElementById("confirmDelete");
    const deleteDescription = document.getElementById("deleteDescription");

    let pendingForm = null;
    let oldFocus = null;

    document.querySelectorAll(".sa-delete-form").forEach(form => {
        form.addEventListener("submit", event => {
            event.preventDefault();

            if (!modal) {
                if (confirm("Delete this student and attendance history?")) {
                    form.submit();
                }
                return;
            }

            pendingForm = form;
            oldFocus = document.activeElement;

            if (deleteDescription) {
                deleteDescription.textContent =
                    `Delete ${form.dataset.studentName || "this student"} and their attendance history? This cannot be undone.`;
            }

            modal.hidden = false;
            cancelDelete?.focus();
        });
    });

    function closeModal() {
        if (modal) modal.hidden = true;
        pendingForm = null;
        oldFocus?.focus();
    }

    cancelDelete?.addEventListener("click", closeModal);

    confirmDelete?.addEventListener("click", () => {
        if (!pendingForm) return;

        const form = pendingForm;
        pendingForm = null;
        confirmDelete.disabled = true;
        confirmDelete.textContent = "Deleting...";
        form.submit();
    });

    modal?.addEventListener("click", event => {
        if (event.target === modal) closeModal();
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && modal && !modal.hidden) {
            closeModal();
        }
    });
});
