// @ts-check

/** @typedef {"all" | "delayed" | "clear"} ArrivalFilter */

const arrivalFilter = /** @type {HTMLSelectElement} */ (
  document.querySelector("#arrival-filter")
);
const arrivalList = /** @type {HTMLElement} */ (document.querySelector("#arrival-list"));
const emptyState = /** @type {HTMLElement} */ (document.querySelector("#empty-state"));
const resetFilter = /** @type {HTMLButtonElement} */ (
  document.querySelector("#reset-filter")
);
const eventDialog = /** @type {HTMLDialogElement} */ (
  document.querySelector("#event-dialog")
);
const eventForm = /** @type {HTMLFormElement} */ (document.querySelector("#event-form"));
const eventTitle = /** @type {HTMLInputElement} */ (document.querySelector("#event-title"));
const formError = /** @type {HTMLElement} */ (document.querySelector("#form-error"));
const formSuccess = /** @type {HTMLElement} */ (document.querySelector("#form-success"));
const sidebar = /** @type {HTMLElement} */ (document.querySelector("#sidebar"));
const navToggle = /** @type {HTMLButtonElement} */ (document.querySelector("#nav-toggle"));

/**
 * Filter the visible queue and swap in a deliberate empty state.
 *
 * @param {ArrivalFilter} filter
 * @returns {void}
 */
function applyArrivalFilter(filter) {
  const rows = [...arrivalList.querySelectorAll("[data-state]")];
  let visibleCount = 0;

  for (const row of rows) {
    const isVisible =
      filter === "all" || (filter === "delayed" && row.getAttribute("data-state") === "delayed");
    row.toggleAttribute("hidden", !isVisible);
    visibleCount += isVisible ? 1 : 0;
  }

  arrivalList.toggleAttribute("hidden", visibleCount === 0);
  emptyState.toggleAttribute("hidden", visibleCount !== 0);
}

arrivalFilter.addEventListener("change", () => {
  applyArrivalFilter(/** @type {ArrivalFilter} */ (arrivalFilter.value));
});

resetFilter.addEventListener("click", () => {
  arrivalFilter.value = "all";
  applyArrivalFilter("all");
  arrivalFilter.focus();
});

document.querySelector("#open-log")?.addEventListener("click", () => {
  formError.hidden = true;
  formSuccess.hidden = true;
  eventDialog.showModal();
  eventTitle.focus();
});

function closeDialog() {
  eventDialog.close();
  eventForm.reset();
}

document.querySelector("#close-log")?.addEventListener("click", closeDialog);
document.querySelector("#cancel-log")?.addEventListener("click", closeDialog);

eventForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const hasTitle = eventTitle.value.trim().length > 0;
  formError.hidden = hasTitle;
  formSuccess.hidden = !hasTitle;

  if (!hasTitle) {
    eventTitle.focus();
    return;
  }

  window.setTimeout(closeDialog, 900);
});

navToggle.addEventListener("click", () => {
  const isOpen = sidebar.classList.toggle("open");
  navToggle.setAttribute("aria-expanded", String(isOpen));
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && sidebar.classList.contains("open")) {
    sidebar.classList.remove("open");
    navToggle.setAttribute("aria-expanded", "false");
    navToggle.focus();
  }
});
